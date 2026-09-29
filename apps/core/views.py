from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render

from apps.authentication.permissions import ops_required
from apps.delivery.forms import DriverAvailabilityForm
from apps.delivery.models import Delivery


User = get_user_model()


@login_required
def dashboard(request):

    if request.user.is_ops_staff():

        dashboard_deliveries = Delivery.objects.all()

    elif request.user.is_customer_role():

        dashboard_deliveries = Delivery.objects.filter(
            customer__user=request.user
        )

    elif request.user.is_driver_role():

        dashboard_deliveries = Delivery.objects.filter(
            assignments__driver__user=request.user
        ).distinct()

    else:

        dashboard_deliveries = Delivery.objects.none()

    total_deliveries = dashboard_deliveries.count()

    pending_deliveries = dashboard_deliveries.filter(
        status=Delivery.Status.PENDING
    ).count()

    delivered_deliveries = dashboard_deliveries.filter(
        status=Delivery.Status.DELIVERED
    ).count()

    active_deliveries = dashboard_deliveries.filter(
        status__in=[
            Delivery.Status.ASSIGNED,
            Delivery.Status.PICKED_UP,
            Delivery.Status.IN_TRANSIT,
        ]
    ).count()

    recent_deliveries = (
        dashboard_deliveries
        .select_related(
            "customer__user",
            "pickup_address",
            "destination_address",
        )
        .prefetch_related(
            "assignments__driver__user",
        )
        .order_by("-created_at")[:5]
    )

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_deliveries": total_deliveries,
            "pending_deliveries": pending_deliveries,
            "active_deliveries": active_deliveries,
            "delivered_deliveries": delivered_deliveries,
            "recent_deliveries": recent_deliveries,
        },
    )


@ops_required
def drivers(request):

    drivers_list = (
        User.objects
        .filter(role=User.Role.DRIVER)
        .select_related("driver_profile")
        .order_by("username")
    )

    return render(
        request,
        "drivers/drivers.html",
        {
            "drivers": drivers_list,
        },
    )


@ops_required
def create_driver(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        vehicle_form = DriverAvailabilityForm(request.POST)

        if not username or not password or not vehicle_form.is_valid():
            return render(
                request,
                "drivers/create_driver.html",
                {
                    "vehicle_form": vehicle_form,
                },
            )

        if User.objects.filter(username=username).exists():
            return render(
                request,
                "drivers/create_driver.html",
                {
                    "vehicle_form": vehicle_form,
                    "error": "Username already exists.",
                },
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=User.Role.DRIVER,
        )

        driver_profile = user.driver_profile

        driver_profile.vehicle_type = vehicle_form.cleaned_data["vehicle_type"]
        driver_profile.vehicle_plate = vehicle_form.cleaned_data["vehicle_plate"]
        driver_profile.is_available = vehicle_form.cleaned_data["is_available"]
        driver_profile.is_active = vehicle_form.cleaned_data["is_active"]
        driver_profile.notes = vehicle_form.cleaned_data["notes"]

        driver_profile.save()

        return redirect("drivers")

    else:
        vehicle_form = DriverAvailabilityForm()

    return render(
        request,
        "drivers/create_driver.html",
        {
            "vehicle_form": vehicle_form,
        },
    )