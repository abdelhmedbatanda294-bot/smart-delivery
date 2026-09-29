from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from apps.authentication.forms import (
    CustomerRegistrationForm,
    ProfileForm,
    StaffUserCreateForm,
    StyledAuthenticationForm,
)
from apps.authentication.models import User
from apps.authentication.permissions import admin_required, can_manage_users
from apps.delivery.forms import DriverAvailabilityForm
from apps.delivery.models import Notification


class AppLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class AppLogoutView(LogoutView):
    next_page = reverse_lazy("authentication:login")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = CustomerRegistrationForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Account created. You can log in now.")
        return redirect("authentication:login")

    return render(
        request,
        "registration/register.html",
        {"form": form},
    )


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    driver_form = None

    if request.user.is_driver_role():
        driver_form = DriverAvailabilityForm(
            request.POST or None,
            instance=request.user.driver_profile,
        )

        if "is_active" in driver_form.fields:
            driver_form.fields.pop("is_active")

    if request.method == "POST":
        ok = form.is_valid()

        if driver_form:
            ok = ok and driver_form.is_valid()

        if ok:
            form.save()

            if driver_form:
                driver_form.save()

            messages.success(request, "Profile updated.")
            return redirect("authentication:profile")

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "driver_form": driver_form,
        },
    )


@login_required
def notification_list(request):
    notes = Notification.objects.filter(user=request.user)

    return render(
        request,
        "accounts/notifications.html",
        {"notifications": notes},
    )


@login_required
def mark_notification_read(request, pk):
    note = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user,
    )

    note.is_read = True
    note.save(update_fields=["is_read"])

    return redirect("authentication:notifications")


@admin_required
def user_list(request):
    users = User.objects.all().order_by("role", "username")

    return render(
        request,
        "accounts/user_list.html",
        {"users": users},
    )


@admin_required
def user_create(request):
    form = StaffUserCreateForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "User created.")
        return redirect("authentication:user_list")

    return render(
        request,
        "accounts/user_form.html",
        {"form": form},
    )
