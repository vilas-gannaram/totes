from django.contrib import admin

from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    autocomplete_fields = ("product",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "supplier", "warehouse", "status", "expected_at", "created_at")
    list_filter = ("status", "warehouse")
    list_select_related = ("supplier", "warehouse")
    search_fields = ("supplier__name", "supplier__email")
    inlines = [PurchaseOrderItemInline]
