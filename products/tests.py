import uuid
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from inventory.models import Inventory, StockMovement
from warehouses.models import Warehouse

from .models import Product


class ProductListTests(TestCase):
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
        cls.new = Product.objects.create(
            sku="NEW-1", name="Brand new", category="",
            unit_price=Decimal("1.00"), reorder_point=5,
        )
        # bolt: 8 + 7 = 15 across two warehouses, at or below its reorder point
        Inventory.objects.create(product=cls.bolt, warehouse=cls.pune, quantity_available=8)
        Inventory.objects.create(product=cls.bolt, warehouse=cls.delhi, quantity_available=7)
        Inventory.objects.create(product=cls.box, warehouse=cls.pune, quantity_available=100)

    def get(self, **params):
        response = self.client.get(reverse("product-list"), params)
        self.assertEqual(response.status_code, 200)
        return response

    def rows(self, **params):
        return {p.sku: p for p in self.get(**params).context["page"]}

    def test_stock_is_summed_across_warehouses(self):
        rows = self.rows()
        self.assertEqual(rows["HW-BOLT"].total_available, 15)
        self.assertEqual(rows["PKG-BOX"].total_available, 100)

    def test_product_without_inventory_is_out_of_stock(self):
        self.assertEqual(self.rows()["NEW-1"].total_available, 0)
        self.assertEqual(self.rows()["NEW-1"].status, "out")

    def test_status(self):
        rows = self.rows()
        self.assertEqual(rows["HW-BOLT"].status, "low")
        self.assertEqual(rows["PKG-BOX"].status, "ok")

    def test_search_and_category_filters(self):
        self.assertEqual(list(self.rows(q="bolt")), ["HW-BOLT"])
        self.assertEqual(list(self.rows(q="pkg-")), ["PKG-BOX"])
        self.assertEqual(list(self.rows(category="Packaging")), ["PKG-BOX"])

    def test_default_order_is_by_sku(self):
        skus = [p.sku for p in self.get().context["page"]]
        self.assertEqual(skus, sorted(skus))

    def test_pagination(self):
        for i in range(30):
            Product.objects.create(sku=f"S{i:02}", name=f"P{i}", unit_price=1)
        self.assertEqual(len(self.get().context["page"]), 25)
        self.assertEqual(len(self.get(page=2).context["page"]), 8)


class ProductDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.pune = Warehouse.objects.create(name="Pune", location_code="PNQ")
        cls.delhi = Warehouse.objects.create(name="Delhi", location_code="DEL")
        cls.bolt = Product.objects.create(
            sku="HW-BOLT", name="Hex bolt", category="Hardware",
            unit_price=Decimal("10.00"), reorder_point=20,
        )
        cls.other = Product.objects.create(
            sku="PKG-BOX", name="Box", unit_price=Decimal("2.50"), reorder_point=1,
        )
        cls.pune_row = Inventory.objects.create(
            product=cls.bolt, warehouse=cls.pune, quantity_available=8, quantity_reserved=2
        )
        Inventory.objects.create(product=cls.bolt, warehouse=cls.delhi, quantity_available=7)
        cls.other_row = Inventory.objects.create(
            product=cls.other, warehouse=cls.pune, quantity_available=50
        )

    def get(self, product):
        response = self.client.get(reverse("product-detail", args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        return response

    def test_totals_and_status(self):
        ctx = self.get(self.bolt).context
        self.assertEqual(ctx["total_available"], 15)
        self.assertEqual(ctx["total_reserved"], 2)
        self.assertEqual(ctx["stock_value"], Decimal("150.00"))
        self.assertEqual(ctx["status"], "low")

    def test_only_this_products_stock_rows(self):
        rows = self.get(self.bolt).context["rows"]
        self.assertEqual([r.warehouse.location_code for r in rows], ["DEL", "PNQ"])

    def test_movements_are_only_for_this_product(self):
        StockMovement.objects.create(
            inventory=self.pune_row, movement_type="RECEIPT",
            quantity_delta=5, reference_type="MANUAL",
        )
        StockMovement.objects.create(
            inventory=self.other_row, movement_type="SHIP",
            quantity_delta=-1, reference_type="ORDER",
        )
        movements = list(self.get(self.bolt).context["movements"])
        self.assertEqual(len(movements), 1)
        self.assertEqual(movements[0].quantity_delta, 5)

    def test_product_without_stock_renders(self):
        lonely = Product.objects.create(sku="X-1", name="Lonely", unit_price=1)
        response = self.get(lonely)
        self.assertEqual(response.context["status"], "out")
        self.assertContains(response, "Not stocked in any warehouse yet.")

    def test_unknown_product_is_404(self):
        response = self.client.get(reverse("product-detail", args=[uuid.uuid4()]))
        self.assertEqual(response.status_code, 404)

    def test_list_links_to_detail(self):
        response = self.client.get(reverse("product-list"))
        self.assertContains(response, reverse("product-detail", args=[self.bolt.pk]))
