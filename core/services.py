from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from .models import (
    AuditEvent,
    DailyTeamNote,
    HandoverAcknowledgement,
    HandoverEntry,
    HandoverRevision,
    TaskItem,
    TaskList,
    TaskResult,
    TaskRun,
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


# ---------------------------------------------------------------------------
# Aufgaben. Eine Liste beschreibt, was wann faellig ist; erst der erste Haken
# an einem Tag legt den zugehoerigen Lauf an. Dadurch bleibt der Bestand klein
# und ein Tag ohne Betrieb hinterlaesst keine leeren Datensaetze.
# ---------------------------------------------------------------------------

def active_task_lists(station):
    return (
        TaskList.objects.filter(station=station, is_active=True)
        .prefetch_related(
            Prefetch("items", queryset=TaskItem.objects.filter(is_active=True), to_attr="open_items")
        )
    )


def task_lists_for_day(station, day):
    """Die Listen, die an diesem Tag faellig sind - in ihrer Reihenfolge."""
    return [item for item in active_task_lists(station) if item.occurs_on(day)]


def task_day_overview(station, day):
    """Faellige Listen des Tages mit dem Stand je Punkt.

    Liefert je Liste den Lauf (falls schon einer existiert) und zu jedem
    aktiven Punkt das bisherige Ergebnis - genau das, was die Tagesansicht
    anzeigt und was fuer den Zaehler in der Wochenansicht gebraucht wird.
    """
    lists = task_lists_for_day(station, day)
    runs = {
        run.task_list_id: run
        for run in TaskRun.objects.filter(
            station=station, date=day, task_list__in=lists
        ).prefetch_related("results__recorded_by", "results__handover")
    }
    overview = []
    for task_list in lists:
        run = runs.get(task_list.pk)
        results = {result.item_id: result for result in run.results.all()} if run else {}
        rows = [
            {"item": item, "result": results.get(item.pk)}
            for item in task_list.open_items
        ]
        overview.append({
            "list": task_list,
            "run": run,
            "rows": rows,
            "total": len(rows),
            "settled": sum(1 for row in rows if row["result"] is not None),
            "defects": sum(
                1 for row in rows
                if row["result"] and row["result"].state == TaskResult.State.DEFECT
            ),
        })
    return overview


def task_week_progress(station, days):
    """Stand je Tag fuer die Wochenansicht - eine Abfrage fuer die ganze Woche.

    Bewusst ohne task_day_overview je Tag: das waeren sieben Abfragen fuer eine
    Zahl, die auf der Startseite steht.
    """
    lists = list(active_task_lists(station))
    counts = {
        (row["task_list_id"], row["date"]): row
        for row in TaskRun.objects.filter(station=station, date__in=days)
        .values("task_list_id", "date")
        .annotate(
            settled=Count("results"),
            defects=Count("results", filter=Q(results__state=TaskResult.State.DEFECT)),
        )
    }
    progress = {}
    for day in days:
        total = settled = defects = 0
        for task_list in lists:
            if not task_list.occurs_on(day):
                continue
            total += len(task_list.open_items)
            row = counts.get((task_list.pk, day))
            if row:
                settled += row["settled"]
                defects += row["defects"]
        progress[day] = {"total": total, "settled": settled, "defects": defects} if total else None
    return progress


def defect_handover_title(item):
    return f"Mangel: {item.title}"[:160]


@transaction.atomic
def record_task_result(station, task_list, item, day, state, note, membership):
    """Haken setzen oder aendern.

    Ein Mangel erzeugt zusaetzlich einen Uebergabe-Eintrag - das ist die
    Schleife, die aus Dokumentation Arbeit macht. Der Eintrag lebt danach
    eigenstaendig weiter und wird nicht mitgeloescht, wenn jemand den Haken
    spaeter korrigiert; er wurde in der Uebergabe bereits gelesen.
    """
    run, _ = TaskRun.objects.get_or_create(
        station=station, task_list=task_list, date=day,
    )
    result = TaskResult.objects.select_for_update().filter(run=run, item=item).first()
    previous = result.state if result else None
    if result is None:
        result = TaskResult(run=run, item=item)
    result.state = state
    result.note = note
    result.recorded_by = membership.user

    if state == TaskResult.State.DEFECT and result.handover_id is None:
        details = note or "Beim Abarbeiten der Liste als Mangel gemeldet."
        handover = HandoverEntry.objects.create(
            station=station,
            category=HandoverEntry.Category.SAFETY,
            priority=HandoverEntry.Priority.IMPORTANT,
            title=defect_handover_title(item),
            details=f"{details}\n\nAus der Liste „{task_list.title}“ vom {day:%d.%m.%Y}.",
            author=membership.user,
            for_date=day,
        )
        HandoverRevision.objects.create(
            handover=handover, version=handover.version,
            snapshot=handover_snapshot(handover), changed_by=membership.user,
        )
        result.handover = handover
        audit(membership.user, station, "handover.created_from_task", handover, {
            "task_item": item.pk, "task_list": task_list.pk,
        })

    result.save()
    audit(membership.user, station, "task.result_recorded", result, {
        "task_list": task_list.pk, "item": item.pk, "date": day.isoformat(),
        "from": previous, "to": state,
    })
    return result


@transaction.atomic
def clear_task_result(station, run, item, membership):
    """Haken zuruecknehmen. Ein bereits erzeugter Mangel-Eintrag bleibt
    bestehen und wird ueber die Uebergabe abgeschlossen, nicht hier."""
    result = TaskResult.objects.filter(run=run, item=item).first()
    if result is None:
        return None
    previous = result.state
    result.delete()
    audit(membership.user, station, "task.result_cleared", run, {
        "item": item.pk, "date": run.date.isoformat(), "from": previous,
    })
    return previous


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
