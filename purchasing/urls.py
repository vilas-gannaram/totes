from django.urls import path

from . import views

urlpatterns = [
    path("", views.purchase_order_list, name="purchase-order-list"),
    path("new/", views.purchase_order_new, name="purchase-order-new"),
    path("<uuid:pk>/", views.purchase_order_detail, name="purchase-order-detail"),
    path("<uuid:pk>/edit/", views.purchase_order_edit, name="purchase-order-edit"),
    path("<uuid:pk>/status/", views.purchase_order_status, name="purchase-order-status"),
    path("<uuid:pk>/receive/", views.purchase_order_receive, name="purchase-order-receive"),
]
