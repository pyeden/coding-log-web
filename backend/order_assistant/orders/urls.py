from django.urls import path

from . import views

app_name = "order_api"

urlpatterns = [
    path("health", views.health, name="health"),
    path("meta", views.meta, name="meta"),
    path("requirements", views.requirements, name="requirements"),
    path(
        "requirements/<str:public_id>",
        views.requirement_detail,
        name="requirement_detail",
    ),
    path(
        "requirements/<str:public_id>/rounds",
        views.requirement_rounds,
        name="requirement_rounds",
    ),
    path(
        "requirements/<str:public_id>/status",
        views.requirement_status,
        name="requirement_status",
    ),
    path("quotes", views.quotes, name="quotes"),
    path("quotes/<int:quote_id>", views.quote_detail, name="quote_detail"),
]
