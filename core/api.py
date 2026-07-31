"""Read-only JSON API for the mobile client (iOS/Android).

The API deliberately mirrors the station-scoped access rules of the HTML views and
exposes only data the signed-in member may already see in the interface. It never
returns patient, health or operational data and performs no writes, so it stays
inside the documented privacy boundary of the Wachbuch.
"""

from functools import wraps

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .access import CONTENT_ROLES, get_membership
from .models import CalendarEvent, CoffeeEntry, HandoverEntry, Membership
from .views import prioritized_handovers

API_VERSION = "1.0"


def _error(status, message):
    return JsonResponse({"error": message}, status=status)


def api_member_view(allowed_roles=CONTENT_ROLES):
    """Session-authenticate an API view and attach the caller's membership.

    Unlike the HTML ``membership_required`` decorator this returns JSON error
    responses (401/403) instead of redirects, which suits a native client.
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_GET
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return _error(401, "Anmeldung erforderlich.")
            membership = get_membership(request.user)
            if membership is None:
                return _error(403, "Keine aktive Wachenmitgliedschaft.")
            if allowed_roles is not None and membership.role not in allowed_roles:
                return _error(403, "Fuer diese Rolle nicht freigegeben.")
            request.membership = membership
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


@require_GET
def status(request):
    """Auth-optional metadata endpoint the client can call without a membership."""
    membership = get_membership(request.user)
    payload = {
        "api_version": API_VERSION,
        "authenticated": request.user.is_authenticated,
        "has_membership": membership is not None,
    }
    if membership is not None:
        payload["station"] = membership.station.name
        payload["role"] = membership.role
    return JsonResponse(payload)


def _handover_json(handover):
    return {
        "id": handover.pk,
        "title": handover.title,
        "category": handover.category,
        "category_label": handover.get_category_display(),
        "priority": handover.priority,
        "priority_label": handover.get_priority_display(),
        "status": handover.status,
        "status_label": handover.get_status_display(),
        "updated_at": handover.updated_at.isoformat(),
    }


@api_member_view()
def overview(request):
    """Station dashboard summary for the signed-in member (read-only)."""
    membership = request.membership
    station = membership.station
    now = timezone.now()

    active = prioritized_handovers(station)
    payload = {
        "station": {"name": station.name, "slug": station.slug},
        "role": membership.role,
        "role_label": membership.get_role_display(),
        "modules": {
            "calendar": station.calendar_enabled,
            "birthdays": station.birthdays_enabled,
            "coffee": station.coffee_enabled,
            "feeds": station.feeds_enabled,
        },
        "handovers": {
            "open_count": active.count(),
            "urgent_count": active.filter(
                priority=HandoverEntry.Priority.URGENT
            ).count(),
            "items": [_handover_json(item) for item in active[:5]],
        },
    }

    if station.calendar_enabled:
        events = (
            CalendarEvent.objects.filter(station=station, ends_at__gte=now)
            .order_by("starts_at")[:3]
        )
        payload["events"] = [
            {
                "id": event.pk,
                "title": event.title,
                "starts_at": event.starts_at.isoformat(),
                "ends_at": event.ends_at.isoformat(),
            }
            for event in events
        ]

    if station.coffee_enabled:
        can_book = membership.role in {
            Membership.Role.CASHIER,
            Membership.Role.ADMIN,
        }
        own_cents = (
            CoffeeEntry.objects.filter(station=station, member=request.user)
            .aggregate(total=Sum("amount_cents"))["total"]
            or 0
        )
        coffee = {
            "own_balance_euros": own_cents / 100,
            "can_book": can_book,
        }
        if can_book:
            total_cents = (
                CoffeeEntry.objects.filter(station=station)
                .aggregate(total=Sum("amount_cents"))["total"]
                or 0
            )
            coffee["total_balance_euros"] = total_cents / 100
        payload["coffee"] = coffee

    return JsonResponse(payload)
