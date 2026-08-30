from django.shortcuts import render

from .models import Warehouse

# Create your views here.


def warehouse_list(request):
    warehouses = Warehouse.objects.all()
    return render(request, "warehouses/list.html", {"warehouses": warehouses})
