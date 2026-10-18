from uuid import uuid4

from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"
        SHIPPED = "SHIPPED"
        CANCELLED = "CANCELLED"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_amount__gte=0),
                name="order_total_amount_gte_0",
            )
        ]

    def __str__(self):
        return f"{str(self.id)[:8]} - {self.customer.name}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price_at_order = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_orderitem_order_product",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="orderitem_quantity_gt_0"
            ),
            models.CheckConstraint(
                condition=models.Q(unit_price_at_order__gte=0),
                name="orderitem_unit_price_at_order_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product.sku}"
