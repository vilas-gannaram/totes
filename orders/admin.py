from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total_amount", "created_at")
    list_filter = ("status",)
    list_select_related = ("customer",)
    search_fields = ("customer__name", "customer__email")
    inlines = [OrderItemInline]
