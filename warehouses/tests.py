from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from inventory.models import Inventory
from products.models import Product

from .models import Warehouse


class WarehouseListTests(TestCase):
    def test_totals_per_warehouse(self):
        pune = Warehouse.objects.create(name="Pune", location_code="PNQ")
        Warehouse.objects.create(name="Delhi", location_code="DEL")
        bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.00"))
        nut = Product.objects.create(sku="N", name="Nut", unit_price=Decimal("1.50"))
        Inventory.objects.create(product=bolt, warehouse=pune, quantity_available=10)
        Inventory.objects.create(product=nut, warehouse=pune, quantity_available=4)

        rows = {w.location_code: w for w in self.client.get(reverse("warehouse-list")).context["warehouses"]}
        self.assertEqual(rows["PNQ"].sku_count, 2)
        self.assertEqual(rows["PNQ"].units, 14)
        self.assertEqual(rows["PNQ"].value, Decimal("26.00"))
        self.assertEqual((rows["DEL"].sku_count, rows["DEL"].units, rows["DEL"].value), (0, 0, 0))
