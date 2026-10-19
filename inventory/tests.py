from decimal import Decimal
from io import StringIO

from django.test import TestCase
from django.urls import reverse

from products.models import Product
from warehouses.models import Warehouse

from .models import Inventory


class InventoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pune = Warehouse.objects.create(name="Pune", location_code="PNQ")
        cls.delhi = Warehouse.objects.create(name="Delhi", location_code="DEL")
        cls.bolt = Product.objects.create(
            sku="HW-BOLT", name="Hex bolt", category="Hardware",
            unit_price=Decimal("10.00"), reorder_point=20,
        )
        cls.box = Product.objects.create(
            sku="PKG-BOX", name="Box", category="Packaging",
            unit_price=Decimal("2.50"), reorder_point=10,
        )
        Inventory.objects.create(product=cls.bolt, warehouse=cls.pune, quantity_available=0)
        Inventory.objects.create(product=cls.bolt, warehouse=cls.delhi, quantity_available=15)
        Inventory.objects.create(product=cls.box, warehouse=cls.pune, quantity_available=100)

    def get(self, **params):
        response = self.client.get(reverse("inventory-list"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_status_classification(self):
        statuses = {
            (r.product.sku, r.warehouse.location_code): r.status
            for r in self.get().context["page"]
        }
        self.assertEqual(statuses[("HW-BOLT", "PNQ")], "out")
        self.assertEqual(statuses[("HW-BOLT", "DEL")], "low")
        self.assertEqual(statuses[("PKG-BOX", "PNQ")], "ok")

    def test_value_is_available_times_unit_price(self):
        rows = {r.product.sku: r.value for r in self.get(status="ok").context["page"]}
        self.assertEqual(rows["PKG-BOX"], Decimal("250.00"))

    def test_status_tab_filters_and_counts(self):
        response = self.get(status="low")
        self.assertEqual(len(response.context["page"]), 1)
        counts = {t["id"]: t["count"] for t in response.context["tabs"]}
        self.assertEqual(counts, {"all": 3, "ok": 1, "low": 1, "out": 1})

    def test_search_category_and_warehouse_filters(self):
        self.assertEqual(len(self.get(q="box").context["page"]), 1)
        self.assertEqual(len(self.get(q="pkg-").context["page"]), 1)
        self.assertEqual(len(self.get(category="Hardware").context["page"]), 2)
        self.assertEqual(len(self.get(warehouse="DEL").context["page"]), 1)

    def test_counts_respect_other_filters(self):
        counts = {t["id"]: t["count"] for t in self.get(warehouse="PNQ").context["tabs"]}
        self.assertEqual(counts["all"], 2)

    def test_unknown_status_falls_back_to_all(self):
        self.assertEqual(len(self.get(status="bogus").context["page"]), 3)

    def test_pagination(self):
        for i in range(30):
            p = Product.objects.create(sku=f"S{i}", name=f"P{i:02}", unit_price=1)
            Inventory.objects.create(product=p, warehouse=self.pune, quantity_available=50)
        page = self.get().context["page"]
        self.assertEqual(len(page), 25)
        self.assertEqual(len(self.get(page=2).context["page"]), 8)


class SeedDemoTests(TestCase):
    def test_seed_builds_a_consistent_database(self):
        from django.core.management import call_command
        from django.db.models import Sum

        from orders.models import Order

        call_command("seed_demo", stdout=StringIO())

        self.assertGreater(Product.objects.count(), 30)
        self.assertGreater(Inventory.objects.count(), 50)
        # the ledger explains every counter
        for row in Inventory.objects.annotate(total=Sum("movements__quantity_delta")):
            self.assertEqual(row.total or 0, row.quantity_available, row)
        # order totals match their items
        for order in Order.objects.prefetch_related("items"):
            self.assertEqual(
                order.total_amount,
                sum(i.quantity * i.unit_price_at_order for i in order.items.all()),
            )

    def test_seed_refuses_a_database_with_data(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        Warehouse.objects.create(name="Existing", location_code="EXI")
        with self.assertRaises(CommandError):
            call_command("seed_demo", stdout=StringIO())

    def test_reset_replaces_existing_data(self):
        from django.core.management import call_command

        Warehouse.objects.create(name="Existing", location_code="EXI")
        call_command("seed_demo", reset=True, yes=True, stdout=StringIO())
        self.assertFalse(Warehouse.objects.filter(location_code="EXI").exists())
        self.assertEqual(Warehouse.objects.count(), 3)
