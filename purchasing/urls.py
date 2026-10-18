from django.urls import path

from . import views

urlpatterns = [path("", views.purchase_order_list, name="purchase-order-list")]
