from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

PARTNER = "Partner"
STAFF = "Staff"
CUSTOMER = "Customer"


def in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def has_role(user, *roles):
    return user.is_superuser or any(in_group(user, role) for role in roles)


def role_required(*roles):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have access to that page.")
            return redirect("dashboard")

        return wrapped

    return decorator


def role_home(user):
    if has_role(user, PARTNER):
        return "partner_dashboard"
    if has_role(user, STAFF):
        return "staff_dashboard"
    return "customer_dashboard"
