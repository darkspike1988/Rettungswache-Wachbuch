"""API v1 fuer Qualifikations-/Tauglichkeitsnachweise mit Ablauffristen.

Produktgrenze: nur Titel + Ablaufdatum (+ kurze Notiz) fuer die Dienstplanung,
keine Diagnosen/Gruende. Sichtbarkeit: Mitglieder sehen ihre eigenen Nachweise,
Schichtleitung/Admin verwalten alle. Auditoren haben keinen Zugriff.
"""

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from ..access import CONTENT_ROLES
from ..messaging import station_content_users
from ..models import MemberQualification, Membership
from ..services import audit
from .views import (
    _json_error,
    _parse_json,
    _scope_allowed,
    api_token_required,
)

WRITE_ROLES = {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN}


def _require_module(request):
    if not request.membership.station.qualifications_enabled:
        return _json_error(request, "Modul ist nicht aktiviert.", status=404)
    return None


def _person(user):
    if user is None:
        return None
    return {"id": user.id, "name": user.first_name or user.username}


def _qual_json(item, today, *, include_member=False):
    data = {
        "id": item.pk,
        "title": item.title,
        "expires_at": item.expires_at.isoformat() if item.expires_at else None,
        "state": item.state(today),
        "note": item.note,
    }
    if include_member:
        data["member"] = _person(item.user)
    return data


def _parse_expires(value):
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError("Ablaufdatum muss ISO-Format (JJJJ-MM-TT) haben.") from exc


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_token_required
def qualifications(request):
    station = request.membership.station
    module_error = _require_module(request)
    if module_error:
        return module_error
    is_manager = request.membership.role in WRITE_ROLES
    today = timezone.localdate()

    if request.method == "POST":
        if not _scope_allowed(request.api_token, "write:qualifications"):
            return _json_error(request, "Scope write:qualifications fehlt.", status=403)
        if not is_manager:
            return _json_error(request, "Nur Schichtleitung oder Admin darf Nachweise verwalten.", status=403)
        body = _parse_json(request)
        if body is None:
            return _json_error(request, "JSON-Körper erwartet.")
        title = str(body.get("title") or "").strip()
        if not (1 <= len(title) <= 160):
            return _json_error(request, "Titel ist erforderlich (max. 160 Zeichen).", status=422)
        try:
            user_id = int(body.get("user_id"))
        except (TypeError, ValueError):
            return _json_error(request, "Mitglied ist ungültig.", status=422)
        member = station_content_users(station).filter(pk=user_id).first()
        if member is None:
            return _json_error(request, "Mitglied gehört nicht zur Wache.", status=422)
        try:
            expires_at = _parse_expires(body.get("expires_at"))
        except ValueError as exc:
            return _json_error(request, str(exc), status=422)
        note = str(body.get("note") or "")[:300]
        with transaction.atomic():
            item = MemberQualification.objects.create(
                station=station,
                user=member,
                title=title,
                expires_at=expires_at,
                note=note,
                created_by=request.user,
            )
            audit(request.user, station, "qualification.created", item, {
                "fields": ["title", "expires_at"],
            })
        return JsonResponse({"ok": True, **_qual_json(item, today, include_member=True)}, status=201)

    if not _scope_allowed(request.api_token, "read:qualifications"):
        return _json_error(request, "Scope read:qualifications fehlt.", status=403)
    if request.membership.role not in CONTENT_ROLES:
        return _json_error(request, "Rolle hat keinen Zugriff auf Qualifikationen.", status=403)
    if is_manager:
        qs = MemberQualification.objects.filter(station=station).select_related("user")
        requested = request.GET.get("user")
        if requested:
            try:
                qs = qs.filter(user_id=int(requested))
            except (TypeError, ValueError):
                return _json_error(request, "Filter ungültig.", status=422)
        results = [_qual_json(item, today, include_member=True) for item in qs[:500]]
    else:
        qs = MemberQualification.objects.filter(station=station, user=request.user)
        results = [_qual_json(item, today) for item in qs[:200]]
    return JsonResponse({"ok": True, "is_manager": is_manager, "results": results})


@csrf_exempt
@require_http_methods(["PATCH", "POST", "DELETE"])
@api_token_required
def qualification_detail(request, pk):
    station = request.membership.station
    module_error = _require_module(request)
    if module_error:
        return module_error
    if not _scope_allowed(request.api_token, "write:qualifications"):
        return _json_error(request, "Scope write:qualifications fehlt.", status=403)
    if request.membership.role not in WRITE_ROLES:
        return _json_error(request, "Nur Schichtleitung oder Admin darf Nachweise verwalten.", status=403)
    item = MemberQualification.objects.filter(pk=pk, station=station).select_related("user").first()
    if item is None:
        return _json_error(request, "Nicht gefunden.", status=404)
    today = timezone.localdate()

    if request.method == "DELETE":
        with transaction.atomic():
            audit(request.user, station, "qualification.deleted", item, {"fields": ["title"]})
            item.delete()
        return JsonResponse({"ok": True})

    body = _parse_json(request) or {}
    if "title" in body:
        title = str(body.get("title") or "").strip()
        if not (1 <= len(title) <= 160):
            return _json_error(request, "Titel ist ungültig.", status=422)
        item.title = title
    if "expires_at" in body:
        try:
            item.expires_at = _parse_expires(body.get("expires_at"))
        except ValueError as exc:
            return _json_error(request, str(exc), status=422)
    if "note" in body:
        item.note = str(body.get("note") or "")[:300]
    with transaction.atomic():
        item.save(update_fields=["title", "expires_at", "note", "updated_at"])
        audit(request.user, station, "qualification.updated", item, {"fields": ["title", "expires_at"]})
    return JsonResponse({"ok": True, **_qual_json(item, today, include_member=True)})


@csrf_exempt
@require_GET
@api_token_required
def qualifications_due(request):
    """Ablaufende/abgelaufene Nachweise fuer die Dienstplanung (Manager)."""
    station = request.membership.station
    module_error = _require_module(request)
    if module_error:
        return module_error
    if not _scope_allowed(request.api_token, "read:qualifications"):
        return _json_error(request, "Scope read:qualifications fehlt.", status=403)
    if request.membership.role not in WRITE_ROLES:
        return _json_error(request, "Nur Schichtleitung oder Admin sieht die Faellig-Liste.", status=403)
    today = timezone.localdate()
    due = []
    for item in MemberQualification.objects.filter(
        station=station, expires_at__isnull=False
    ).select_related("user"):
        if item.state(today) in {"expired", "expiring_soon"}:
            due.append(_qual_json(item, today, include_member=True))
    order = {"expired": 0, "expiring_soon": 1}
    due.sort(key=lambda e: (order.get(e["state"], 2), e["expires_at"] or "9999"))
    return JsonResponse({"ok": True, "count": len(due), "results": due})
