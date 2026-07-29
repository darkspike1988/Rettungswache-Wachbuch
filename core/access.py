from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect

from .models import Membership


CONTENT_ROLES = {
    Membership.Role.MEMBER,
    Membership.Role.SHIFT_LEAD,
    Membership.Role.CASHIER,
    Membership.Role.ADMIN,
}

SESSION_STATION_KEY = "active_station_id"


def available_memberships(user):
    """Alle aktiven Mitgliedschaften einer Person - im Rettungsdienst
    arbeiten Springer regelmaessig auf mehreren Wachen."""
    if not getattr(user, "is_authenticated", False):
        return Membership.objects.none()
    return (
        Membership.objects.select_related("station", "user")
        .filter(user=user, is_active=True, station__is_active=True)
        .order_by("station__name")
    )


def get_membership(user, session=None):
    """Die gerade gewaehlte Mitgliedschaft. Ohne Auswahl gilt die erste;
    die Wahl haelt sich in der Session."""
    memberships = available_memberships(user)
    if session is not None:
        chosen = session.get(SESSION_STATION_KEY)
        if chosen:
            for membership in memberships:
                if membership.station_id == chosen:
                    return membership
            # Zugang zur gemerkten Wache entzogen: Auswahl verwerfen.
            session.pop(SESSION_STATION_KEY, None)
    return memberships.first()


def membership_required(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("access")
            membership = get_membership(request.user, request.session)
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
