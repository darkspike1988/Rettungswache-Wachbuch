from functools import wraps
from urllib.parse import urlencode

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from .models import Membership

CONTENT_ROLES = {
    Membership.Role.MEMBER,
    Membership.Role.SHIFT_LEAD,
    Membership.Role.CASHIER,
    Membership.Role.ADMIN,
}


def get_membership(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return (
        Membership.objects.select_related("station", "user")
        .filter(user=user, is_active=True, station__is_active=True)
        .first()
    )


def membership_required(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                login_url = reverse("login")
                query = urlencode({"next": request.get_full_path()})
                return redirect(f"{login_url}?{query}")
            membership = get_membership(request.user)
            if not membership:
                return redirect("access")
            if allowed_roles is not None and membership.role not in allowed_roles:
                raise PermissionDenied
            request.membership = membership
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def station_module_required(field_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not getattr(request.membership.station, field_name):
                raise Http404
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
