from django.urls import path

from . import views

urlpatterns = [path("", views.warehouse_list, name="warehouse-list")]
