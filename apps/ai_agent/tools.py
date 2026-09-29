from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.delivery.models import (
    Delivery,
    DeliveryStatusHistory,
    Notification,
)


def get_delivery_summary(user):
    """
    Return a summary of delivery statuses.

    Only Admin and Manager users are allowed
    to access the global delivery summary.
    """

    if not user.is_authenticated:
        raise PermissionDenied(
            "Authentication is required."
        )

    if not (
        user.is_admin_role()
        or user.is_manager_role()
    ):
        raise PermissionDenied(
            "You do not have permission to access delivery statistics."
        )

    status_counts = Delivery.objects.values(
        "status"
    ).annotate(
        count=Count("id")
    )

    summary = {
        "total_deliveries": Delivery.objects.count(),
        "pending": 0,
        "assigned": 0,
        "picked_up": 0,
        "in_transit": 0,
        "delivered": 0,
    }

    for item in status_counts:

        status = item["status"]
        count = item["count"]

        if status in summary:
            summary[status] = count

    summary["active_deliveries"] = (
        summary["assigned"]
        + summary["picked_up"]
        + summary["in_transit"]
    )

    return summary


def update_delivery_status(
    user,
    delivery_id,
    new_status,
    note="",
):
    """
    Update a delivery status through the AI Agent.

    Only Admin and Manager users are allowed
    to perform this action.

    All tool parameters are validated before
    any database mutation takes place.
    """

    # =========================
    # Authentication
    # =========================

    if not user.is_authenticated:
        raise PermissionDenied(
            "Authentication is required."
        )


    # =========================
    # Permission
    # =========================

    if not (
        user.is_admin_role()
        or user.is_manager_role()
    ):
        raise PermissionDenied(
            "You do not have permission to update delivery status."
        )


    # =========================
    # Validate delivery_id
    # =========================

    if isinstance(delivery_id, bool):
        raise ValueError(
            "Delivery ID must be a positive integer."
        )

    try:
        delivery_id = int(delivery_id)

    except (TypeError, ValueError):
        raise ValueError(
            "Delivery ID must be a positive integer."
        )

    if delivery_id <= 0:
        raise ValueError(
            "Delivery ID must be a positive integer."
        )


    # =========================
    # Validate new_status
    # =========================

    if not isinstance(new_status, str):
        raise ValueError(
            "Delivery status must be a string."
        )

    new_status = new_status.strip().lower()

    valid_statuses = {
        Delivery.Status.PENDING,
        Delivery.Status.ASSIGNED,
        Delivery.Status.PICKED_UP,
        Delivery.Status.IN_TRANSIT,
        Delivery.Status.DELIVERED,
    }

    if new_status not in valid_statuses:
        raise ValueError(
            "Invalid delivery status. "
            "Allowed values are: pending, assigned, "
            "picked_up, in_transit, delivered."
        )


    # =========================
    # Validate note
    # =========================

    if note is None:
        note = ""

    if not isinstance(note, str):
        raise ValueError(
            "Note must be a string."
        )

    note = note.strip()

    if len(note) > 255:
        raise ValueError(
            "Note must not exceed 255 characters."
        )


    # =========================
    # Get delivery safely
    # =========================

    delivery = (
        Delivery.objects
        .select_related(
            "customer__user"
        )
        .filter(
            id=delivery_id
        )
        .first()
    )

    if delivery is None:
        raise ValueError(
            f"Delivery #{delivery_id} does not exist."
        )


    # =========================
    # No change required
    # =========================

    old_status = delivery.status

    if old_status == new_status:
        return {
            "success": True,
            "delivery_id": delivery.id,
            "old_status": old_status,
            "new_status": new_status,
            "message": "Delivery already has this status.",
        }


    # =========================
    # Database transaction
    # =========================

    with transaction.atomic():

        delivery.status = new_status

        update_fields = [
            "status",
            "updated_at",
        ]

        if new_status == Delivery.Status.DELIVERED:

            delivery.delivered_at = timezone.now()
            delivery.is_delayed = False

            update_fields.extend([
                "delivered_at",
                "is_delayed",
            ])

        delivery.save(
            update_fields=update_fields
        )


        DeliveryStatusHistory.objects.create(
            delivery=delivery,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            note=note,
        )


        Notification.objects.create(
            user=delivery.customer.user,
            title="Delivery Status Updated",
            message=(
                f"Your delivery #{delivery.id} "
                f"status changed to "
                f"{delivery.get_status_display()}."
            ),
            delivery=delivery,
        )


    return {
        "success": True,
        "delivery_id": delivery.id,
        "old_status": old_status,
        "new_status": new_status,
        "message": (
            f"Delivery #{delivery.id} status updated "
            f"from {old_status} to {new_status}."
        ),
    }