"""Read-only JSON API for the mobile client (iOS/Android).

The API mirrors the station-scoped access rules of the HTML views and exposes only
data the signed-in member may already see in the interface. It never returns
patient, health or operational data. Apart from the credential login endpoint it
performs no writes, so it stays inside the documented privacy boundary of the
Wachbuch.

Authentication accepts either an existing Django session cookie or a stateless
bearer token issued by ``POST /api/v1/anmeldung/``. The token is a signed,
time-limited payload (``django.core.signing``) and needs no server-side storage,
which keeps the hardened database model unchanged. Individual tokens cannot be
revoked before they expire; a shorter lifetime and, later, a proper token store
belong to roadmap phase M2.
"""

import json
from functools import wraps

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .access import CONTENT_ROLES, get_membership
from .forms import (
    CalendarEventForm,
    CoffeeEntryForm,
    HandoverForm,
    HandoverStatusForm,
)
from .models import CalendarEvent, CoffeeEntry, HandoverEntry, Membership
from .services import audit, change_handover_status, create_handover
from .views import prioritized_handovers

WRITE_ROLES = {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN}
CASHIER_ROLES = {Membership.Role.CASHIER, Membership.Role.ADMIN}

API_VERSION = "1.0"
TOKEN_SALT = "wachbuch.client.api.v1"
TOKEN_MAX_AGE = 60 * 60 * 12  # 12 hours


def _error(status, message):
    return JsonResponse({"error": message}, status=status)


def issue_token(user):
    return signing.dumps({"uid": user.pk}, salt=TOKEN_SALT)


def _user_from_token(token):
    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)
    except signing.BadSignature:
        return None
    user = User.objects.filter(pk=data.get("uid"), is_active=True).first()
    return user


def resolve_api_user(request):
    """Return the caller as a session user or via a bearer token, else ``None``."""
    if request.user.is_authenticated:
        return request.user
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return _user_from_token(header[len("Bearer "):].strip())
    return None


def api_member_view(allowed_roles=CONTENT_ROLES):
    """Authenticate an API view and attach the caller's membership.

    Unlike the HTML ``membership_required`` decorator this returns JSON error
    responses (401/403) instead of redirects, which suits a native client.
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_GET
        def wrapped(request, *args, **kwargs):
            user = resolve_api_user(request)
            if user is None:
                return _error(401, "Anmeldung erforderlich.")
            request.user = user
            membership = get_membership(user)
            if membership is None:
                return _error(403, "Keine aktive Wachenmitgliedschaft.")
            if allowed_roles is not None and membership.role not in allowed_roles:
                return _error(403, "Für diese Rolle nicht freigegeben.")
            request.membership = membership
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def api_module_required(field_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not getattr(request.membership.station, field_name):
                return _error(404, "Modul ist nicht aktiviert.")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def _bearer_user(request):
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return _user_from_token(header[len("Bearer "):].strip())
    return None


def api_write_view(allowed_roles):
    """Authenticate a writing API view via bearer token only.

    Writes require a token (never an ambient session cookie), which keeps the
    endpoints CSRF-safe without a cookie-based CSRF token exchange.
    """

    def decorator(view_func):
        @wraps(view_func)
        @require_POST
        def wrapped(request, *args, **kwargs):
            user = _bearer_user(request)
            if user is None:
                return _error(401, "Bearer-Token erforderlich.")
            request.user = user
            membership = get_membership(user)
            if membership is None:
                return _error(403, "Keine aktive Wachenmitgliedschaft.")
            if allowed_roles is not None and membership.role not in allowed_roles:
                return _error(403, "Für diese Rolle nicht freigegeben.")
            request.membership = membership
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def _json_body(request):
    try:
        return json.loads(request.body or b"{}"), None
    except (ValueError, TypeError):
        return None, _error(400, "Ungültiger JSON-Körper.")


@csrf_exempt
@require_POST
def login(request):
    """Issue a bearer token for valid credentials (rate-limited via django-axes)."""
    try:
        payload = json.loads(request.body or b"{}")
    except (ValueError, TypeError):
        return _error(400, "Ungültiger JSON-Körper.")
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return _error(400, "Benutzername und Passwort sind erforderlich.")
    try:
        user = authenticate(request, username=username, password=password)
    except PermissionDenied:
        return _error(429, "Zu viele Fehlversuche. Bitte später erneut.")
    if user is None:
        return _error(401, "Anmeldung fehlgeschlagen.")
    membership = get_membership(user)
    return JsonResponse({
        "token": issue_token(user),
        "expires_in": TOKEN_MAX_AGE,
        "has_membership": membership is not None,
        "station": membership.station.name if membership else None,
        "role": membership.role if membership else None,
    })


@require_GET
def status(request):
    """Auth-optional metadata endpoint the client can call without a membership."""
    user = resolve_api_user(request)
    membership = get_membership(user) if user is not None else None
    payload = {
        "api_version": API_VERSION,
        "authenticated": user is not None,
        "has_membership": membership is not None,
    }
    if membership is not None:
        payload["station"] = membership.station.name
        payload["role"] = membership.role
    return JsonResponse(payload)


def _person(user):
    return user.get_full_name() or user.get_username()


def _handover_summary(handover):
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


def _paginate(request, queryset, per_page=20):
    page = Paginator(queryset, per_page).get_page(request.GET.get("seite"))
    return page


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
            "items": [_handover_summary(item) for item in active[:5]],
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
        payload["coffee"] = _coffee_balances(station, membership, request.user)

    return JsonResponse(payload)


@csrf_exempt
def handovers(request):
    """Collection endpoint: ``GET`` lists, ``POST`` creates a handover."""
    if request.method == "GET":
        return _handover_list(request)
    if request.method == "POST":
        return _handover_create(request)
    return _error(405, "Methode nicht erlaubt.")


@api_member_view()
def _handover_list(request):
    """Paginated handover list: active (default), ``dringend`` or ``archiv``."""
    station = request.membership.station
    scope = request.GET.get("ansicht", "aktiv")
    if scope == "archiv":
        handovers = (
            HandoverEntry.objects.filter(
                station=station, status=HandoverEntry.Status.DONE
            )
            .select_related("author")
            .order_by("-completed_at", "-updated_at")
        )
    else:
        scope = "dringend" if scope == "dringend" else "aktiv"
        handovers = prioritized_handovers(station)
        if scope == "dringend":
            handovers = handovers.filter(priority=HandoverEntry.Priority.URGENT)

    page = _paginate(request, handovers)
    return JsonResponse({
        "scope": scope,
        "count": page.paginator.count,
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "results": [_handover_summary(item) for item in page.object_list],
    })


def _handover_detail_json(handover):
    data = _handover_summary(handover)
    data.update({
        "details": handover.details,
        "author": _person(handover.author),
        "version": handover.version,
        "created_at": handover.created_at.isoformat(),
        "completed_at": handover.completed_at.isoformat()
        if handover.completed_at
        else None,
        "revisions": [
            {
                "version": revision.version,
                "changed_by": _person(revision.changed_by),
                "created_at": revision.created_at.isoformat(),
            }
            for revision in handover.revisions.all()
        ],
    })
    return data


@api_member_view()
def handover_detail(request, pk):
    station = request.membership.station
    handover = (
        HandoverEntry.objects.filter(pk=pk, station=station)
        .select_related("author")
        .prefetch_related("revisions__changed_by")
        .first()
    )
    if handover is None:
        return _error(404, "Übergabe wurde nicht gefunden.")
    return JsonResponse(_handover_detail_json(handover))


@csrf_exempt
@api_write_view(CONTENT_ROLES)
def _handover_create(request):
    payload, error = _json_body(request)
    if error is not None:
        return error
    form = HandoverForm(payload)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Eingaben sind ungültig.", "fields": form.errors},
            status=422,
        )
    handover = create_handover(form, request.membership)
    return JsonResponse(_handover_detail_json(handover), status=201)


@csrf_exempt
@api_write_view(WRITE_ROLES)
def handover_set_status(request, pk):
    handover = HandoverEntry.objects.filter(
        pk=pk, station=request.membership.station
    ).first()
    if handover is None:
        return _error(404, "Übergabe wurde nicht gefunden.")
    payload, error = _json_body(request)
    if error is not None:
        return error
    form = HandoverStatusForm(payload, instance=handover)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Status ist ungültig.", "fields": form.errors},
            status=422,
        )
    updated = change_handover_status(
        handover, form.cleaned_data["status"], request.membership
    )
    return JsonResponse(_handover_summary(updated))


@csrf_exempt
def calendar(request):
    """Collection endpoint: ``GET`` lists upcoming events, ``POST`` creates one."""
    if request.method == "GET":
        return _calendar_list(request)
    if request.method == "POST":
        return _calendar_create(request)
    return _error(405, "Methode nicht erlaubt.")


def _event_json(event):
    return {
        "id": event.pk,
        "title": event.title,
        "description": event.description,
        "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat(),
        "created_by": _person(event.created_by),
    }


@api_member_view()
@api_module_required("calendar_enabled")
def _calendar_list(request):
    now = timezone.now()
    events = (
        CalendarEvent.objects.filter(
            station=request.membership.station, ends_at__gte=now
        )
        .select_related("created_by")
        .order_by("starts_at")
    )
    page = _paginate(request, events, 15)
    return JsonResponse({
        "count": page.paginator.count,
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "results": [_event_json(event) for event in page.object_list],
    })


@csrf_exempt
@api_write_view(WRITE_ROLES)
def _calendar_create(request):
    station = request.membership.station
    if not station.calendar_enabled:
        return _error(404, "Modul ist nicht aktiviert.")
    payload, error = _json_body(request)
    if error is not None:
        return error
    form = CalendarEventForm(payload)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Termin ist ungültig.", "fields": form.errors},
            status=422,
        )
    try:
        with transaction.atomic():
            event = form.save(commit=False)
            event.station = station
            event.created_by = request.user
            event.full_clean()
            event.save()
            audit(request.user, station, "calendar.created", event, {
                "fields": ["title", "description", "starts_at", "ends_at"]
            })
    except DjangoValidationError as exc:
        return JsonResponse(
            {"error": "Termin ist ungültig.", "fields": exc.message_dict}
            if hasattr(exc, "message_dict")
            else {"error": "; ".join(exc.messages)},
            status=422,
        )
    return JsonResponse(_event_json(event), status=201)


def _coffee_balances(station, membership, user):
    can_book = membership.role in {Membership.Role.CASHIER, Membership.Role.ADMIN}
    own_cents = (
        CoffeeEntry.objects.filter(station=station, member=user)
        .aggregate(total=Sum("amount_cents"))["total"]
        or 0
    )
    balances = {"own_balance_euros": own_cents / 100, "can_book": can_book}
    if can_book:
        total_cents = (
            CoffeeEntry.objects.filter(station=station)
            .aggregate(total=Sum("amount_cents"))["total"]
            or 0
        )
        balances["total_balance_euros"] = total_cents / 100
    return balances


@csrf_exempt
def coffee(request):
    """Collection endpoint: ``GET`` lists the ledger, ``POST`` books an entry."""
    if request.method == "GET":
        return _coffee_list(request)
    if request.method == "POST":
        return _coffee_create(request)
    return _error(405, "Methode nicht erlaubt.")


@api_member_view()
@api_module_required("coffee_enabled")
def _coffee_list(request):
    """Coffee ledger: members see only their own entries, cashiers/admins all."""
    station = request.membership.station
    membership = request.membership
    can_book = membership.role in {Membership.Role.CASHIER, Membership.Role.ADMIN}
    entries = (
        CoffeeEntry.objects.filter(station=station)
        .select_related("member", "correction_of")
    )
    if not can_book:
        entries = entries.filter(member=request.user)

    page = _paginate(request, entries, 25)
    return JsonResponse({
        "balances": _coffee_balances(station, membership, request.user),
        "count": page.paginator.count,
        "page": page.number,
        "num_pages": page.paginator.num_pages,
        "results": [
            {
                "id": entry.pk,
                "member": _person(entry.member),
                "amount_euros": entry.amount_euros,
                "reason": entry.reason,
                "created_at": entry.created_at.isoformat(),
                "is_correction": entry.correction_of_id is not None,
            }
            for entry in page.object_list
        ],
    })


@csrf_exempt
@api_write_view(CASHIER_ROLES)
def _coffee_create(request):
    station = request.membership.station
    if not station.coffee_enabled:
        return _error(404, "Modul ist nicht aktiviert.")
    payload, error = _json_body(request)
    if error is not None:
        return error
    form = CoffeeEntryForm(payload, station=station)
    if not form.is_valid():
        return JsonResponse(
            {"error": "Buchung ist ungültig.", "fields": form.errors},
            status=422,
        )
    with transaction.atomic():
        entry = CoffeeEntry.objects.create(
            station=station,
            member=form.cleaned_data["member"],
            amount_cents=form.amount_cents(),
            reason=form.cleaned_data["reason"],
            created_by=request.user,
        )
        audit(request.user, station, "coffee.entry_created", entry, {
            "fields": ["member", "amount_cents", "reason"]
        })
    return JsonResponse({
        "id": entry.pk,
        "member": _person(entry.member),
        "amount_euros": entry.amount_euros,
        "reason": entry.reason,
        "created_at": entry.created_at.isoformat(),
        "is_correction": False,
    }, status=201)
