from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from customers.models import Customer
from products.models import Product

from .models import Order, OrderItem


class OrderListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ada = Customer.objects.create(name="Ada", email="ada@x.io")
        bob = Customer.objects.create(name="Bob", email="bob@x.io")
        bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.00"))
        nut = Product.objects.create(sku="N", name="Nut", unit_price=Decimal("1.00"))
        cls.paid = Order.objects.create(customer=ada, status=Order.Status.PAID, total_amount=Decimal("3.00"))
        Order.objects.create(customer=bob, total_amount=Decimal("2.00"))
        for p in (bolt, nut):
            OrderItem.objects.create(order=cls.paid, product=p, quantity=1, unit_price_at_order=p.unit_price)

    def get(self, **params):
        return self.client.get(reverse("order-list"), params)

    def test_tab_counts_add_up_and_items_counted(self):
        ctx = self.get().context
        counts = {t["id"]: t["count"] for t in ctx["tabs"]}
        self.assertEqual((counts["all"], counts["PAID"], counts["PENDING"]), (2, 1, 1))
        rows = {o.pk: o for o in ctx["page"]}
        self.assertEqual(rows[self.paid.pk].item_count, 2)

    def test_status_filter_and_unknown_status(self):
        self.assertEqual([o.pk for o in self.get(status="PAID").context["page"]], [self.paid.pk])
        self.assertEqual(len(self.get(status="bogus").context["page"]), 2)

    def test_search_by_customer_keeps_tab_counts_in_step(self):
        ctx = self.get(q="bob").context
        self.assertEqual(len(ctx["page"]), 1)
        self.assertEqual({t["id"]: t["count"] for t in ctx["tabs"]}["all"], 1)


class OrderDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from inventory.models import Inventory, StockMovement
        from warehouses.models import Warehouse

        ada = Customer.objects.create(name="Ada", email="ada@x.io")
        bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.00"))
        cls.order = Order.objects.create(customer=ada, total_amount=Decimal("7.50"))
        OrderItem.objects.create(order=cls.order, product=bolt, quantity=3, unit_price_at_order=Decimal("2.50"))
        row = Inventory.objects.create(
            product=bolt, warehouse=Warehouse.objects.create(name="Pune", location_code="PNQ")
        )
        StockMovement.objects.create(
            inventory=row, movement_type="RESERVE", quantity_delta=-3,
            reference_type="ORDER", reference_id=cls.order.pk,
        )
        StockMovement.objects.create(  # someone else's movement
            inventory=row, movement_type="RECEIPT", quantity_delta=9, reference_type="MANUAL",
        )

    def test_detail(self):
        resp = self.client.get(reverse("order-detail", args=[self.order.pk]))
        ctx = resp.context
        self.assertEqual(ctx["units"], 3)
        self.assertEqual(ctx["items_total"], Decimal("7.50"))
        self.assertEqual(ctx["items"][0].line_total, Decimal("7.50"))
        self.assertEqual([m.quantity_delta for m in ctx["movements"]], [-3])

    def test_unknown_order_is_404(self):
        import uuid

        self.assertEqual(self.client.get(reverse("order-detail", args=[uuid.uuid4()])).status_code, 404)

    def test_list_links_to_detail(self):
        self.assertContains(self.client.get(reverse("order-list")), reverse("order-detail", args=[self.order.pk]))
