from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum

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


class InvalidTransition(Exception):
    pass


# status -> {target: button label}
TRANSITIONS = {
    Order.Status.PENDING: {Order.Status.PAID: "Mark as paid", Order.Status.CANCELLED: "Cancel order"},
    Order.Status.PAID: {Order.Status.SHIPPED: "Mark as shipped", Order.Status.CANCELLED: "Cancel order"},
}


def allowed_transitions(order):
    return TRANSITIONS.get(order.status, {})


def _held_stock(order):
    """{inventory_id: units still reserved for this order}, from its ledger rows."""
    held = {}
    rows = (
        StockMovement.objects.filter(
            reference_type=StockMovement.ReferenceType.ORDER,
            reference_id=order.pk,
            movement_type__in=[StockMovement.MovementType.RESERVE, StockMovement.MovementType.RELEASE],
        )
        .values("inventory_id")
        .annotate(net=Sum("quantity_delta"))
    )
    for r in rows:
        if r["net"]:
            held[r["inventory_id"]] = -r["net"]
    return held


@transaction.atomic
def change_status(order, target):
    """Move an order to `target`, adjusting stock. Raises InvalidTransition.

    PENDING -> PAID: no stock change.
    -> SHIPPED: the reserved units leave the warehouse (reserved goes down). They
        were already taken out of `quantity_available` when reserved, so the SHIP
        ledger row has delta 0 and only marks where the units left from.
    -> CANCELLED: reserved units go back to available (RELEASE rows).
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if target not in TRANSITIONS.get(order.status, {}):
        raise InvalidTransition(f"{order.get_status_display()} orders can't become {target}")

    if target != Order.Status.PAID:
        for inventory_id, units in _held_stock(order).items():
            if target == Order.Status.SHIPPED:
                Inventory.objects.filter(pk=inventory_id).update(
                    quantity_reserved=F("quantity_reserved") - units
                )
                kind, delta = StockMovement.MovementType.SHIP, 0
            else:
                Inventory.objects.filter(pk=inventory_id).update(
                    quantity_available=F("quantity_available") + units,
                    quantity_reserved=F("quantity_reserved") - units,
                )
                kind, delta = StockMovement.MovementType.RELEASE, units
            StockMovement.objects.create(
                inventory_id=inventory_id,
                movement_type=kind,
                quantity_delta=delta,
                reference_type=StockMovement.ReferenceType.ORDER,
                reference_id=order.pk,
            )

    order.status = target
    order.save(update_fields=["status", "updated_at"])
    return order
