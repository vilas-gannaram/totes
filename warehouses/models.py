from uuid import uuid4

from django.db import models


# Create your models here.
class Warehouse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=244)
    location_code = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location_code} - {self.name}"
