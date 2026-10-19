from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.listing import filter_params, status_tabs
from inventory.models import StockMovement

from .models import PurchaseOrder
from .forms import LineFormSet, PurchaseOrderForm
from .services import (
    InvalidReceipt,
    InvalidTransition,
    NotEditable,
    allowed_transitions,
    change_status,
    create_purchase_order,
    receive,
    update_purchase_order,
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
            "can_edit": po.status == PurchaseOrder.Status.DRAFT,
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


def _po_form(request, po=None):
    """Shared by the new and edit pages; `po` is the draft being edited, if any."""
    if request.method == "POST":
        form, lines = PurchaseOrderForm(request.POST), LineFormSet(request.POST)
    elif po is None:
        form, lines = PurchaseOrderForm(), LineFormSet()
    else:
        form = PurchaseOrderForm(
            initial={
                "supplier": po.supplier_id,
                "warehouse": po.warehouse_id,
                "expected_at": po.expected_at.date() if po.expected_at else None,
            }
        )
        lines = LineFormSet(
            initial=[
                {"product": i.product_id, "quantity_ordered": i.quantity_ordered, "unit_cost": i.unit_cost}
                for i in po.items.order_by("product__sku")
            ]
        )

    if request.method == "POST" and form.is_valid() and lines.is_valid():
        args = (
            form.cleaned_data["supplier"],
            form.cleaned_data["warehouse"],
            form.cleaned_data["expected_at"],
            lines.lines(),
        )
        if po is None:
            saved = create_purchase_order(*args)
            messages.success(request, "Purchase order created as a draft.")
        else:
            try:
                saved = update_purchase_order(po, *args)
            except NotEditable as exc:
                messages.error(request, str(exc))
                return redirect("purchase-order-detail", pk=po.pk)
            messages.success(request, "Purchase order updated.")
        return redirect("purchase-order-detail", pk=saved.pk)

    return render(
        request,
        "purchasing/form.html",
        {"form": form, "lines": lines, "po": po},
    )


def purchase_order_new(request):
    return _po_form(request)


def purchase_order_edit(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related("supplier", "warehouse"), pk=pk)
    if po.status != PurchaseOrder.Status.DRAFT:
        messages.error(request, "Only draft purchase orders can be edited.")
        return redirect("purchase-order-detail", pk=po.pk)
    return _po_form(request, po)
