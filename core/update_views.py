from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .access import membership_required
from .models import Membership, Station, UpdateRequest
from .services import audit
from .update_service import UpdateCheckError, fetch_latest_release, is_newer_version


@membership_required({Membership.Role.ADMIN})
@require_http_methods(["GET", "POST"])
def updates(request):
    release = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"check", "request"}:
            try:
                release = fetch_latest_release()
            except UpdateCheckError as exc:
                messages.error(request, str(exc))
            else:
                if not is_newer_version(release.version, settings.APP_VERSION):
                    messages.success(request, "Diese Installation ist bereits aktuell.")
                elif action == "request":
                    with transaction.atomic():
                        Station.objects.select_for_update().get(
                            pk=request.membership.station_id
                        )
                        active = UpdateRequest.objects.filter(
                            status__in=[
                                UpdateRequest.Status.PENDING,
                                UpdateRequest.Status.RUNNING,
                            ]
                        ).first()
                        if active:
                            messages.error(
                                request,
                                "Es existiert bereits ein offener Updateauftrag.",
                            )
                        else:
                            update = UpdateRequest.objects.create(
                                requested_by=request.user,
                                station=request.membership.station,
                                current_version=settings.APP_VERSION,
                                target_version=release.version,
                                release_url=release.url,
                            )
                            audit(
                                request.user,
                                request.membership.station,
                                "system.update_requested",
                                update,
                                {
                                    "current_version": settings.APP_VERSION,
                                    "target_version": release.version,
                                },
                            )
                            messages.success(
                                request,
                                "Update angefordert. Starte auf dem Host "
                                "./scripts/update.sh --apply-requested.",
                            )
                    return redirect("updates")
        elif action == "cancel":
            request_id = request.POST.get("request_id", "")
            if not request_id.isdecimal():
                raise Http404
            with transaction.atomic():
                update = get_object_or_404(
                    UpdateRequest.objects.select_for_update(),
                    pk=request_id,
                    station=request.membership.station,
                    status=UpdateRequest.Status.PENDING,
                )
                update.status = UpdateRequest.Status.CANCELLED
                update.result_message = "Vom Master-Admin abgebrochen."
                update.finished_at = timezone.now()
                update.save(
                    update_fields=["status", "result_message", "finished_at"]
                )
                audit(
                    request.user,
                    request.membership.station,
                    "system.update_cancelled",
                    update,
                    {
                        "target_version": update.target_version,
                    },
                )
            messages.success(request, "Updateauftrag wurde abgebrochen.")
            return redirect("updates")

    history = UpdateRequest.objects.filter(station=request.membership.station)[:20]
    active = UpdateRequest.objects.filter(
        status__in=[UpdateRequest.Status.PENDING, UpdateRequest.Status.RUNNING]
    ).first()
    return render(
        request,
        "core/updates.html",
        {
            "release": release,
            "release_is_newer": bool(
                release and is_newer_version(release.version, settings.APP_VERSION)
            ),
            "active_update": active,
            "update_history": history,
            "update_check_enabled": getattr(settings, "UPDATE_CHECK_ENABLED", True),
        },
    )
