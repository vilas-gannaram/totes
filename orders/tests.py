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


class OrderNewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from inventory.models import Inventory
        from warehouses.models import Warehouse

        cls.ada = Customer.objects.create(name="Ada", email="ada@x.io")
        cls.bolt = Product.objects.create(sku="B", name="Bolt", unit_price=Decimal("2.50"))
        cls.nut = Product.objects.create(sku="N", name="Nut", unit_price=Decimal("1.00"))
        cls.gone = Product.objects.create(sku="G", name="Gone", unit_price=Decimal("9.00"))
        pune = Warehouse.objects.create(name="Pune", location_code="PNQ")
        delhi = Warehouse.objects.create(name="Delhi", location_code="DEL")
        cls.bolt_pune = Inventory.objects.create(product=cls.bolt, warehouse=pune, quantity_available=5)
        cls.bolt_delhi = Inventory.objects.create(product=cls.bolt, warehouse=delhi, quantity_available=3)
        cls.nut_pune = Inventory.objects.create(product=cls.nut, warehouse=pune, quantity_available=10)
        Inventory.objects.create(product=cls.gone, warehouse=pune, quantity_available=0)

    def post(self, *lines, customer=None):
        data = {
            "customer": (customer or self.ada).pk,
            "form-TOTAL_FORMS": 6, "form-INITIAL_FORMS": 0,
            "form-MIN_NUM_FORMS": 0, "form-MAX_NUM_FORMS": 1000,
        }
        for i in range(6):
            product, qty = lines[i] if i < len(lines) else ("", "")
            data[f"form-{i}-product"] = getattr(product, "pk", product)
            data[f"form-{i}-quantity"] = qty
        return self.client.post(reverse("order-new"), data)

    def test_form_renders_and_hides_out_of_stock_products(self):
        resp = self.client.get(reverse("order-new"))
        self.assertContains(resp, "B — Bolt")
        self.assertNotContains(resp, "G — Gone")

    def test_places_order_and_reserves_stock_across_warehouses(self):
        from inventory.models import StockMovement

        resp = self.post((self.bolt, 6), (self.nut, 2))
        order = Order.objects.get()
        self.assertRedirects(resp, reverse("order-detail", args=[order.pk]))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total_amount, Decimal("17.00"))  # 6*2.50 + 2*1.00
        self.assertEqual(order.items.count(), 2)
        for row in (self.bolt_pune, self.bolt_delhi, self.nut_pune):
            row.refresh_from_db()
        # the bigger stock (Pune, 5) is drained first, then Delhi
        self.assertEqual((self.bolt_pune.quantity_available, self.bolt_pune.quantity_reserved), (0, 5))
        self.assertEqual((self.bolt_delhi.quantity_available, self.bolt_delhi.quantity_reserved), (2, 1))
        self.assertEqual((self.nut_pune.quantity_available, self.nut_pune.quantity_reserved), (8, 2))
        moves = StockMovement.objects.filter(reference_type="ORDER", reference_id=order.pk)
        self.assertEqual(sorted(m.quantity_delta for m in moves), [-5, -2, -1])

    def test_rejects_more_than_in_stock(self):
        resp = self.post((self.bolt, 9))
        self.assertContains(resp, "Only 8 in stock.")
        self.assertEqual(Order.objects.count(), 0)

    def test_rejects_empty_and_duplicate_lines(self):
        self.assertContains(self.post(), "Add at least one item.")
        self.assertContains(self.post((self.bolt, 1), (self.bolt, 2)), "only once")
        self.assertContains(self.post((self.bolt, "")), "Pick a product and a quantity.")
        self.assertEqual(Order.objects.count(), 0)

    def test_place_order_rolls_back_when_stock_runs_out(self):
        from inventory.models import StockMovement

        from .services import InsufficientStock, place_order

        with self.assertRaises(InsufficientStock):
            place_order(self.ada, [(self.nut, 4), (self.bolt, 99)])
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.nut_pune.refresh_from_db()
        self.assertEqual(self.nut_pune.quantity_available, 10)

    def test_list_links_to_new_order(self):
        self.assertContains(self.client.get(reverse("order-list")), reverse("order-new"))
