from django.db import transaction
from django.db.models import F

from inventory.models import Inventory, StockMovement

from .models import PurchaseOrder, PurchaseOrderItem


class InvalidTransition(Exception):
    pass


class InvalidReceipt(Exception):
    pass


# status -> {target: button label}. Receiving moves ORDERED to RECEIVED on its own.
TRANSITIONS = {
    PurchaseOrder.Status.DRAFT: {
        PurchaseOrder.Status.ORDERED: "Mark as ordered",
        PurchaseOrder.Status.CANCELLED: "Cancel",
    },
    PurchaseOrder.Status.ORDERED: {PurchaseOrder.Status.CANCELLED: "Cancel"},
}


def allowed_transitions(po):
    return TRANSITIONS.get(po.status, {})


@transaction.atomic
def change_status(po, target):
    """DRAFT -> ORDERED, or cancel a DRAFT / an ORDERED PO nothing was received on."""
    po = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
    if target not in TRANSITIONS.get(po.status, {}):
        raise InvalidTransition(f"{po.get_status_display()} purchase orders can't become {target}")
    if target == PurchaseOrder.Status.CANCELLED and po.items.filter(quantity_received__gt=0).exists():
        raise InvalidTransition("Stock was already received on this purchase order")
    po.status = target
    po.save(update_fields=["status"])
    return po


@transaction.atomic
def receive(po, quantities):
    """Book received units into the PO's warehouse.

    `quantities` is {item pk: units received now}. Each unit count goes onto
    the item, into `Inventory.quantity_available` (the row is created if the
    product wasn't stocked there yet) and onto the ledger as a RECEIPT. The PO
    becomes RECEIVED once every line is complete. Raises InvalidReceipt, with
    nothing saved, for a non-ORDERED PO, an unknown item, or more than is outstanding.
    """
    po = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
    if po.status != PurchaseOrder.Status.ORDERED:
        raise InvalidReceipt("Only ordered purchase orders can receive stock")

    items = {i.pk: i for i in PurchaseOrderItem.objects.select_for_update().filter(purchase_order=po)}
    quantities = {pk: n for pk, n in quantities.items() if n}
    if not quantities:
        raise InvalidReceipt("Enter a quantity to receive")

    for pk, units in quantities.items():
        item = items.get(pk)
        if item is None:
            raise InvalidReceipt("Unknown item")
        outstanding = item.quantity_ordered - item.quantity_received
        if units < 0 or units > outstanding:
            raise InvalidReceipt(f"{item.product.sku}: {outstanding} outstanding, can't receive {units}")

    for pk, units in quantities.items():
        item = items[pk]
        row, _ = Inventory.objects.select_for_update().get_or_create(
            product=item.product, warehouse=po.warehouse
        )
        Inventory.objects.filter(pk=row.pk).update(quantity_available=F("quantity_available") + units)
        StockMovement.objects.create(
            inventory=row,
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity_delta=units,
            reference_type=StockMovement.ReferenceType.PURCHASE_ORDER,
            reference_id=po.pk,
        )
        PurchaseOrderItem.objects.filter(pk=pk).update(quantity_received=F("quantity_received") + units)

    if not PurchaseOrderItem.objects.filter(
        purchase_order=po, quantity_received__lt=F("quantity_ordered")
    ).exists():
        po.status = PurchaseOrder.Status.RECEIVED
        po.save(update_fields=["status"])
    return po
