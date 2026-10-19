from django.test import TestCase
from django.urls import reverse

from purchasing.models import PurchaseOrder
from warehouses.models import Warehouse

from .models import Supplier


class SupplierListTests(TestCase):
    def test_po_counts_and_search(self):
        acme = Supplier.objects.create(name="Acme", email="a@x.io")
        Supplier.objects.create(name="Zed", email="z@x.io")
        wh = Warehouse.objects.create(name="Pune", location_code="PNQ")
        PurchaseOrder.objects.create(supplier=acme, warehouse=wh)

        rows = {s.name: s for s in self.client.get(reverse("supplier-list")).context["page"]}
        self.assertEqual((rows["Acme"].po_count, rows["Zed"].po_count), (1, 0))

        page = self.client.get(reverse("supplier-list"), {"q": "zed"}).context["page"]
        self.assertEqual([s.name for s in page], ["Zed"])
