from decimal import Decimal

from django.db import transaction
from django.db.models import F

from inventory.models import Inventory, StockMovement

from .models import Order, OrderItem


class InsufficientStock(Exception):
    def __init__(self, product, wanted, available):
        self.product, self.wanted, self.available = product, wanted, available
        super().__init__(f"{product.sku}: wanted {wanted}, only {available} available")


@transaction.atomic
def place_order(customer, lines):
    """Create a PENDING order and reserve its stock.

    `lines` is a list of (product, quantity) with distinct products. Stock is
    taken from the warehouses holding the most of that product first, and each
    reservation is written to the ledger (available -> reserved). Raises
    InsufficientStock, rolling everything back, if any line can't be covered.
    """
    order = Order.objects.create(customer=customer, total_amount=0)
    total = Decimal("0")

    for product, quantity in lines:
        rows = list(
            Inventory.objects.select_for_update()
            .filter(product=product, quantity_available__gt=0)
            .order_by("-quantity_available", "warehouse__location_code")
        )
        available = sum(r.quantity_available for r in rows)
        if available < quantity:
            raise InsufficientStock(product, quantity, available)

        remaining = quantity
        for row in rows:
            take = min(row.quantity_available, remaining)
            Inventory.objects.filter(pk=row.pk).update(
                quantity_available=F("quantity_available") - take,
                quantity_reserved=F("quantity_reserved") + take,
            )
            StockMovement.objects.create(
                inventory=row,
                movement_type=StockMovement.MovementType.RESERVE,
                quantity_delta=-take,
                reference_type=StockMovement.ReferenceType.ORDER,
                reference_id=order.pk,
            )
            remaining -= take
            if not remaining:
                break

        OrderItem.objects.create(
            order=order, product=product, quantity=quantity, unit_price_at_order=product.unit_price
        )
        total += product.unit_price * quantity

    order.total_amount = total
    order.save(update_fields=["total_amount", "updated_at"])
    return order
