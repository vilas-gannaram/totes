from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.shortcuts import render

from config.listing import filter_params, status_tabs

from .models import PurchaseOrder

PAGE_SIZE = 25


def purchase_order_list(request):
    purchase_orders = PurchaseOrder.objects.all()

    q = request.GET.get("q", "").strip()
    if q:
        purchase_orders = purchase_orders.filter(
            Q(supplier__name__icontains=q) | Q(warehouse__name__icontains=q)
        )

    tabs, status, purchase_orders = status_tabs(
        purchase_orders, request.GET.get("status", "all"), PurchaseOrder.Status.choices
    )
    purchase_orders = purchase_orders.select_related("supplier", "warehouse").annotate(
        item_count=Count("items"),
        total_cost=Sum(
            ExpressionWrapper(
                F("items__quantity_ordered") * F("items__unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
    )
    page = Paginator(purchase_orders.order_by("-created_at"), PAGE_SIZE).get_page(
        request.GET.get("page")
    )
    return render(
        request,
        "purchasing/list.html",
        {
            "page": page,
            "tabs": tabs,
            "status": status,
            "q": q,
            "filter_qs": filter_params(request),
            "tab_qs": filter_params(request, "status"),
        },
    )
