from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.authentication.models import User


def effective_role(user):
    if not user.is_authenticated:
        return None
    return user.effective_role


def can_manage_users(user):
    return bool(user.is_authenticated and user.is_admin_role())


def can_assign_deliveries(user):
    return bool(user.is_authenticated and user.is_ops_staff())


def can_manage_drivers(user):
    return bool(user.is_authenticated and user.is_ops_staff())


def can_update_any_status(user):
    return bool(user.is_authenticated and user.is_ops_staff())


def role_required(*roles):
    """Allow only the given roles (superusers count as admin)."""

    allowed = set(roles)

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.effective_role not in allowed:
                raise PermissionDenied("You do not have permission to open this page.")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(User.Role.ADMIN)
ops_required = role_required(User.Role.ADMIN, User.Role.MANAGER)
driver_required = role_required(User.Role.DRIVER)
customer_required = role_required(User.Role.CUSTOMER)
