from django.contrib import admin

from .models import Inventory, StockMovement


# Register your models here.
@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "product",
        "warehouse",
        "quantity_available",
        "quantity_reserved",
        "updated_at",
    )
    list_filter = ("warehouse",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "inventory",
        "movement_type",
        "quantity_delta",
        "reference_type",
        "created_at",
    )
    list_filter = ("movement_type", "reference_type")
