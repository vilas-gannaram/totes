from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from orders.models import Order

from .models import Customer


class CustomerListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ada = Customer.objects.create(name="Ada", email="ada@x.io", phone="555")
        cls.bob = Customer.objects.create(name="Bob", email="bob@x.io")
        for _ in range(2):
            Order.objects.create(customer=cls.ada, total_amount=Decimal("5.00"))

    def get(self, **params):
        return self.client.get(reverse("customer-list"), params)

    def test_order_counts(self):
        rows = {c.name: c for c in self.get().context["page"]}
        self.assertEqual(rows["Ada"].order_count, 2)
        self.assertEqual(rows["Bob"].order_count, 0)
        self.assertIsNone(rows["Bob"].last_order)

    def test_search(self):
        self.assertEqual([c.name for c in self.get(q="bob@").context["page"]], ["Bob"])
        self.assertEqual([c.name for c in self.get(q="555").context["page"]], ["Ada"])
