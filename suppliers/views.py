from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.shortcuts import render

from config.listing import filter_params

from .models import Supplier

PAGE_SIZE = 25


def supplier_list(request):
    suppliers = Supplier.objects.annotate(
        po_count=Count("purchaseorder"), last_po=Max("purchaseorder__created_at")
    )

    q = request.GET.get("q", "").strip()
    if q:
        suppliers = suppliers.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )

    suppliers = suppliers.order_by("name", "email")
    page = Paginator(suppliers, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "suppliers/list.html",
        {"page": page, "q": q, "filter_qs": filter_params(request)},
    )
