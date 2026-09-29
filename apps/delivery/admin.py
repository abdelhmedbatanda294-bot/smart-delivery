
from django.contrib import admin

from .models import (
    Address,
    CustomerProfile,
    Delivery,
    DeliveryAssignment,
    DeliveryStatusHistory,
    DriverProfile,
    Notification,
)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company_name",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "company_name",
    )


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "vehicle_type",
        "vehicle_plate",
        "is_available",
        "is_active",
    )

    list_filter = (
        "is_available",
        "is_active",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "vehicle_plate",
    )


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "street",
        "city",
        "state",
        "country",
        "created_by",
    )

    list_filter = (
        "city",
        "country",
    )

    search_fields = (
        "label",
        "street",
        "city",
        "postal_code",
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "status",
        "is_delayed",
        "expected_delivery_at",
        "created_at",
    )

    list_filter = (
        "status",
        "is_delayed",
    )

    search_fields = (
        "package_description",
        "customer__user__username",
        "customer__company_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "delivered_at",
    )


@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "delivery",
        "driver",
        "is_current",
        "assigned_by",
        "assigned_at",
    )

    list_filter = (
        "is_current",
    )

    search_fields = (
        "driver__user__username",
        "driver__user__first_name",
        "driver__user__last_name",
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "delivery",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
    )

    search_fields = (
        "title",
        "message",
        "user__username",
    )


@admin.register(DeliveryStatusHistory)
class DeliveryStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "delivery",
        "from_status",
        "to_status",
        "changed_by",
        "created_at",
    )

    list_filter = (
        "to_status",
    )

    search_fields = (
        "delivery__id",
        "changed_by__username",
    )
