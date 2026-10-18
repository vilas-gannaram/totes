from django.core.paginator import Paginator
from django.db.models import Case, Count, DecimalField, ExpressionWrapper, F, Q, Value, When
from django.shortcuts import render

from products.models import Product
from warehouses.models import Warehouse

from .models import Inventory

PAGE_SIZE = 25

STATUS_TABS = [
    ("all", "All"),
    ("ok", "In stock"),
    ("low", "Low"),
    ("out", "Out of stock"),
]


def with_status(queryset):
    """Annotate each row with a stock status and its stock value.

    out: nothing available. low: at or below the product's reorder point.
    """
    return queryset.annotate(
        status=Case(
            When(quantity_available=0, then=Value("out")),
            When(quantity_available__lte=F("product__reorder_point"), then=Value("low")),
            default=Value("ok"),
        ),
        value=ExpressionWrapper(
            F("quantity_available") * F("product__unit_price"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )


def inventory_list(request):
    base = with_status(Inventory.objects.select_related("product", "warehouse"))

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    warehouse = request.GET.get("warehouse", "")
    status = request.GET.get("status", "all")

    if q:
        base = base.filter(Q(product__name__icontains=q) | Q(product__sku__icontains=q))
    if category:
        base = base.filter(product__category=category)
    if warehouse:
        base = base.filter(warehouse__location_code=warehouse)

    # Tab counts reflect the other filters, so they add up to "All".
    counts = {row["status"]: row["n"] for row in base.values("status").annotate(n=Count("id"))}
    counts["all"] = sum(counts.values())

    rows = base.filter(status=status) if status in ("ok", "low", "out") else base
    rows = rows.order_by("product__name", "warehouse__location_code")
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)
    tab_params = params.copy()
    tab_params.pop("status", None)

    return render(
        request,
        "inventory/list.html",
        {
            "page": page,
            "tabs": [
                {"id": id_, "label": label, "count": counts.get(id_, 0), "active": id_ == status}
                for id_, label in STATUS_TABS
            ],
            "q": q,
            "category": category,
            "warehouse": warehouse,
            "status": status if status in dict(STATUS_TABS) else "all",
            "categories": Product.objects.exclude(category="")
            .order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "warehouses": Warehouse.objects.order_by("location_code"),
            "filter_qs": params.urlencode(),
            "tab_qs": tab_params.urlencode(),
        },
    )
