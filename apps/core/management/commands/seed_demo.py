from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.delivery.models import (
    CustomerProfile,
    DriverProfile,
)


class Command(BaseCommand):
    help = "Create demo users and profiles"

    def handle(self, *args, **options):
        User = get_user_model()

        admin, created = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "role": "admin",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            admin.set_password("DemoAdmin123!")
            admin.save()

        customer, created = User.objects.get_or_create(
            username="demo_customer",
            defaults={
                "role": "customer",
            },
        )

        if created:
            customer.set_password("DemoCustomer123!")
            customer.save()

        driver, created = User.objects.get_or_create(
            username="demo_driver",
            defaults={
                "role": "driver",
            },
        )

        if created:
            driver.set_password("DemoDriver123!")
            driver.save()

        CustomerProfile.objects.get_or_create(
            user=customer,
            defaults={
                "company_name": "Demo Customer",
                "notes": "Demo customer for testing",
            },
        )

        DriverProfile.objects.get_or_create(
            user=driver,
            defaults={
                "vehicle_type": "Motorcycle",
                "vehicle_plate": "SD-1001",
                "is_available": True,
                "is_active": True,
                "notes": "Demo driver for testing",
            },
        )

        self.stdout.write(
            self.style.SUCCESS("Demo data created successfully.")
        )