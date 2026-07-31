"""Versioned JSON API for future open-source iOS/Android clients.

Auth style follows Paperless-ngx / Nextcloud app passwords:
Authorization: Token <secret>
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from ..access import CONTENT_ROLES, get_membership
from ..models import ApiToken, HandoverEntry
from ..services import audit
from ..version import APP_VERSION

API_VERSION = "v1"
TOKEN_PREFIX = "wb_"


def hash_api_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_api_token() -> tuple[str, str, str]:
    """Return (raw_token, token_hash, display_prefix)."""
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    return raw, hash_api_token(raw), raw[:11]


def _json_error(message, status=400, **extra):
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return JsonResponse(payload, status=status)


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
    if "*" in scopes or "all" in scopes:
        return True
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
            "me": "/api/v1/me/",
            "handovers": "/api/v1/handovers/",
            "openapi": "/api/v1/openapi.yaml",
        },
        "mobile_clients": {
            "status": "foundation",
            "notes": "Stable contract for future AGPL iOS/Android apps (Paperless/Nextcloud style).",
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
    raw, token_hash, prefix = generate_api_token()
    token = ApiToken.objects.create(
        user=user,
        label=label or "Mobile App",
        token_prefix=prefix,
        token_hash=token_hash,
        scopes=["read:me", "read:handovers"],
    )
    audit(user, membership.station, "api.token_created", token, {
        "fields": ["label", "scopes"],
        "via": "api.token",
    })
    return JsonResponse({
        "ok": True,
        "token": raw,
        "token_prefix": prefix,
        "api_version": API_VERSION,
    })


@csrf_exempt
@require_GET
@api_token_required
def me(request):
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


@csrf_exempt
@require_GET
@api_token_required
def handovers_list(request):
    if not _scope_allowed(request.api_token, "read:handovers"):
        return _json_error("Scope read:handovers fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error("Rolle hat keinen Zugriff auf Übergaben.", status=403)
    qs = (
        HandoverEntry.objects.filter(station=request.membership.station)
        .exclude(status=HandoverEntry.Status.DONE)
        .order_by("-updated_at")[:50]
    )
    results = [
        {
            "id": item.pk,
            "title": item.title,
            "category": item.category,
            "priority": item.priority,
            "status": item.status,
            "updated_at": item.updated_at.isoformat(),
        }
        for item in qs
    ]
    return JsonResponse({
        "ok": True,
        "api_version": API_VERSION,
        "count": len(results),
        "results": results,
        "next": None,
        "previous": None,
    })
