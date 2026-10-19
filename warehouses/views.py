from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import Warehouse


def warehouse_list(request):
    warehouses = Warehouse.objects.annotate(
        sku_count=Count("inventory", distinct=True),
        units=Coalesce(Sum("inventory__quantity_available"), Value(0)),
        value=Coalesce(
            Sum(
                ExpressionWrapper(
                    F("inventory__quantity_available") * F("inventory__product__unit_price"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            ),
            Value(0),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    ).order_by("location_code")
    return render(request, "warehouses/list.html", {"warehouses": warehouses})
