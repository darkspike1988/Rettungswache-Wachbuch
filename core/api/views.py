"""Versioned JSON API for future open-source iOS/Android clients.

Auth style follows Paperless-ngx / Nextcloud app passwords:
Authorization: Token <secret>
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Sum

from ..access import CONTENT_ROLES, get_membership
from ..forms import CalendarEventForm, CoffeeEntryForm, HandoverForm, HandoverStatusForm
from ..models import (
    ApiToken,
    CalendarEvent,
    Checklist,
    ChecklistCompletion,
    CoffeeEntry,
    HandoverEntry,
    Membership,
)
from ..services import audit, change_handover_status, create_handover
from ..version import APP_VERSION

API_VERSION = "v1"
TOKEN_PREFIX = "wb_"
DEFAULT_TOKEN_TTL_DAYS = 90
WRITE_ROLES = {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN}
CASHIER_ROLES = {Membership.Role.CASHIER, Membership.Role.ADMIN}
DEFAULT_MOBILE_SCOPES = [
    "read:me",
    "read:handovers",
    "write:handovers",
    "read:calendar",
    "write:calendar",
    "read:coffee",
    "write:coffee",
    "read:checklists",
    "write:checklists",
]


def hash_api_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_api_token() -> tuple[str, str, str]:
    """Return (raw_token, token_hash, display_prefix)."""
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_token(raw), raw[:11]


def default_token_expiry():
    return timezone.now() + timedelta(days=DEFAULT_TOKEN_TTL_DAYS)


def _json_error(message, status=400, **extra):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


def _api_get_or_404(model, **kwargs):
    """Return (obj, None) or (None, JsonResponse 404) for API clients."""
    obj = model.objects.filter(**kwargs).first()
    if obj is None:
        return None, _json_error("Nicht gefunden.", status=404)
    return obj, None


def _parse_json(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _extract_bearer_token(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2:
        return None
    scheme, value = parts[0].lower(), parts[1].strip()
    if scheme in {"token", "bearer"} and value:
        return value
    return None


def resolve_api_token(raw_token: str):
    if not raw_token or len(raw_token) > 200:
        return None
    digest = hash_api_token(raw_token)
    token = (
        ApiToken.objects.select_related("user")
        .filter(token_hash=digest, is_active=True, user__is_active=True)
        .first()
    )
    if token is None:
        # Constant-time-ish miss path
        hmac.compare_digest(digest, "0" * 64)
        return None
    if token.expires_at and token.expires_at <= timezone.now():
        return None
    return token


def api_token_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        raw = _extract_bearer_token(request)
        if not raw:
            return _json_error("Authentifizierung erforderlich.", status=401)
        token = resolve_api_token(raw)
        if token is None:
            return _json_error("Ungültiges oder widerrufenes API-Token.", status=401)
        membership = get_membership(token.user)
        if membership is None:
            return _json_error("Kein aktiver Wachenzugang.", status=403)
        ApiToken.objects.filter(pk=token.pk).update(last_used_at=timezone.now())
        request.user = token.user
        request.membership = membership
        request.api_token = token
        return view(request, *args, **kwargs)

    return wrapped


def _scope_allowed(token: ApiToken, scope: str) -> bool:
    scopes = token.scopes or []
    return scope in scopes


@csrf_exempt
@require_GET
def api_root(request):
    return JsonResponse({
        "ok": True,
        "name": getattr(settings, "APP_NAME", "Wachbuch"),
        "app_version": APP_VERSION,
        "api_version": API_VERSION,
        "authentication": ["Token", "Bearer"],
        "docs": "/api/v1/openapi.yaml",
        "endpoints": {
            "token": "/api/v1/token/",
            "anmeldung": "/api/v1/anmeldung/",
            "me": "/api/v1/me/",
            "status": "/api/v1/status/",
            "uebersicht": "/api/v1/uebersicht/",
            "handovers": "/api/v1/handovers/",
            "uebergaben": "/api/v1/uebergaben/",
            "kalender": "/api/v1/kalender/",
            "kaffeekasse": "/api/v1/kaffeekasse/",
            "checklisten": "/api/v1/checklisten/",
            "openapi": "/api/v1/openapi.yaml",
        },
        "mobile_clients": {
            "status": "unified",
            "repo": "https://github.com/darkspike1988/Wachbuch-Client",
            "notes": "Widerrufbare App-Tokens (wb_…) plus deutsche Alias-Pfade aus PR#12.",
        },
    })


@csrf_exempt
@require_GET
def openapi_spec(request):
    from pathlib import Path

    path = Path(__file__).resolve().parent / "openapi_v1.yaml"
    return HttpResponse(path.read_text(encoding="utf-8"), content_type="application/yaml; charset=utf-8")


@csrf_exempt
@require_POST
def obtain_token(request):
    """Paperless-style token exchange: username + password → API token."""
    body = _parse_json(request)
    if body is None:
        # also accept form-encoded like Paperless
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        label = (request.POST.get("label") or "Mobile App").strip()[:120]
    else:
        username = str(body.get("username") or "").strip()
        password = str(body.get("password") or "")
        label = str(body.get("label") or "Mobile App").strip()[:120]
    if not username or not password:
        return _json_error("Benutzername und Passwort erforderlich.")
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active:
        return _json_error("Anmeldung fehlgeschlagen.", status=401)
    membership = get_membership(user)
    if membership is None:
        return _json_error("Kein aktiver Wachenzugang.", status=403)
    from ..mfa import user_has_confirmed_mfa

    if user_has_confirmed_mfa(user):
        return _json_error(
            "Für dieses Konto ist MFA aktiv. Bitte ein App-Token unter /konto/api/ erzeugen.",
            status=403,
            code="mfa_required",
        )
    from axes.utils import reset as axes_reset

    axes_reset(username=username)
    expires_at = default_token_expiry()
    raw, token_hash, prefix = generate_api_token()
    token = ApiToken.objects.create(
        user=user,
        label=label or "Mobile App",
        token_prefix=prefix,
        token_hash=token_hash,
        scopes=list(DEFAULT_MOBILE_SCOPES),
        expires_at=expires_at,
    )
    audit(user, membership.station, "api.token_created", token, {
        "fields": ["label", "scopes", "expires_at"],
        "via": "api.token",
    })
    return JsonResponse({
        "ok": True,
        "token": raw,
        "token_prefix": prefix,
        "api_version": API_VERSION,
        "expires_in": DEFAULT_TOKEN_TTL_DAYS * 24 * 3600,
        "expires_at": expires_at.isoformat(),
        "has_membership": True,
        "station": membership.station.name,
        "role": membership.role,
    })


@csrf_exempt
@require_GET
@api_token_required
def me(request):
    if not _scope_allowed(request.api_token, "read:me"):
        return _json_error("Scope read:me fehlt.", status=403)
    membership = request.membership
    station = membership.station
    return JsonResponse({
        "ok": True,
        "api_version": API_VERSION,
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        },
        "membership": {
            "role": membership.role,
            "role_label": membership.get_role_display(),
            "station": {
                "id": station.id,
                "name": station.name,
                "slug": station.slug,
                "modules": {
                    "calendar": station.calendar_enabled,
                    "chat": station.chat_enabled,
                    "tasks": station.tasks_enabled,
                    "coffee": station.coffee_enabled,
                    "feeds": station.feeds_enabled,
                    "birthdays": station.birthdays_enabled,
                    "holidays": station.holidays_enabled,
                    "checklists": station.checklists_enabled,
                },
            },
        },
        "token": {
            "id": request.api_token.id,
            "label": request.api_token.label,
            "prefix": request.api_token.token_prefix,
            "scopes": request.api_token.scopes,
        },
    })


def _person(user):
    return {
        "id": user.pk,
        "username": user.username,
        "display_name": user.get_full_name() or user.username,
    }


def _handover_json(item, *, detail=False):
    data = {
        "id": item.pk,
        "title": item.title,
        "category": item.category,
        "priority": item.priority,
        "status": item.status,
        "updated_at": item.updated_at.isoformat(),
    }
    if detail:
        data["details"] = item.details
        data["created_at"] = item.created_at.isoformat()
        data["author"] = _person(item.author) if item.author_id else None
        data["version"] = item.version
    return data


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def handovers_list(request):
    if request.method == "POST":
        return handover_create(request)
    if not _scope_allowed(request.api_token, "read:handovers"):
        return _json_error("Scope read:handovers fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf Übergaben.", status=403)
    qs = (
        HandoverEntry.objects.filter(station=request.membership.station)
        .exclude(status=HandoverEntry.Status.DONE)
        .order_by("-updated_at")[:50]
    )
    results = [_handover_json(item) for item in qs]
    return JsonResponse({
        "ok": True,
        "api_version": API_VERSION,
        "count": len(results),
        "results": results,
        "next": None,
        "previous": None,
    })


@csrf_exempt
@require_GET
def api_status(request):
    """Auth-optional status for clients (German alias: /status/)."""
    raw = _extract_bearer_token(request)
    authenticated = False
    has_membership = False
    station_name = None
    role = None
    if raw:
        token = resolve_api_token(raw)
        if token is not None:
            authenticated = True
            membership = get_membership(token.user)
            if membership is not None:
                has_membership = True
                station_name = membership.station.name
                role = membership.role
    elif request.user.is_authenticated:
        authenticated = True
        membership = get_membership(request.user)
        if membership is not None:
            has_membership = True
            station_name = membership.station.name
            role = membership.role
    payload = {
        "ok": True,
        "api_version": API_VERSION,
        "app_version": APP_VERSION,
        "authenticated": authenticated,
        "has_membership": has_membership,
    }
    if station_name is not None:
        payload["station"] = station_name
        payload["role"] = role
    return JsonResponse(payload)


@csrf_exempt
@require_GET
@api_token_required
def overview(request):
    """Dashboard summary (German alias: /uebersicht/)."""
    if not _scope_allowed(request.api_token, "read:me"):
        return _json_error("Scope read:me fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf die Übersicht.", status=403)
    station = request.membership.station
    handovers = {"open_count": 0, "urgent_count": 0, "items": []}
    if _scope_allowed(request.api_token, "read:handovers"):
        open_qs = HandoverEntry.objects.filter(station=station).exclude(
            status=HandoverEntry.Status.DONE
        )
        handovers = {
            "open_count": open_qs.count(),
            "urgent_count": open_qs.filter(priority=HandoverEntry.Priority.URGENT).count(),
            "items": [_handover_json(item) for item in open_qs.order_by("-updated_at")[:5]],
        }
    return JsonResponse({
        "ok": True,
        "api_version": API_VERSION,
        "station": {"id": station.id, "name": station.name, "slug": station.slug},
        "role": request.membership.role,
        "role_label": request.membership.get_role_display(),
        "modules": {
            "calendar": station.calendar_enabled,
            "chat": station.chat_enabled,
            "tasks": station.tasks_enabled,
            "coffee": station.coffee_enabled,
            "feeds": station.feeds_enabled,
            "birthdays": station.birthdays_enabled,
            "holidays": station.holidays_enabled,
            "checklists": station.checklists_enabled,
        },
        "handovers": handovers,
    })


def handover_create(request):
    if not _scope_allowed(request.api_token, "write:handovers"):
        return _json_error("Scope write:handovers fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle darf keine Übergaben anlegen.", status=403)
    body = _parse_json(request)
    if body is None:
        return _json_error("JSON-Körper erwartet.")
    form = HandoverForm(body)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": "Eingaben sind ungültig.", "fields": form.errors}, status=422)
    handover = create_handover(form, request.membership)
    return JsonResponse({"ok": True, **_handover_json(handover, detail=True)}, status=201)


@csrf_exempt
@require_GET
@api_token_required
def handover_detail(request, pk):
    if not _scope_allowed(request.api_token, "read:handovers"):
        return _json_error("Scope read:handovers fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf Übergaben.", status=403)
    handover, err = _api_get_or_404(HandoverEntry, pk=pk, station=request.membership.station)
    if err:
        return err
    return JsonResponse({"ok": True, **_handover_json(handover, detail=True)})


@csrf_exempt
@require_POST
@api_token_required
def handover_set_status(request, pk):
    if not _scope_allowed(request.api_token, "write:handovers"):
        return _json_error("Scope write:handovers fehlt.", status=403)
    if request.membership.role not in WRITE_ROLES:
        return _json_error("Rolle darf den Status nicht ändern.", status=403)
    handover, err = _api_get_or_404(HandoverEntry, pk=pk, station=request.membership.station)
    if err:
        return err
    body = _parse_json(request) or {}
    form = HandoverStatusForm(body, instance=handover)
    if not form.is_valid():
        return JsonResponse({"ok": False, "error": "Status ungültig.", "fields": form.errors}, status=422)
    updated = change_handover_status(handover, form.cleaned_data["status"], request.membership)
    return JsonResponse({"ok": True, **_handover_json(updated, detail=True)})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def calendar_api(request):
    station = request.membership.station
    if not station.calendar_enabled:
        return _json_error("Modul ist nicht aktiviert.", status=404)
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:calendar"):
            return _json_error("Scope write:calendar fehlt.", status=403)
        if request.membership.role not in WRITE_ROLES:
            return _json_error("Rolle darf keine Termine anlegen.", status=403)
        body = _parse_json(request)
        if body is None:
            return _json_error("JSON-Körper erwartet.")
        form = CalendarEventForm(body)
        if not form.is_valid():
            return JsonResponse({"ok": False, "error": "Termin ist ungültig.", "fields": form.errors}, status=422)
        try:
            with transaction.atomic():
                event = form.save(commit=False)
                event.station = station
                event.created_by = request.user
                event.full_clean()
                event.save()
                audit(request.user, station, "calendar.created", event, {
                    "fields": ["title", "description", "starts_at", "ends_at"],
                })
        except DjangoValidationError as exc:
            return JsonResponse(
                {"ok": False, "error": "Termin ist ungültig.", "fields": getattr(exc, "message_dict", {"__all__": exc.messages})},
                status=422,
            )
        return JsonResponse({
            "ok": True,
            "id": event.pk,
            "title": event.title,
            "starts_at": event.starts_at.isoformat(),
            "ends_at": event.ends_at.isoformat() if event.ends_at else None,
        }, status=201)

    if not _scope_allowed(request.api_token, "read:calendar"):
        return _json_error("Scope read:calendar fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf den Kalender.", status=403)
    events = (
        CalendarEvent.objects.filter(station=station, starts_at__gte=timezone.now())
        .order_by("starts_at")[:30]
    )
    return JsonResponse({
        "ok": True,
        "results": [
            {
                "id": event.pk,
                "title": event.title,
                "starts_at": event.starts_at.isoformat(),
                "ends_at": event.ends_at.isoformat() if event.ends_at else None,
            }
            for event in events
        ],
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def coffee_api(request):
    station = request.membership.station
    if not station.coffee_enabled:
        return _json_error("Modul ist nicht aktiviert.", status=404)
    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:coffee"):
            return _json_error("Scope write:coffee fehlt.", status=403)
        if request.membership.role not in CASHIER_ROLES:
            return _json_error("Rolle darf die Kasse nicht buchen.", status=403)
        body = _parse_json(request)
        if body is None:
            return _json_error("JSON-Körper erwartet.")
        form = CoffeeEntryForm(body, station=station)
        if not form.is_valid():
            return JsonResponse({"ok": False, "error": "Buchung ist ungültig.", "fields": form.errors}, status=422)
        with transaction.atomic():
            entry = CoffeeEntry.objects.create(
                station=station,
                member=form.cleaned_data["member"],
                amount_cents=form.amount_cents(),
                reason=form.cleaned_data["reason"],
                created_by=request.user,
            )
            audit(request.user, station, "coffee.entry_created", entry, {
                "fields": ["member", "amount_cents", "reason"],
            })
        return JsonResponse({
            "ok": True,
            "id": entry.pk,
            "member": _person(entry.member),
            "amount_euros": entry.amount_euros,
            "reason": entry.reason,
            "created_at": entry.created_at.isoformat(),
        }, status=201)

    if not _scope_allowed(request.api_token, "read:coffee"):
        return _json_error("Scope read:coffee fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf die Kaffeekasse.", status=403)
    qs = CoffeeEntry.objects.filter(station=station).select_related("member")
    if request.membership.role not in CASHIER_ROLES:
        qs = qs.filter(member=request.user)
    total = qs.aggregate(total=Sum("amount_cents"))["total"] or 0
    results = [
        {
            "id": entry.pk,
            "member": _person(entry.member),
            "amount_euros": entry.amount_euros,
            "reason": entry.reason,
            "created_at": entry.created_at.isoformat(),
        }
        for entry in qs.order_by("-created_at")[:50]
    ]
    return JsonResponse({"ok": True, "balance_euros": total / 100, "results": results})


@csrf_exempt
@require_GET
@api_token_required
def checklists_api(request):
    station = request.membership.station
    if not station.checklists_enabled:
        return _json_error("Modul ist nicht aktiviert.", status=404)
    if not _scope_allowed(request.api_token, "read:checklists"):
        return _json_error("Scope read:checklists fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf Checklisten.", status=403)
    lists = Checklist.objects.filter(station=station, is_active=True).prefetch_related("items")
    latest = {}
    for completion in (
        ChecklistCompletion.objects.filter(station=station)
        .select_related("completed_by")
        .order_by("checklist_id", "-created_at")
    ):
        latest.setdefault(completion.checklist_id, completion)
    results = []
    for checklist in lists:
        last = latest.get(checklist.id)
        results.append({
            "id": checklist.id,
            "title": checklist.title,
            "description": checklist.description,
            "items": [item.text for item in checklist.items.all()],
            "last_completed_at": last.created_at.isoformat() if last else None,
            "last_completed_by": _person(last.completed_by)["display_name"] if last else None,
        })
    return JsonResponse({"ok": True, "results": results})


@csrf_exempt
@require_POST
@api_token_required
def checklist_complete_api(request, pk):
    station = request.membership.station
    if not station.checklists_enabled:
        return _json_error("Modul ist nicht aktiviert.", status=404)
    if not _scope_allowed(request.api_token, "write:checklists"):
        return _json_error("Scope write:checklists fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle darf Checklisten nicht abschließen.", status=403)
    checklist, err = _api_get_or_404(Checklist, pk=pk, station=station, is_active=True)
    if err:
        return err
    body = _parse_json(request) or {}
    note = str(body.get("note") or "")[:300]
    with transaction.atomic():
        completion = ChecklistCompletion.objects.create(
            station=station,
            checklist=checklist,
            completed_by=request.user,
            note=note,
        )
        audit(request.user, station, "checklist.completed", completion, {
            "fields": ["checklist", "note"],
        })
    return JsonResponse({
        "ok": True,
        "id": completion.pk,
        "checklist": checklist.id,
        "completed_by": _person(request.user),
        "created_at": completion.created_at.isoformat(),
    }, status=201)
