from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from config.listing import filter_params, status_tabs
from inventory.models import StockMovement

from .forms import LineFormSet, OrderForm
from .models import Order
from .services import InsufficientStock, place_order

PAGE_SIZE = 25


def order_list(request):
    orders = Order.objects.all()

    q = request.GET.get("q", "").strip()
    if q:
        orders = orders.filter(Q(customer__name__icontains=q) | Q(customer__email__icontains=q))

    tabs, status, orders = status_tabs(orders, request.GET.get("status", "all"), Order.Status.choices)
    # Annotated after the tab counts: the items join would inflate them.
    orders = orders.select_related("customer").annotate(item_count=Count("items"))
    page = Paginator(orders.order_by("-created_at"), PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "orders/list.html",
        {
            "page": page,
            "tabs": tabs,
            "status": status,
            "q": q,
            "filter_qs": filter_params(request),
            "tab_qs": filter_params(request, "status"),
        },
    )


def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("customer"), pk=pk)
    items = list(
        order.items.select_related("product")
        .annotate(
            line_total=ExpressionWrapper(
                F("quantity") * F("unit_price_at_order"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .order_by("product__sku")
    )
    movements = StockMovement.objects.filter(
        reference_type=StockMovement.ReferenceType.ORDER, reference_id=order.pk
    ).select_related("inventory__product", "inventory__warehouse")
    return render(
        request,
        "orders/detail.html",
        {
            "order": order,
            "items": items,
            "units": sum(i.quantity for i in items),
            "items_total": sum(i.line_total for i in items),
            "movements": movements,
        },
    )


def order_new(request):
    form = OrderForm(request.POST or None)
    lines = LineFormSet(request.POST or None)
    stock_error = None

    if request.method == "POST" and form.is_valid() and lines.is_valid():
        try:
            order = place_order(form.cleaned_data["customer"], lines.lines())
        except InsufficientStock as exc:
            # Stock moved between rendering the form and submitting it.
            stock_error = f"{exc.product.sku}: only {exc.available} left, you asked for {exc.wanted}."
        else:
            messages.success(request, "Order placed and stock reserved.")
            return redirect("order-detail", pk=order.pk)

    return render(request, "orders/new.html", {"form": form, "lines": lines, "stock_error": stock_error})
