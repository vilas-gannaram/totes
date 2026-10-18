from django.core.paginator import Paginator
from django.db.models import Case, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, render

from inventory.models import Inventory, StockMovement
from inventory.views import with_status

from .models import Product

PAGE_SIZE = 25
RECENT_MOVEMENTS_LIMIT = 20


def product_list(request):
    """Products with their stock summed across all warehouses.

    out: nothing available anywhere. low: at or below the reorder point.
    """
    products = Product.objects.annotate(
        total_available=Coalesce(Sum("inventory__quantity_available"), Value(0)),
    ).annotate(
        status=Case(
            When(total_available=0, then=Value("out")),
            When(total_available__lte=F("reorder_point"), then=Value("low")),
            default=Value("ok"),
        )
    )

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")

    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q))
    if category:
        products = products.filter(category=category)

    # Aggregating adds a GROUP BY, and Django ignores Meta.ordering for those.
    products = products.order_by("sku")

    page = Paginator(products, PAGE_SIZE).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "products/list.html",
        {
            "page": page,
            "q": q,
            "category": category,
            "categories": Product.objects.exclude(category="")
            .order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "filter_qs": params.urlencode(),
        },
    )


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    stock = with_status(Inventory.objects.select_related("warehouse")).filter(
        product=product
    ).order_by("warehouse__location_code")
    rows = list(stock)

    total_available = sum(r.quantity_available for r in rows)
    if total_available == 0:
        status = "out"
    elif total_available <= product.reorder_point:
        status = "low"
    else:
        status = "ok"

    movements = StockMovement.objects.filter(inventory__product=product).select_related(
        "inventory__warehouse"
    )[:RECENT_MOVEMENTS_LIMIT]

    return render(
        request,
        "products/detail.html",
        {
            "product": product,
            "rows": rows,
            "total_available": total_available,
            "total_reserved": sum(r.quantity_reserved for r in rows),
            "stock_value": total_available * product.unit_price,
            "status": status,
            "movements": movements,
        },
    )
