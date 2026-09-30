
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.ai_agent.tools import (
    get_delivery_summary,
    update_delivery_status,
)
from apps.delivery.models import (
    Address,
    CustomerProfile,
    Delivery,
)


class AIToolsTestCase(TestCase):

    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="test_admin",
            password="TestAdmin123!",
            role="admin",
        )

        self.customer = User.objects.create_user(
            username="test_customer",
            password="TestCustomer123!",
            role="customer",
        )

        self.customer_profile = CustomerProfile.objects.get(
            user=self.customer
        )

        self.pickup_address = Address.objects.create(
            label="Test Pickup",
            street="10 Test Street",
            city="Cairo",
            state="Cairo",
            postal_code="11511",
            country="Egypt",
            created_by=self.admin,
        )

        self.destination_address = Address.objects.create(
            label="Test Destination",
            street="20 Test Street",
            city="Giza",
            state="Giza",
            postal_code="12511",
            country="Egypt",
            created_by=self.admin,
        )

        self.delivery = Delivery.objects.create(
            customer=self.customer_profile,
            pickup_address=self.pickup_address,
            destination_address=self.destination_address,
            package_description="Test Package",
            weight_kg=5,
            status="pending",
            is_delayed=False,
        )

    def test_admin_can_get_delivery_summary(self):
        result = get_delivery_summary(self.admin)

        self.assertEqual(
            result["total_deliveries"],
            1,
        )

        self.assertEqual(
            result["active_deliveries"],
            0,
        )

    def test_customer_cannot_get_delivery_summary(self):
        with self.assertRaises(PermissionDenied):
            get_delivery_summary(self.customer)

    def test_admin_can_update_delivery_status(self):
        result = update_delivery_status(
            user=self.admin,
            delivery_id=self.delivery.id,
            new_status="picked_up",
        )

        self.assertTrue(result["success"])

        self.delivery.refresh_from_db()

        self.assertEqual(
            self.delivery.status,
            "picked_up",
        )

    def test_invalid_delivery_id(self):
        with self.assertRaises(ValueError):
            update_delivery_status(
                user=self.admin,
                delivery_id=999999,
                new_status="delivered",
            )

