from uuid import uuid4

from django.db import models


# Create your models here.
class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=244)
    category = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    reorder_point = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sku} - {self.name}"
