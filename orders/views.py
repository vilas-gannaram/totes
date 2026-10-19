from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from config.listing import filter_params, status_tabs

from .models import Order

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
