from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Inventory, StockMovement
from products.models import Product
from purchasing.models import PurchaseOrder, PurchaseOrderItem
from suppliers.models import Supplier
from warehouses.models import Warehouse


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.wh = Warehouse.objects.create(name="Pune", location_code="PNQ")
        cls.bolt = Product.objects.create(
            sku="HW-BOLT", name="Hex bolt", category="Hardware",
            unit_price=Decimal("10.00"), reorder_point=20,
        )
        cls.box = Product.objects.create(
            sku="PKG-BOX", name="Box", category="",
            unit_price=Decimal("2.50"), reorder_point=10,
        )
        cls.gone = Product.objects.create(
            sku="PPE-GLV", name="Gloves", category="Safety",
            unit_price=Decimal("5.00"), reorder_point=5,
        )
        cls.low_row = Inventory.objects.create(product=cls.bolt, warehouse=cls.wh, quantity_available=15)
        Inventory.objects.create(product=cls.box, warehouse=cls.wh, quantity_available=100)
        Inventory.objects.create(product=cls.gone, warehouse=cls.wh, quantity_available=0)

    def get(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        return response

    def test_key_figures(self):
        ctx = self.get().context
        self.assertEqual(ctx["total_skus"], 3)
        self.assertEqual(ctx["stock_value"], Decimal("400.00"))  # 15*10 + 100*2.5
        self.assertEqual((ctx["low_count"], ctx["out_count"]), (1, 1))

    def test_needs_reorder_lists_out_and_low_rows_only(self):
        skus = [r.product.sku for r in self.get().context["needs_reorder"]]
        self.assertEqual(skus, ["PPE-GLV", "HW-BOLT"])

    def test_value_by_category(self):
        cats = {c["name"]: c for c in self.get().context["categories"]}
        self.assertEqual(cats["Uncategorised"]["pct"], 100)
        self.assertEqual(cats["Hardware"]["pct"], 60)

    def test_open_purchase_orders(self):
        supplier = Supplier.objects.create(name="Acme", email="a@x.io")
        po = PurchaseOrder.objects.create(
            supplier=supplier, warehouse=self.wh,
            status=PurchaseOrder.Status.ORDERED, expected_at=timezone.now(),
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po, product=self.bolt,
            quantity_ordered=10, quantity_received=4, unit_cost=Decimal("3.00"),
        )
        PurchaseOrder.objects.create(supplier=supplier, warehouse=self.wh)  # draft
        ctx = self.get().context
        self.assertEqual(ctx["open_po_count"], 1)
        self.assertEqual(ctx["incoming_value"], Decimal("18.00"))  # (10-4)*3

    def test_recent_movements(self):
        StockMovement.objects.create(
            inventory=self.low_row, movement_type="RECEIPT",
            quantity_delta=5, reference_type="MANUAL",
        )
        self.assertEqual(len(self.get().context["movements"]), 1)

    def test_empty_database_renders(self):
        Inventory.objects.all().delete()
        Product.objects.all().delete()
        self.assertContains(self.get(), "Nothing needs reordering.")
