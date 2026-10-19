from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import Product
from suppliers.models import Supplier
from warehouses.models import Warehouse

from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        acme = Supplier.objects.create(name="Acme", email="a@x.io")
        wh = Warehouse.objects.create(name="Pune", location_code="PNQ")
        bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.00"))
        nut = Product.objects.create(sku="N", name="Nut", unit_price=Decimal("1.00"))
        cls.ordered = PurchaseOrder.objects.create(
            supplier=acme, warehouse=wh, status=PurchaseOrder.Status.ORDERED
        )
        PurchaseOrder.objects.create(supplier=acme, warehouse=wh)  # draft
        PurchaseOrderItem.objects.create(purchase_order=cls.ordered, product=bolt, quantity_ordered=10, unit_cost=Decimal("1.50"))
        PurchaseOrderItem.objects.create(purchase_order=cls.ordered, product=nut, quantity_ordered=4, unit_cost=Decimal("2.00"))

    def get(self, **params):
        return self.client.get(reverse("purchase-order-list"), params)

    def test_totals_and_tab_counts(self):
        ctx = self.get().context
        counts = {t["id"]: t["count"] for t in ctx["tabs"]}
        self.assertEqual((counts["all"], counts["ORDERED"], counts["DRAFT"]), (2, 1, 1))
        row = {p.pk: p for p in ctx["page"]}[self.ordered.pk]
        self.assertEqual((row.item_count, row.total_cost), (2, Decimal("23.00")))

    def test_status_filter(self):
        page = self.get(status="ORDERED").context["page"]
        self.assertEqual([p.pk for p in page], [self.ordered.pk])


class PurchaseOrderDetailTests(PurchaseOrderListTests):
    def test_detail(self):
        from inventory.models import Inventory, StockMovement

        bolt = Product.objects.get(sku="B")
        row = Inventory.objects.create(product=bolt, warehouse=self.ordered.warehouse)
        StockMovement.objects.create(
            inventory=row, movement_type="RECEIPT", quantity_delta=6,
            reference_type="PURCHASE_ORDER", reference_id=self.ordered.pk,
        )
        StockMovement.objects.create(inventory=row, movement_type="ADJUST", quantity_delta=1, reference_type="MANUAL")

        ctx = self.client.get(reverse("purchase-order-detail", args=[self.ordered.pk])).context
        self.assertEqual((ctx["units_ordered"], ctx["units_received"]), (14, 0))
        self.assertEqual(ctx["total_cost"], Decimal("23.00"))
        self.assertEqual([m.quantity_delta for m in ctx["movements"]], [6])

    def test_list_links_to_detail(self):
        self.assertContains(self.get(), reverse("purchase-order-detail", args=[self.ordered.pk]))

    def test_unknown_po_is_404(self):
        import uuid

        self.assertEqual(self.client.get(reverse("purchase-order-detail", args=[uuid.uuid4()])).status_code, 404)
