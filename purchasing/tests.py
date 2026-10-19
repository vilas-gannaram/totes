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


class PurchaseOrderWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.acme = Supplier.objects.create(name="Acme", email="a@x.io")
        cls.wh = Warehouse.objects.create(name="Pune", location_code="PNQ")
        cls.bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.00"))
        cls.nut = Product.objects.create(sku="N", name="Nut", unit_price=Decimal("1.00"))

    def make_po(self, status=PurchaseOrder.Status.ORDERED):
        po = PurchaseOrder.objects.create(supplier=self.acme, warehouse=self.wh, status=status)
        self.bolt_item = PurchaseOrderItem.objects.create(purchase_order=po, product=self.bolt, quantity_ordered=10, unit_cost=Decimal("1.50"))
        self.nut_item = PurchaseOrderItem.objects.create(purchase_order=po, product=self.nut, quantity_ordered=4, unit_cost=Decimal("0.50"))
        return po

    def status(self, po, target):
        return self.client.post(reverse("purchase-order-status", args=[po.pk]), {"status": target})

    def receive(self, po, bolt="", nut=""):
        return self.client.post(
            reverse("purchase-order-receive", args=[po.pk]),
            {f"receive-{self.bolt_item.pk}": bolt, f"receive-{self.nut_item.pk}": nut},
        )

    def available(self, product):
        from inventory.models import Inventory

        row = Inventory.objects.filter(product=product, warehouse=self.wh).first()
        return row.quantity_available if row else None

    def test_draft_to_ordered_and_cancel(self):
        po = self.make_po(PurchaseOrder.Status.DRAFT)
        self.status(po, "ORDERED")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.ORDERED)
        self.status(po, "CANCELLED")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.CANCELLED)

    def test_invalid_transitions_change_nothing(self):
        po = self.make_po(PurchaseOrder.Status.DRAFT)
        self.status(po, "RECEIVED")  # only receiving gets you there
        self.status(po, "bogus")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.DRAFT)

    def test_partial_then_full_receipt(self):
        from inventory.models import StockMovement

        po = self.make_po()
        self.receive(po, bolt="6", nut="4")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.ORDERED)  # bolts outstanding
        self.assertEqual((self.available(self.bolt), self.available(self.nut)), (6, 4))

        self.receive(po, bolt="4")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.RECEIVED)
        self.assertEqual(self.available(self.bolt), 10)
        self.bolt_item.refresh_from_db()
        self.assertEqual(self.bolt_item.quantity_received, 10)
        moves = StockMovement.objects.filter(reference_type="PURCHASE_ORDER", reference_id=po.pk)
        self.assertEqual(sorted(m.quantity_delta for m in moves), [4, 4, 6])
        self.assertEqual({m.movement_type for m in moves}, {"RECEIPT"})

    def test_receipt_adds_to_existing_inventory_row(self):
        from inventory.models import Inventory

        Inventory.objects.create(product=self.bolt, warehouse=self.wh, quantity_available=7)
        self.receive(self.make_po(), bolt="3")
        self.assertEqual(self.available(self.bolt), 10)

    def test_bad_receipts_save_nothing(self):
        po = self.make_po()
        self.receive(po, bolt="11")  # more than outstanding
        self.receive(po, bolt="2", nut="5")  # one good line, one bad: all or nothing
        self.receive(po, bolt="x")
        self.receive(po, bolt="-1")
        self.receive(po)
        self.assertIsNone(self.available(self.bolt))
        self.bolt_item.refresh_from_db()
        self.assertEqual(self.bolt_item.quantity_received, 0)

    def test_cannot_receive_unless_ordered(self):
        po = self.make_po(PurchaseOrder.Status.DRAFT)
        self.receive(po, bolt="1")
        self.assertIsNone(self.available(self.bolt))

    def test_cannot_cancel_after_receiving(self):
        po = self.make_po()
        self.receive(po, bolt="1")
        self.status(po, "CANCELLED")
        po.refresh_from_db()
        self.assertEqual(po.status, PurchaseOrder.Status.ORDERED)

    def test_detail_shows_receive_form_only_when_ordered(self):
        po = self.make_po()
        url = reverse("purchase-order-detail", args=[po.pk])
        self.assertContains(self.client.get(url), f"receive-{self.bolt_item.pk}")
        self.status(po, "CANCELLED")
        self.assertNotContains(self.client.get(url), "Receive stock")

    def test_get_not_allowed(self):
        po = self.make_po()
        for name in ("purchase-order-status", "purchase-order-receive"):
            self.assertEqual(self.client.get(reverse(name, args=[po.pk])).status_code, 405)
