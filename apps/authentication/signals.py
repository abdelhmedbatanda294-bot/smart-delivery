from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.authentication.models import User


@receiver(post_save, sender=User)
def ensure_role_profile(sender, instance, created, **kwargs):
    """Create the matching profile when a user is saved with that role."""
    from apps.delivery.models import CustomerProfile, DriverProfile

    if instance.role == User.Role.CUSTOMER:
        CustomerProfile.objects.get_or_create(user=instance)
    if instance.role == User.Role.DRIVER:
        DriverProfile.objects.get_or_create(user=instance)
