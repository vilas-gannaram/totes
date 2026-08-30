from django.shortcuts import render

from .models import Inventory

# Create your views here.


def inventory_list(request):
    inventory = Inventory.objects.select_related("product", "warehouse").all()
    return render(request, "inventory/list.html", {"inventory": inventory})
