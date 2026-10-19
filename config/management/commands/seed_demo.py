"""Fill the database with believable demo data.

Run `python manage.py seed_demo`. The data is deterministic (fixed random
seed), so every run builds the same warehouse. It refuses to touch a database
that already has data unless you pass --reset.

The stock ledger is kept honest: for every inventory row,
quantity_available equals the sum of its StockMovement.quantity_delta values.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from customers.models import Customer
from inventory.models import Inventory, StockMovement
from orders.models import Order, OrderItem
from products.models import Product
from purchasing.models import PurchaseOrder, PurchaseOrderItem
from suppliers.models import Supplier
from warehouses.models import Warehouse

WAREHOUSES = [
    ("Columbus Central", "COL-01"),
    ("Reno West", "RNO-01"),
    ("Newark East", "EWR-01"),
]

# (sku, name, category, unit_price, reorder_point)
PRODUCTS = [
    ("HW-BLT-M840", "Hex bolt M8×40, zinc (pack of 50)", "Hardware", "12.40", 40),
    ("HW-NUT-M8", "Hex nut M8, zinc (pack of 100)", "Hardware", "9.80", 40),
    ("HW-WSH-M8", "Flat washer M8 (pack of 100)", "Hardware", "6.20", 50),
    ("HW-SCR-8150", "Wood screw #8 × 1.5 in (box of 200)", "Hardware", "11.50", 30),
    ("HW-ANC-50", "Drywall anchor kit (50 pieces)", "Hardware", "14.90", 25),
    ("HW-HNG-SC", "Cabinet hinge, soft close (pair)", "Hardware", "7.30", 60),
    ("HW-PLK-40", "Padlock, 40 mm brass", "Hardware", "13.60", 20),
    ("HW-TIE-300", "Cable tie 300 mm (pack of 100)", "Hardware", "5.40", 80),
    ("PKG-BOX-1210", "Corrugated box 12×10×8 in", "Packaging", "1.15", 300),
    ("PKG-BOX-1814", "Corrugated box 18×14×12 in", "Packaging", "1.85", 200),
    ("PKG-STR-500", "Stretch wrap film 500 mm", "Packaging", "18.90", 40),
    ("PKG-LBL-1015", "Thermal labels 100×150 mm (roll)", "Packaging", "8.70", 60),
    ("PKG-TPE-48", "Packing tape 48 mm (6 rolls)", "Packaging", "13.20", 40),
    ("PKG-BWR-50", "Bubble wrap 1 m × 50 m", "Packaging", "24.00", 15),
    ("PKG-PAP-10", "Void-fill paper (10 kg)", "Packaging", "29.50", 12),
    ("PKG-MLR-1013", "Poly mailer 10×13 in (pack of 100)", "Packaging", "12.80", 35),
    ("PPE-GLV-M100", "Nitrile gloves, size M (box of 100)", "Safety & PPE", "9.90", 120),
    ("PPE-GLV-L100", "Nitrile gloves, size L (box of 100)", "Safety & PPE", "9.90", 100),
    ("PPE-GOG-AF", "Safety goggles, anti-fog", "Safety & PPE", "4.60", 50),
    ("PPE-HLM-V", "Safety helmet, ventilated", "Safety & PPE", "11.40", 30),
    ("PPE-VST-C2", "Hi-vis vest, class 2", "Safety & PPE", "6.80", 40),
    ("PPE-EAR-200", "Ear plugs (box of 200)", "Safety & PPE", "15.20", 20),
    ("PPE-MSK-N95", "Dust mask N95 (box of 20)", "Safety & PPE", "17.50", 30),
    ("PPE-FAK-50", "First aid kit, 50 person", "Safety & PPE", "34.00", 8),
    ("EL-LED-2236", "LED panel 2×2 ft, 36 W", "Electrical", "38.50", 20),
    ("EL-WIR-25", "Copper wire 2.5 mm² (90 m)", "Electrical", "64.00", 10),
    ("EL-EXT-5M4", "Extension cord 5 m, 4 sockets", "Electrical", "16.90", 25),
    ("EL-CBR-20A", "Circuit breaker 20 A", "Electrical", "12.30", 30),
    ("EL-SWT-1G", "Wall switch, 1 gang", "Electrical", "3.20", 80),
    ("EL-GLD-M20", "Cable gland M20 (pack of 20)", "Electrical", "7.60", 40),
    ("EL-HST-ASR", "Heat-shrink tubing assortment", "Electrical", "9.40", 25),
    ("EL-BLB-E27", "LED bulb E27 9 W (pack of 10)", "Electrical", "13.90", 40),
    ("TL-DRL-18V", "Cordless drill 18 V", "Tools", "89.00", 6),
    ("TL-AGR-4", "Angle grinder 4 in", "Tools", "54.00", 6),
    ("TL-TPM-5", "Tape measure 5 m", "Tools", "6.50", 40),
    ("TL-WRN-250", "Adjustable wrench 250 mm", "Tools", "14.20", 20),
    ("TL-SDR-12", "Screwdriver set (12 pieces)", "Tools", "19.80", 15),
    ("TL-HMR-16", "Claw hammer 16 oz", "Tools", "12.90", 15),
    ("TL-KNF-UT", "Utility knife", "Tools", "4.90", 50),
    ("TL-LVL-600", "Spirit level 600 mm", "Tools", "11.70", 12),
]

# (name, email, phone)
CUSTOMERS = [
    ("Harborview Construction", "purchasing@harborview-construction.example", "+1 614 555 0142"),
    ("Maple & Finch Furniture", "orders@maplefinch.example", "+1 614 555 0117"),
    ("Brightline Logistics", "supplies@brightline-logistics.example", "+1 775 555 0163"),
    ("Cedar Ridge Hardware", "buyer@cedarridge-hardware.example", "+1 775 555 0129"),
    ("Northgate Electric", "ops@northgate-electric.example", "+1 973 555 0184"),
    ("Tri-County Facilities", "procurement@tricounty-facilities.example", "+1 973 555 0138"),
    ("Summit Fabrication", "stores@summit-fab.example", "+1 614 555 0175"),
    ("Lakeside Property Management", "maintenance@lakeside-pm.example", ""),
    ("Ridgeway Contractors", "accounts@ridgeway-contractors.example", "+1 775 555 0191"),
    ("Pioneer Packaging Co.", "purchasing@pioneerpack.example", "+1 973 555 0106"),
    ("Willow Creek Builders", "office@willowcreek-builders.example", "+1 614 555 0153"),
    ("Anvil & Oak Workshop", "hello@anvilandoak.example", ""),
]

# (name, email, phone, categories it supplies)
SUPPLIERS = [
    ("Midwest Fastener Supply", "sales@midwest-fastener.example", "+1 216 555 0121", ["Hardware"]),
    ("Pacific Packaging Group", "sales@pacificpack.example", "+1 503 555 0148", ["Packaging"]),
    ("SafeWorks Distributors", "orders@safeworks-dist.example", "+1 312 555 0172", ["Safety & PPE"]),
    ("Voltline Electrical Wholesale", "trade@voltline.example", "+1 404 555 0133", ["Electrical"]),
    ("Ironside Tool Co.", "wholesale@ironside-tools.example", "+1 412 555 0109", ["Tools", "Hardware"]),
]

NEWEST_FIRST_ORDER_STATUSES = ["PENDING", "PENDING", "PAID", "PAID", "SHIPPED", "CANCELLED"]
SHIPPED_ORDERS = 9
ORDER_COUNT = 18
DOMAIN_MODELS = [
    StockMovement, OrderItem, Order, PurchaseOrderItem, PurchaseOrder,
    Inventory, Product, Warehouse, Customer, Supplier,
]  # delete order: children before parents


class Command(BaseCommand):
    help = "Fill the database with believable demo data (warehouses, stock, orders)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Delete all domain data (not users) before seeding.",
        )
        parser.add_argument(
            "--yes", action="store_true", help="Skip the confirmation for --reset."
        )

    def handle(self, *args, reset, yes, **options):
        existing = {m.__name__: m.objects.count() for m in DOMAIN_MODELS}
        if any(existing.values()):
            if not reset:
                raise CommandError(
                    "The database already has data "
                    f"({', '.join(f'{k}: {v}' for k, v in existing.items() if v)}). "
                    "Use --reset to delete it first."
                )
            if not yes and input("Delete ALL domain data first? [y/N] ").lower() != "y":
                raise CommandError("Aborted.")

        with transaction.atomic():
            if reset:
                for model in DOMAIN_MODELS:
                    model.objects.all().delete()
            self.seed()

        self.stdout.write(self.style.SUCCESS(
            "Seeded: " + ", ".join(f"{m.__name__}: {m.objects.count()}" for m in DOMAIN_MODELS)
        ))

    # --- seeding --------------------------------------------------------

    def seed(self):
        self.rng = random.Random(42)
        self.now = timezone.now()
        self.events = []  # (key, type, delta, reference_type, reference_id, when)
        self.state = {}  # (product_id, warehouse_id) -> {"available", "reserved"}

        warehouses = [Warehouse.objects.create(name=n, location_code=c) for n, c in WAREHOUSES]
        products = [
            Product.objects.create(
                sku=sku, name=name, category=cat, unit_price=Decimal(price), reorder_point=rp
            )
            for sku, name, cat, price, rp in PRODUCTS
        ]
        customers = [
            Customer.objects.create(name=n, email=e, phone=p) for n, e, p in CUSTOMERS
        ]
        suppliers = [
            (Supplier.objects.create(name=n, email=e, phone=p), cats)
            for n, e, p, cats in SUPPLIERS
        ]

        self.opening_stock(products, warehouses)
        orders = self.make_orders(products, customers)
        purchase_orders = self.make_purchase_orders(products, warehouses, suppliers)
        self.write_inventory_and_ledger()
        self.backdate(orders, purchase_orders)

    def days_ago(self, days, hours=0):
        return self.now - timedelta(days=days, hours=hours)

    def row(self, product, warehouse):
        return self.state.setdefault(
            (product.pk, warehouse.pk), {"available": 0, "reserved": 0}
        )

    def log(self, product, warehouse, kind, delta, ref_type, ref_id, when):
        self.events.append(((product.pk, warehouse.pk), kind, delta, ref_type, ref_id, when))

    def opening_stock(self, products, warehouses):
        rng = self.rng
        low = set(rng.sample(range(len(products)), 6))
        out = set(rng.sample([i for i in range(len(products)) if i not in low], 3))
        for i, product in enumerate(products):
            price = product.unit_price
            lo, hi = (150, 600) if price < 10 else (60, 300) if price < 30 else (15, 80)
            for wh in rng.sample(warehouses, rng.choice([1, 2, 2, 3])):
                qty = rng.randint(lo, hi)
                qty = max(qty, product.reorder_point + rng.randint(5, 40))
                if i in low:
                    qty = rng.randint(1, product.reorder_point)
                when = self.days_ago(rng.randint(50, 60))
                row = self.row(product, wh)
                if i in out:
                    # received, then written off after a cycle count
                    start = product.reorder_point + 10
                    self.log(product, wh, "RECEIPT", start, "MANUAL", None, when)
                    self.log(product, wh, "ADJUST", -start, "MANUAL", None,
                             self.days_ago(rng.randint(3, 12)))
                    continue
                row["available"] += qty
                self.log(product, wh, "RECEIPT", qty, "MANUAL", None, when)

    def make_orders(self, products, customers):
        rng = self.rng
        stocked = [k for k, v in self.state.items() if v["available"] > 0]
        by_pk = {p.pk: p for p in products}
        wh_by_pk = {w.pk: w for w in Warehouse.objects.all()}
        statuses = ["SHIPPED"] * SHIPPED_ORDERS + (
            NEWEST_FIRST_ORDER_STATUSES * 3
        )[: ORDER_COUNT - SHIPPED_ORDERS]
        orders = []
        for n, status in enumerate(statuses):
            age_days = int(45 - n * (43 / ORDER_COUNT)) if status == "SHIPPED" else rng.randint(0, 6)
            placed = self.days_ago(max(age_days, 0), hours=rng.randint(0, 8))
            lines = []
            for key in rng.sample(stocked, k=min(len(stocked), rng.randint(1, 4))):
                product_pk, wh_pk = key
                row = self.state[key]
                product = by_pk[product_pk]
                wanted = rng.randint(1, 8) if product.unit_price >= 30 else rng.randint(5, 60)
                qty = min(wanted, row["available"])
                if qty <= 0 or any(l[0].pk == product_pk for l in lines):
                    continue
                lines.append((product, wh_by_pk[wh_pk], qty))
            if not lines:
                continue
            order = Order.objects.create(
                customer=rng.choice(customers), status=status, total_amount=0
            )
            total = Decimal("0")
            for product, wh, qty in lines:
                price = product.unit_price
                if status == "SHIPPED" and age_days > 25 and rng.random() < 0.4:
                    price = (price * Decimal("0.95")).quantize(Decimal("0.01"))  # older price
                OrderItem.objects.create(
                    order=order, product=product, quantity=qty, unit_price_at_order=price
                )
                total += price * qty
                row = self.row(product, wh)
                if status == "SHIPPED":
                    # as in the real flow: reserve takes it out of available, and
                    # shipping clears the reservation (delta 0, nothing left to move)
                    row["available"] -= qty
                    self.log(product, wh, "RESERVE", -qty, "ORDER", order.pk, placed)
                    self.log(product, wh, "SHIP", 0, "ORDER", order.pk, placed + timedelta(days=2))
                elif status in ("PENDING", "PAID"):
                    row["available"] -= qty
                    row["reserved"] += qty
                    self.log(product, wh, "RESERVE", -qty, "ORDER", order.pk, placed)
                else:  # cancelled: reserved, then released
                    self.log(product, wh, "RESERVE", -qty, "ORDER", order.pk, placed)
                    self.log(product, wh, "RELEASE", qty, "ORDER", order.pk, placed + timedelta(hours=20))
            order.total_amount = total
            order.save(update_fields=["total_amount"])
            updated = placed + timedelta(days=2 if status in ("PAID", "SHIPPED") else 0)
            orders.append((order, placed, updated))
        return orders

    def make_purchase_orders(self, products, warehouses, suppliers):
        rng = self.rng
        plan = [("RECEIVED", 30), ("RECEIVED", 14), ("ORDERED", -4), ("ORDERED", -9), ("DRAFT", None)]
        made = []
        for status, expected_in in plan:
            supplier, cats = rng.choice(suppliers)
            wh = rng.choice(warehouses)
            pool = [p for p in products if p.category in cats]
            created = self.days_ago(rng.randint(18, 40) if status == "RECEIVED" else rng.randint(2, 8))
            expected = (
                None if expected_in is None
                else created + timedelta(days=12) if status == "RECEIVED"
                else self.now + timedelta(days=-expected_in)
            )
            po = PurchaseOrder.objects.create(
                supplier=supplier, warehouse=wh, status=status, expected_at=expected
            )
            for k, product in enumerate(rng.sample(pool, k=min(len(pool), rng.randint(2, 4)))):
                ordered = rng.randint(100, 400) if product.unit_price < 30 else rng.randint(10, 40)
                received = 0
                if status == "RECEIVED":
                    received = ordered
                elif status == "ORDERED" and k == 0 and expected_in == -4:
                    received = ordered // 2  # a partial delivery
                PurchaseOrderItem.objects.create(
                    purchase_order=po, product=product, quantity_ordered=ordered,
                    quantity_received=received,
                    unit_cost=(product.unit_price * Decimal("0.62")).quantize(Decimal("0.01")),
                )
                if received:
                    self.row(product, wh)["available"] += received
                    when = expected if status == "RECEIVED" else self.days_ago(1)
                    self.log(product, wh, "RECEIPT", received, "PURCHASE_ORDER", po.pk, when)
            made.append((po, created))
        return made

    def write_inventory_and_ledger(self):
        inventory = {}
        for (product_pk, wh_pk), counts in self.state.items():
            inventory[(product_pk, wh_pk)] = Inventory.objects.create(
                product_id=product_pk, warehouse_id=wh_pk,
                quantity_available=counts["available"],
                quantity_reserved=counts["reserved"],
            )
        movements = [
            StockMovement(
                inventory=inventory[key], movement_type=kind, quantity_delta=delta,
                reference_type=ref_type, reference_id=ref_id,
            )
            for key, kind, delta, ref_type, ref_id, _ in self.events
        ]
        StockMovement.objects.bulk_create(movements)
        for movement, event in zip(movements, self.events):
            movement.created_at = min(event[5], self.now)
        StockMovement.objects.bulk_update(movements, ["created_at"])
        # Inventory.updated_at: the time of each row's last movement
        latest = {}
        for key, *_, when in self.events:
            latest[key] = max(latest.get(key, when), when)
        rows = list(inventory.values())
        by_key = {v.pk: k for k, v in inventory.items()}
        for row in rows:
            row.updated_at = min(latest[by_key[row.pk]], self.now)
        Inventory.objects.bulk_update(rows, ["updated_at"])

    def backdate(self, orders, purchase_orders):
        for order, placed, updated in orders:
            order.created_at = min(placed, self.now)
            order.updated_at = min(updated, self.now)
        Order.objects.bulk_update([o for o, *_ in orders], ["created_at", "updated_at"])
        for po, when in purchase_orders:
            po.created_at = when
        PurchaseOrder.objects.bulk_update([p for p, _ in purchase_orders], ["created_at"])
