from django.core.paginator import Paginator
from django.db.models import Case, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import Product

PAGE_SIZE = 25


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
