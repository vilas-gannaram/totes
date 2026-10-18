from uuid import uuid4

from django.db import models


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        ORDERED = "ORDERED"
        RECEIVED = "RECEIVED"
        CANCELLED = "CANCELLED"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT)
    warehouse = models.ForeignKey("warehouses.Warehouse", on_delete=models.PROTECT)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    expected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{str(self.id)[:8]} - {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name="items"
    )
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_order", "product"],
                name="unique_purchaseorderitem_purchase_order_product",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_ordered__gt=0),
                name="purchaseorderitem_quantity_ordered_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_received__gte=0),
                name="purchaseorderitem_quantity_received_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_cost__gte=0),
                name="purchaseorderitem_unit_cost_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.quantity_ordered} x {self.product.sku}"
