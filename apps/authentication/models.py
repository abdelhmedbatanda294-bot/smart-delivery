from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Application user with a single primary role."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        DRIVER = "driver", "Driver"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
    )
    phone = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def effective_role(self):
        if self.is_superuser:
            return self.Role.ADMIN
        return self.role

    def is_admin_role(self):
        return self.effective_role == self.Role.ADMIN

    def is_manager_role(self):
        return self.effective_role == self.Role.MANAGER

    def is_ops_staff(self):
        return self.effective_role in {self.Role.ADMIN, self.Role.MANAGER}

    def is_driver_role(self):
        return self.effective_role == self.Role.DRIVER

    def is_customer_role(self):
        return self.effective_role == self.Role.CUSTOMER
