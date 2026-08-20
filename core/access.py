from functools import wraps
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse

from .models import Membership, RegistrationRequest


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


def pending_registrations_for_station(station):
    """Pending sign-ups that named this station. Cross-station rows stay hidden."""
    return (
        RegistrationRequest.objects.filter(
            status=RegistrationRequest.Status.PENDING,
            user__is_active=True,
            preferred_station=station,
        )
        .select_related("user", "preferred_station")
        .order_by("created_at")
    )


def users_awaiting_station_access(station):
    """Active users without membership whose pending request is this station.

    Users with a pending request for another station, or without a named
    station, stay out of this station's assignment list. Accounts without any
    pending request remain assignable (admin-created users waiting for a
    membership).
    """
    pending_elsewhere = (
        RegistrationRequest.objects.filter(
            status=RegistrationRequest.Status.PENDING,
        )
        .filter(Q(preferred_station__isnull=True) | ~Q(preferred_station=station))
        .values_list("user_id", flat=True)
    )
    return (
        User.objects.filter(is_active=True)
        .exclude(station_memberships__is_active=True)
        .exclude(pk__in=pending_elsewhere)
        .order_by("first_name", "username")
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
