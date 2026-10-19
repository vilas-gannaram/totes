from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.listing import filter_params, status_tabs
from inventory.models import StockMovement

from .models import PurchaseOrder
from .services import (
    InvalidReceipt,
    InvalidTransition,
    allowed_transitions,
    change_status,
    receive,
)

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


def purchase_order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related("supplier", "warehouse"), pk=pk)
    items = list(
        po.items.select_related("product")
        .annotate(
            line_cost=ExpressionWrapper(
                F("quantity_ordered") * F("unit_cost"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            outstanding=F("quantity_ordered") - F("quantity_received"),
        )
        .order_by("product__sku")
    )
    movements = StockMovement.objects.filter(
        reference_type=StockMovement.ReferenceType.PURCHASE_ORDER, reference_id=po.pk
    ).select_related("inventory__product", "inventory__warehouse")
    return render(
        request,
        "purchasing/detail.html",
        {
            "po": po,
            "items": items,
            "units_ordered": sum(i.quantity_ordered for i in items),
            "units_received": sum(i.quantity_received for i in items),
            "total_cost": sum(i.line_cost for i in items),
            "movements": movements,
            "can_receive": po.status == PurchaseOrder.Status.ORDERED,
            "actions": [
                {"status": status, "label": label, "danger": status == PurchaseOrder.Status.CANCELLED}
                for status, label in allowed_transitions(po).items()
            ],
        },
    )


@require_POST
def purchase_order_status(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        po = change_status(po, request.POST.get("status", ""))
    except InvalidTransition as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Purchase order is now {po.get_status_display().lower()}.")
    return redirect("purchase-order-detail", pk=po.pk)


@require_POST
def purchase_order_receive(request, pk):
    po = get_object_or_404(PurchaseOrder, pk=pk)
    quantities = {}
    try:
        for item_pk in po.items.values_list("pk", flat=True):
            raw = request.POST.get(f"receive-{item_pk}", "").strip()
            if raw:
                quantities[item_pk] = int(raw)
        po = receive(po, quantities)
    except ValueError:
        messages.error(request, "Quantities must be whole numbers.")
    except InvalidReceipt as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request,
            "Stock received."
            + (" Purchase order complete." if po.status == PurchaseOrder.Status.RECEIVED else ""),
        )
    return redirect("purchase-order-detail", pk=po.pk)
