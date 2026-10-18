from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.shortcuts import render

from inventory.models import Inventory, StockMovement
from inventory.views import with_status
from products.models import Product
from purchasing.models import PurchaseOrder, PurchaseOrderItem

MONEY = DecimalField(max_digits=16, decimal_places=2)
NEEDS_REORDER_LIMIT = 6
RECENT_MOVEMENTS_LIMIT = 5


def dashboard(request):
    stock = with_status(Inventory.objects.select_related("product", "warehouse"))

    counts = {row["status"]: row["n"] for row in stock.values("status").annotate(n=Count("id"))}
    stock_value = stock.aggregate(total=Sum("value"))["total"] or 0

    value_by_category = list(
        stock.values("product__category")
        .annotate(total=Sum("value"))
        .order_by("-total")
    )
    top_value = value_by_category[0]["total"] if value_by_category else 0
    categories = [
        {
            "name": row["product__category"] or "Uncategorised",
            "total": row["total"],
            "pct": round(row["total"] / top_value * 100) if top_value else 0,
        }
        for row in value_by_category
    ]

    open_orders = PurchaseOrder.objects.filter(status=PurchaseOrder.Status.ORDERED)
    incoming_value = PurchaseOrderItem.objects.filter(
        purchase_order__in=open_orders
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                (F("quantity_ordered") - F("quantity_received")) * F("unit_cost"),
                output_field=MONEY,
            )
        )
    )["total"] or 0

    return render(
        request,
        "dashboard.html",
        {
            "total_skus": Product.objects.count(),
            "stock_value": stock_value,
            "low_count": counts.get("low", 0),
            "out_count": counts.get("out", 0),
            "open_po_count": open_orders.count(),
            "incoming_value": incoming_value,
            "needs_reorder": stock.filter(status__in=["out", "low"]).order_by(
                "quantity_available", "product__name"
            )[:NEEDS_REORDER_LIMIT],
            "categories": categories,
            "movements": StockMovement.objects.select_related(
                "inventory__product", "inventory__warehouse"
            )[:RECENT_MOVEMENTS_LIMIT],
        },
    )
