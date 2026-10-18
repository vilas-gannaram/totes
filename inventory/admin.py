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
    list_select_related = ("product", "warehouse")
    search_fields = ("product__sku", "product__name")


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
    list_select_related = ("inventory__product", "inventory__warehouse")
    search_fields = ("inventory__product__sku", "inventory__product__name")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
