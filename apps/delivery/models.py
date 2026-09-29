from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="customer_profile",
    )
    company_name = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.company_name or self.user.get_full_name() or self.user.username


class DriverProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
    )
    vehicle_type = models.CharField(max_length=80, blank=True)
    vehicle_plate = models.CharField(max_length=30, blank=True)
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle_plate"],
                condition=~Q(vehicle_plate=""),
                name="unique_driver_vehicle_plate",
            )
        ]
        indexes = [
            models.Index(fields=["is_active", "is_available"]),
        ]

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Address(models.Model):
    label = models.CharField(max_length=80, blank=True)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=80, default="Egypt")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="addresses",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["city", "street"]
        indexes = [models.Index(fields=["city"])]

    def __str__(self):
        parts = [self.street, self.city, self.country]
        return ", ".join(part for part in parts if part)

    def as_text(self):
        return str(self)


class Delivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ASSIGNED = "assigned", "Assigned"
        PICKED_UP = "picked_up", "Picked Up"
        IN_TRANSIT = "in_transit", "In Transit"
        DELIVERED = "delivered", "Delivered"

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    pickup_address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="pickup_deliveries",
    )
    destination_address = models.ForeignKey(
        Address,
        on_delete=models.PROTECT,
        related_name="destination_deliveries",
    )
    package_description = models.CharField(max_length=255)
    weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    is_delayed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    expected_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expected_delivery_at"]),
            models.Index(fields=["is_delayed"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(pickup_address=models.F("destination_address")),
                name="delivery_pickup_differs_from_destination",
            )
        ]

    def __str__(self):
        return f"Delivery #{self.pk} ({self.get_status_display()})"

    def clean(self):
        if self.pickup_address_id and self.destination_address_id:
            if self.pickup_address_id == self.destination_address_id:
                raise ValidationError("Pickup and destination addresses must be different.")

    @property
    def current_assignment(self):
        return self.assignments.filter(is_current=True).select_related("driver__user").first()

    @property
    def assigned_driver(self):
        assignment = self.current_assignment
        return assignment.driver if assignment else None

    def refresh_delayed_flag(self, save=True):
        """Mark delayed if the expected time passed and the package is not delivered."""
        if self.status == self.Status.DELIVERED:
            self.is_delayed = False
        elif self.expected_delivery_at and timezone.now() > self.expected_delivery_at:
            self.is_delayed = True
        if save:
            self.save(update_fields=["is_delayed", "updated_at"])
        return self.is_delayed


class DeliveryAssignment(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["delivery"],
                condition=Q(is_current=True),
                name="one_current_assignment_per_delivery",
            )
        ]
        indexes = [
            models.Index(fields=["is_current", "driver"]),
        ]

    def __str__(self):
        prefix = "Current" if self.is_current else "Past"
        return f"{prefix} assignment of #{self.delivery_id} to {self.driver}"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self):
        return f"{self.title} -> {self.user}"


class DeliveryStatusHistory(models.Model):
    """Optional audit trail for status changes."""

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="delivery_status_changes",
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.delivery_id}: {self.from_status} -> {self.to_status}"
