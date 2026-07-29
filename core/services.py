from django.db import transaction
from django.utils import timezone

from .models import (
    AuditEvent,
    DailyTeamNote,
    HandoverAcknowledgement,
    HandoverEntry,
    HandoverRevision,
)


def audit(actor, station, action, obj, metadata=None):
    return AuditEvent.objects.create(
        actor=actor,
        station=station,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        metadata=metadata or {},
    )


def handover_snapshot(handover):
    return {
        "category": handover.category,
        "priority": handover.priority,
        "status": handover.status,
        "title": handover.title,
        "details": handover.details,
        "for_date": handover.for_date.isoformat() if handover.for_date else None,
    }


@transaction.atomic
def create_handover(form, membership):
    handover = form.save(commit=False)
    handover.station = membership.station
    handover.author = membership.user
    handover.save()
    HandoverRevision.objects.create(
        handover=handover,
        version=handover.version,
        snapshot=handover_snapshot(handover),
        changed_by=membership.user,
    )
    audit(membership.user, membership.station, "handover.created", handover, {"fields": [
        "category", "priority", "title", "details"
    ]})
    return handover


EDITABLE_HANDOVER_FIELDS = ["category", "priority", "title", "details", "for_date"]


@transaction.atomic
def update_handover(handover, form, membership):
    locked = HandoverEntry.objects.select_for_update().get(pk=handover.pk)
    for field in EDITABLE_HANDOVER_FIELDS:
        setattr(locked, field, form.cleaned_data[field])
    locked.version += 1
    locked.save(update_fields=EDITABLE_HANDOVER_FIELDS + ["version", "updated_at"])
    HandoverRevision.objects.create(
        handover=locked,
        version=locked.version,
        snapshot=handover_snapshot(locked),
        changed_by=membership.user,
    )
    audit(membership.user, membership.station, "handover.updated", locked, {
        "fields": [field for field in form.changed_data if field in EDITABLE_HANDOVER_FIELDS],
        "version": locked.version,
    })
    return locked


@transaction.atomic
def change_handover_status(handover, status, membership):
    locked = HandoverEntry.objects.select_for_update().get(pk=handover.pk)
    if locked.status == status:
        return locked
    locked.status = status
    locked.version += 1
    locked.completed_at = timezone.now() if status == HandoverEntry.Status.DONE else None
    locked.save(update_fields=["status", "version", "completed_at", "updated_at"])
    HandoverRevision.objects.create(
        handover=locked,
        version=locked.version,
        snapshot=handover_snapshot(locked),
        changed_by=membership.user,
    )
    audit(membership.user, membership.station, "handover.status_changed", locked, {
        "fields": ["status"], "version": locked.version
    })
    return locked


@transaction.atomic
def acknowledge_handover(handover, membership):
    acknowledgement, created = HandoverAcknowledgement.objects.get_or_create(
        handover=handover, user=membership.user,
    )
    if created:
        audit(membership.user, membership.station, "handover.acknowledged", handover, {
            "version": handover.version,
        })
    return acknowledgement


@transaction.atomic
def set_daily_team(station, day, note, membership):
    team_note, created = DailyTeamNote.objects.select_for_update().get_or_create(
        station=station, date=day, defaults={"note": note, "updated_by": membership.user}
    )
    if not created:
        team_note.note = note
        team_note.updated_by = membership.user
        team_note.save(update_fields=["note", "updated_by", "updated_at"])
    audit(membership.user, station, "handover.team_set", team_note, {"fields": ["note"], "date": day.isoformat()})
    return team_note
