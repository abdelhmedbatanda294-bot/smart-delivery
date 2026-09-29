"""Reusable delivery business rules. Views and AI tools both call this module."""

from django.db import transaction
from django.utils import timezone

from apps.authentication.models import User
from apps.authentication.permissions import (
    can_assign_deliveries,
    can_update_any_status,
)
from apps.delivery.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryStatusHistory,
    DriverProfile,
    Notification,
)

ALLOWED_TRANSITIONS = {
    Delivery.Status.PENDING: {Delivery.Status.ASSIGNED},
    Delivery.Status.ASSIGNED: {Delivery.Status.PICKED_UP},
    Delivery.Status.PICKED_UP: {Delivery.Status.IN_TRANSIT},
    Delivery.Status.IN_TRANSIT: {Delivery.Status.DELIVERED},
    Delivery.Status.DELIVERED: set(),
}

OPEN_STATUSES = {
    Delivery.Status.ASSIGNED,
    Delivery.Status.PICKED_UP,
    Delivery.Status.IN_TRANSIT,
}


class BusinessError(Exception):
    """Safe, user-facing business rule failure."""

    def __init__(self, message, code="business_error"):
        super().__init__(message)
        self.message = message
        self.code = code


def sync_delayed_deliveries():
    now = timezone.now()
    qs = Delivery.objects.exclude(status=Delivery.Status.DELIVERED).filter(
        expected_delivery_at__lt=now,
        is_delayed=False,
    )
    qs.update(is_delayed=True, updated_at=now)
    Delivery.objects.filter(status=Delivery.Status.DELIVERED, is_delayed=True).update(
        is_delayed=False,
        updated_at=now,
    )


def deliveries_visible_to(user):
    qs = Delivery.objects.select_related(
        "customer__user",
        "pickup_address",
        "destination_address",
    ).prefetch_related("assignments__driver__user")
    if user.is_ops_staff():
        return qs
    if user.is_driver_role():
        return qs.filter(assignments__driver__user=user, assignments__is_current=True).distinct()
    if user.is_customer_role():
        return qs.filter(customer__user=user)
    return qs.none()


def drivers_visible_to(user):
    qs = DriverProfile.objects.select_related("user")
    if user.is_ops_staff():
        return qs
    if user.is_driver_role():
        return qs.filter(user=user)
    return qs.none()


def get_delivery_or_error(delivery_id, user=None):
    try:
        delivery = Delivery.objects.select_related("customer__user").get(pk=delivery_id)
    except Delivery.DoesNotExist as exc:
        raise BusinessError("Delivery was not found.", "not_found") from exc
    if user is not None and not deliveries_visible_to(user).filter(pk=delivery.pk).exists():
        raise BusinessError("You are not allowed to access this delivery.", "forbidden")
    return delivery


def get_driver_or_error(driver_id):
    try:
        return DriverProfile.objects.select_related("user").get(pk=driver_id)
    except DriverProfile.DoesNotExist as exc:
        raise BusinessError("Driver was not found.", "not_found") from exc


def driver_has_open_assignment(driver):
    return driver.assignments.filter(
        is_current=True,
        delivery__status__in=OPEN_STATUSES,
    ).exists()


def is_driver_available(driver):
    return bool(driver.is_active and driver.is_available and not driver_has_open_assignment(driver))


def available_drivers_queryset():
    busy_ids = DeliveryAssignment.objects.filter(
        is_current=True,
        delivery__status__in=OPEN_STATUSES,
    ).values("driver_id")
    return DriverProfile.objects.select_related("user").filter(
        is_active=True,
        is_available=True,
    ).exclude(id__in=busy_ids)


def delayed_deliveries_queryset():
    sync_delayed_deliveries()
    return Delivery.objects.filter(is_delayed=True).exclude(status=Delivery.Status.DELIVERED)


def notify(user, title, message, delivery=None):
    if user is None:
        return None
    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        delivery=delivery,
    )


def serialize_driver(driver):
    return {
        "driver_id": driver.id,
        "user_id": driver.user_id,
        "name": driver.user.get_full_name() or driver.user.username,
        "phone": driver.user.phone,
        "vehicle_type": driver.vehicle_type,
        "vehicle_plate": driver.vehicle_plate,
        "is_available": is_driver_available(driver),
        "is_active": driver.is_active,
    }


def serialize_delivery(delivery):
    driver = delivery.assigned_driver
    return {
        "delivery_id": delivery.id,
        "status": delivery.status,
        "status_label": delivery.get_status_display(),
        "is_delayed": delivery.is_delayed,
        "package_description": delivery.package_description,
        "customer": delivery.customer.user.get_full_name() or delivery.customer.user.username,
        "driver_id": driver.id if driver else None,
        "driver_name": (driver.user.get_full_name() or driver.user.username) if driver else None,
        "expected_delivery_at": delivery.expected_delivery_at.isoformat()
        if delivery.expected_delivery_at
        else None,
    }


def _assert_can_assign(user):
    if not can_assign_deliveries(user):
        raise BusinessError("Only admins and managers can assign deliveries.", "forbidden")


def _assert_driver_assignable(driver):
    if not driver.is_active:
        raise BusinessError("This driver is inactive and cannot take deliveries.", "driver_inactive")
    if not is_driver_available(driver):
        raise BusinessError("This driver is not currently available.", "driver_unavailable")


@transaction.atomic
def assign_delivery(user, delivery_id, driver_id):
    _assert_can_assign(user)
    delivery = get_delivery_or_error(delivery_id)
    driver = get_driver_or_error(driver_id)

    if delivery.status != Delivery.Status.PENDING:
        raise BusinessError(
            "Only pending deliveries can be assigned. Use reassign for an already assigned delivery.",
            "invalid_state",
        )
    if delivery.current_assignment:
        raise BusinessError("This delivery already has a driver.", "already_assigned")

    _assert_driver_assignable(driver)

    assignment = DeliveryAssignment.objects.create(
        delivery=delivery,
        driver=driver,
        assigned_by=user,
        is_current=True,
        note="Initial assignment",
    )
    _apply_status(user, delivery, Delivery.Status.ASSIGNED, note="Driver assigned")
    notify(
        driver.user,
        "New delivery assigned",
        f"You were assigned delivery #{delivery.id}.",
        delivery,
    )
    notify(
        delivery.customer.user,
        "Driver assigned",
        f"Delivery #{delivery.id} was assigned to a driver.",
        delivery,
    )
    return assignment


@transaction.atomic
def reassign_delivery(user, delivery_id, new_driver_id):
    _assert_can_assign(user)
    delivery = get_delivery_or_error(delivery_id)
    new_driver = get_driver_or_error(new_driver_id)

    if delivery.status != Delivery.Status.ASSIGNED:
        raise BusinessError(
            "A delivery can only be reassigned while its status is Assigned.",
            "invalid_state",
        )

    current = delivery.current_assignment
    if current is None:
        raise BusinessError("This delivery has no current driver to replace.", "not_assigned")
    if current.driver_id == new_driver.id:
        raise BusinessError("The delivery is already assigned to this driver.", "same_driver")

    _assert_driver_assignable(new_driver)

    current.is_current = False
    current.unassigned_at = timezone.now()
    current.save(update_fields=["is_current", "unassigned_at"])

    assignment = DeliveryAssignment.objects.create(
        delivery=delivery,
        driver=new_driver,
        assigned_by=user,
        is_current=True,
        note="Reassignment",
    )
    notify(
        current.driver.user,
        "Delivery reassigned",
        f"Delivery #{delivery.id} was moved to another driver.",
        delivery,
    )
    notify(
        new_driver.user,
        "New delivery assigned",
        f"You were assigned delivery #{delivery.id} (reassignment).",
        delivery,
    )
    return assignment


def can_driver_update(user, delivery):
    if not user.is_driver_role():
        return False
    assignment = delivery.current_assignment
    return bool(assignment and assignment.driver.user_id == user.id)


def _apply_status(user, delivery, new_status, note=""):
    old_status = delivery.status
    if old_status == new_status:
        raise BusinessError("The delivery is already in that status.", "same_status")
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise BusinessError(
            f"Invalid status change: {old_status} cannot go directly to {new_status}.",
            "invalid_transition",
        )

    delivery.status = new_status
    update_fields = ["status", "updated_at"]
    if new_status == Delivery.Status.DELIVERED:
        delivery.delivered_at = timezone.now()
        delivery.is_delayed = False
        update_fields.extend(["delivered_at", "is_delayed"])
    delivery.save(update_fields=update_fields)

    DeliveryStatusHistory.objects.create(
        delivery=delivery,
        from_status=old_status,
        to_status=new_status,
        changed_by=user,
        note=note,
    )
    notify(
        delivery.customer.user,
        "Delivery status updated",
        f"Delivery #{delivery.id} is now {delivery.get_status_display()}.",
        delivery,
    )
    if delivery.assigned_driver:
        notify(
            delivery.assigned_driver.user,
            "Delivery status updated",
            f"Delivery #{delivery.id} is now {delivery.get_status_display()}.",
            delivery,
        )


@transaction.atomic
def update_delivery_status(user, delivery_id, new_status):
    delivery = get_delivery_or_error(delivery_id, user=user)
    if new_status not in Delivery.Status.values:
        raise BusinessError("Unknown delivery status.", "invalid_status")

    if can_update_any_status(user):
        pass
    elif can_driver_update(user, delivery):
        pass
    else:
        raise BusinessError("You cannot update this delivery status.", "forbidden")

    _apply_status(user, delivery, new_status, note="Status update")
    return delivery


def dashboard_stats(user):
    sync_delayed_deliveries()
    qs = deliveries_visible_to(user)
    stats = {
        "total": qs.count(),
        "pending": qs.filter(status=Delivery.Status.PENDING).count(),
        "assigned": qs.filter(status=Delivery.Status.ASSIGNED).count(),
        "picked_up": qs.filter(status=Delivery.Status.PICKED_UP).count(),
        "in_transit": qs.filter(status=Delivery.Status.IN_TRANSIT).count(),
        "delivered": qs.filter(status=Delivery.Status.DELIVERED).count(),
        "delayed": qs.filter(is_delayed=True).exclude(status=Delivery.Status.DELIVERED).count(),
        "available_drivers": available_drivers_queryset().count() if user.is_ops_staff() else None,
    }
    return stats
