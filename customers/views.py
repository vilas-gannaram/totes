from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.shortcuts import render

from config.listing import filter_params

from .models import Customer

PAGE_SIZE = 25


def customer_list(request):
    customers = Customer.objects.annotate(
        order_count=Count("order"), last_order=Max("order__created_at")
    )

    q = request.GET.get("q", "").strip()
    if q:
        customers = customers.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    # Aggregating adds a GROUP BY, and Django ignores Meta.ordering for those.
    customers = customers.order_by("name", "email")
    page = Paginator(customers, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "customers/list.html",
        {"page": page, "q": q, "filter_qs": filter_params(request)},
    )
