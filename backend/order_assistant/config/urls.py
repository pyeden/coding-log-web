from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/order/", include("orders.urls")),
    path("", admin.site.urls),
]
