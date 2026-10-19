from django.urls import path

from . import views

urlpatterns = [
    path("", views.order_list, name="order-list"),
    path("new/", views.order_new, name="order-new"),
    path("<uuid:pk>/", views.order_detail, name="order-detail"),
]
