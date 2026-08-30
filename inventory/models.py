from uuid import uuid4

from django.db import models


# Create your models here.
class Inventory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    warehouse = models.ForeignKey("warehouses.Warehouse", on_delete=models.CASCADE)
    quantity_available = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_inventory_product_warehouse",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_available__gte=0),
                name="inventory_quantity_available_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_reserved__gte=0),
                name="inventory_quantity_reserved_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.warehouse.location_code}"


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RECEIPT = "RECEIPT"
        RESERVE = "RESERVE"
        RELEASE = "RELEASE"
        SHIP = "SHIP"
        ADJUST = "ADJUST"

    class ReferenceType(models.TextChoices):
        ORDER = "ORDER"
        PURCHASE_ORDER = "PURCHASE_ORDER"
        MANUAL = "MANUAL"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name="movements"
    )
    movement_type = models.CharField(max_length=16, choices=MovementType.choices)
    quantity_delta = models.IntegerField()
    reference_type = models.CharField(max_length=16, choices=ReferenceType.choices)
    reference_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} {self.quantity_delta} - {self.inventory}"
