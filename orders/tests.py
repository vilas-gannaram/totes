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
