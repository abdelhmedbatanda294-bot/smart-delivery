
from django.contrib import admin
from django.urls import include, path

from apps.ai_agent.views import ai_assistant
from apps.core.views import dashboard, drivers, create_driver
from apps.delivery.views import (
    assign_delivery,
    create_delivery,
    deliveries,
    delete_delivery,
    driver_deliveries,
    edit_delivery,
    my_deliveries,
    update_delivery_status,
)


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", dashboard, name="dashboard"),

    path("deliveries/", deliveries, name="deliveries"),
    path("deliveries/create/", create_delivery, name="create_delivery"),

    path(
        "deliveries/<int:delivery_id>/edit/",
        edit_delivery,
        name="edit_delivery",
    ),

    path(
        "deliveries/<int:delivery_id>/delete/",
        delete_delivery,
        name="delete_delivery",
    ),

    path(
        "deliveries/<int:delivery_id>/assign/",
        assign_delivery,
        name="assign_delivery",
    ),

    path(
        "deliveries/<int:delivery_id>/status/",
        update_delivery_status,
        name="update_delivery_status",
    ),

    path(
        "my-deliveries/",
        my_deliveries,
        name="my_deliveries",
    ),

    path(
        "driver-deliveries/",
        driver_deliveries,
        name="driver_deliveries",
    ),

    path("drivers/", drivers, name="drivers"),
    path("drivers/create/", create_driver, name="create_driver"),

    path("ai/", ai_assistant, name="ai_assistant"),

    path(
        "auth/",
        include("apps.authentication.urls"),
    ),

    path(
        "i18n/",
        include("django.conf.urls.i18n"),
    ),
]

