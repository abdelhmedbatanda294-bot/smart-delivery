
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.authentication.permissions import ops_required
from apps.delivery.forms import (
    DeliveryAssignmentForm,
    DeliveryCreateForm,
    DeliveryStatusForm,
    DeliveryUpdateForm,
)
from apps.delivery.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryStatusHistory,
    DriverProfile,
    Notification,
)


@ops_required
def deliveries(request):
    status = request.GET.get("status", "").strip()

    deliveries_list = (
        Delivery.objects
        .select_related(
            "customer__user",
            "pickup_address",
            "destination_address",
        )
        .prefetch_related("assignments__driver__user")
        .order_by("-created_at")
    )

    if status in dict(Delivery.Status.choices):
        deliveries_list = deliveries_list.filter(status=status)

    available_drivers = (
        DriverProfile.objects
        .filter(
            is_active=True,
            is_available=True,
            user__role="driver",
        )
        .select_related("user")
        .order_by("user__username")
    )

    return render(
        request,
        "deliveries/deliveries.html",
        {
            "deliveries": deliveries_list,
            "selected_status": status,
            "available_drivers": available_drivers,
        },
    )


@login_required
def create_delivery(request):
    if not (
        request.user.is_admin_role()
        or request.user.is_manager_role()
        or request.user.is_customer_role()
    ):
        raise PermissionDenied(
            "You do not have permission to create a delivery."
        )

    if request.method == "POST":
        form = DeliveryCreateForm(request.POST)

        if form.is_valid():
            delivery = form.save_with_customer(request.user)

            Notification.objects.create(
                user=request.user,
                title="Delivery Created",
                message=(
                    f"Your delivery order #{delivery.id} "
                    f"has been created successfully."
                ),
                delivery=delivery,
            )

            if request.user.is_ops_staff():
                return redirect("deliveries")

            return redirect("dashboard")

    else:
        form = DeliveryCreateForm()

    return render(
        request,
        "deliveries/create_delivery.html",
        {"form": form},
    )


@ops_required
def edit_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related(
            "customer__user",
            "pickup_address",
            "destination_address",
        ),
        id=delivery_id,
    )

    if request.method == "POST":
        form = DeliveryUpdateForm(
            request.POST,
            instance=delivery,
        )

        if form.is_valid():
            form.save()
            return redirect("deliveries")

    else:
        form = DeliveryUpdateForm(
            instance=delivery,
        )

    return render(
        request,
        "deliveries/edit_delivery.html",
        {
            "form": form,
            "delivery": delivery,
        },
    )


@ops_required
def delete_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery,
        id=delivery_id,
    )

    if request.method == "POST":
        delivery.delete()
        return redirect("deliveries")

    return render(
        request,
        "deliveries/delete_delivery.html",
        {"delivery": delivery},
    )


@ops_required
def assign_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related("customer__user"),
        id=delivery_id,
    )

    if request.method != "POST":
        return redirect("deliveries")

    form = DeliveryAssignmentForm(request.POST)

    if not form.is_valid():
        return redirect("deliveries")

    driver = form.cleaned_data["driver"]
    note = form.cleaned_data["note"]

    with transaction.atomic():
        old_assignment = (
            DeliveryAssignment.objects
            .filter(
                delivery=delivery,
                is_current=True,
            )
            .first()
        )

        if old_assignment:
            old_assignment.is_current = False
            old_assignment.unassigned_at = timezone.now()
            old_assignment.save(
                update_fields=[
                    "is_current",
                    "unassigned_at",
                ]
            )

        DeliveryAssignment.objects.create(
            delivery=delivery,
            driver=driver,
            assigned_by=request.user,
            note=note,
        )

        old_status = delivery.status
        delivery.status = Delivery.Status.ASSIGNED

        delivery.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        DeliveryStatusHistory.objects.create(
            delivery=delivery,
            from_status=old_status,
            to_status=Delivery.Status.ASSIGNED,
            changed_by=request.user,
            note=note,
        )

        Notification.objects.create(
            user=driver.user,
            title="New Delivery Assigned",
            message=(
                f"Delivery #{delivery.id} has been assigned to you."
            ),
            delivery=delivery,
        )

        Notification.objects.create(
            user=delivery.customer.user,
            title="Driver Assigned",
            message=(
                f"A driver has been assigned to your delivery "
                f"#{delivery.id}."
            ),
            delivery=delivery,
        )

    return redirect("deliveries")


@login_required
def driver_deliveries(request):
    if not request.user.is_driver_role():
        raise PermissionDenied(
            "You do not have permission to open this page."
        )

    deliveries_list = (
        Delivery.objects
        .filter(
            assignments__driver__user=request.user,
            assignments__is_current=True,
        )
        .select_related(
            "customer__user",
            "pickup_address",
            "destination_address",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "deliveries/driver_deliveries.html",
        {"deliveries": deliveries_list},
    )


@login_required
def update_delivery_status(request, delivery_id):
    if not request.user.is_driver_role():
        raise PermissionDenied(
            "Only drivers can update delivery status."
        )

    delivery = get_object_or_404(
        Delivery.objects.filter(
            assignments__driver__user=request.user,
            assignments__is_current=True,
        ),
        id=delivery_id,
    )

    if request.method != "POST":
        return redirect("driver_deliveries")

    form = DeliveryStatusForm(request.POST)

    if not form.is_valid():
        return redirect("driver_deliveries")

    new_status = form.cleaned_data["status"]
    note = form.cleaned_data["note"]

    allowed_transitions = {
        Delivery.Status.ASSIGNED: [
            Delivery.Status.PICKED_UP,
        ],
        Delivery.Status.PICKED_UP: [
            Delivery.Status.IN_TRANSIT,
        ],
        Delivery.Status.IN_TRANSIT: [
            Delivery.Status.DELIVERED,
        ],
    }

    if new_status not in allowed_transitions.get(
        delivery.status,
        [],
    ):
        return redirect("driver_deliveries")

    old_status = delivery.status

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
            changed_by=request.user,
            note=note,
        )

        Notification.objects.create(
            user=delivery.customer.user,
            title="Delivery Status Updated",
            message=(
                f"Your delivery #{delivery.id} status changed to "
                f"{delivery.get_status_display()}."
            ),
            delivery=delivery,
        )

    return redirect("driver_deliveries")


@login_required
def my_deliveries(request):
    if not request.user.is_customer_role():
        raise PermissionDenied(
            "You do not have permission to open this page."
        )

    deliveries_list = (
        Delivery.objects
        .filter(
            customer__user=request.user,
        )
        .select_related(
            "customer__user",
            "pickup_address",
            "destination_address",
        )
        .prefetch_related(
            "assignments__driver__user",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "deliveries/my_deliveries.html",
        {"deliveries": deliveries_list},
    )
