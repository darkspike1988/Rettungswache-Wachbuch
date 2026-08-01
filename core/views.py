from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import Case, IntegerField, Sum, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .access import CONTENT_ROLES, membership_required, station_module_required

from .forms import (
    BirthdayForm,
    CalendarEventForm,
    CoffeeCorrectionForm,
    CoffeeEntryForm,
    HandoverForm,
    HandoverStatusForm,
    MembershipAssignmentForm,
    MembershipEditForm,
    StationSettingsForm,
)
from .models import (
    AuditEvent,
    BirthdayPreference,
    CalendarEvent,
    Checklist,
    ChecklistCompletion,
    CoffeeEntry,
    FeedItem,
    FeedSource,
    HandoverEntry,
    Membership,
)
from .services import audit, change_handover_status, create_handover


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})


def access(request):
    membership = None
    if request.user.is_authenticated:
        membership = request.user.station_memberships.filter(
            is_active=True, station__is_active=True
        ).select_related("station").first()
        if membership:
            if membership.role == Membership.Role.AUDITOR:
                return redirect("audit_log")
            return redirect("dashboard")
    return render(request, "core/access.html", {"membership": membership})


@membership_required(CONTENT_ROLES)
def dashboard(request):
    station = request.membership.station
    now = timezone.now()
    active = prioritized_handovers(station)
    events = CalendarEvent.objects.none()
    if station.calendar_enabled:
        events = CalendarEvent.objects.filter(
            station=station, ends_at__gte=now
        ).order_by("starts_at")[:3]
    context = {
        "open_handovers": active[:5],
        "open_count": active.count(),
        "urgent_count": active.filter(priority=HandoverEntry.Priority.URGENT).count(),
        "events": events,
        "calendar_enabled": station.calendar_enabled,
    }
    return render(request, "core/dashboard.html", context)


def prioritized_handovers(station):
    return (
        HandoverEntry.objects.filter(station=station)
        .exclude(status=HandoverEntry.Status.DONE)
        .select_related("author")
        .annotate(
            priority_rank=Case(
                When(priority=HandoverEntry.Priority.URGENT, then=Value(0)),
                When(priority=HandoverEntry.Priority.IMPORTANT, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            ),
            status_rank=Case(
                When(status=HandoverEntry.Status.OPEN, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
        )
        .order_by("priority_rank", "status_rank", "-updated_at")
    )


def page_for(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("seite"))


def upcoming_birthdays(station):
    today = timezone.localdate()
    preferences = list(
        BirthdayPreference.objects.filter(station=station, is_visible=True)
        .select_related("user")
    )
    def next_date(item):
        for year in range(today.year, today.year + 5):
            try:
                candidate = date(year, item.month, item.day)
            except ValueError:
                continue
            if candidate >= today:
                return candidate
        return date.max

    return sorted(preferences, key=next_date)


@membership_required(CONTENT_ROLES)
def handover_list(request):
    scope = request.GET.get("ansicht", "aktiv")
    if scope == "archiv":
        handovers = HandoverEntry.objects.filter(
            station=request.membership.station,
            status=HandoverEntry.Status.DONE,
        ).select_related("author").order_by("-completed_at", "-updated_at")
    else:
        scope = "dringend" if scope == "dringend" else "aktiv"
        handovers = prioritized_handovers(request.membership.station)
        if scope == "dringend":
            handovers = handovers.filter(priority=HandoverEntry.Priority.URGENT)
    return render(request, "core/handover_list.html", {
        "page_obj": page_for(request, handovers),
        "scope": scope,
    })


@membership_required(CONTENT_ROLES)
@require_http_methods(["GET", "POST"])
def handover_create(request):
    form = HandoverForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        handover = create_handover(form, request.membership)
        messages.success(request, "Übergabe wurde angelegt.")
        return redirect("handover_detail", pk=handover.pk)
    return render(request, "core/handover_form.html", {"form": form})


@membership_required(CONTENT_ROLES)
def handover_detail(request, pk):
    handover = get_object_or_404(
        HandoverEntry.objects.select_related("author").prefetch_related("revisions__changed_by"),
        pk=pk,
        station=request.membership.station,
    )
    can_change_status = request.membership.role in {
        Membership.Role.SHIFT_LEAD,
        Membership.Role.ADMIN,
    }
    return render(request, "core/handover_detail.html", {
        "handover": handover,
        "status_form": HandoverStatusForm(instance=handover),
        "can_change_status": can_change_status,
    })


@membership_required({Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN})
@require_POST
def handover_status(request, pk):
    handover = get_object_or_404(HandoverEntry, pk=pk, station=request.membership.station)
    form = HandoverStatusForm(request.POST, instance=handover)
    if form.is_valid():
        change_handover_status(handover, form.cleaned_data["status"], request.membership)
        messages.success(request, "Status wurde aktualisiert.")
    else:
        messages.error(request, "Status konnte nicht aktualisiert werden.")
    return redirect("handover_detail", pk=pk)


@membership_required(CONTENT_ROLES)
@station_module_required("calendar_enabled")
def calendar_view(request):
    station = request.membership.station
    can_create = request.membership.role in {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN}
    events = CalendarEvent.objects.filter(
        station=station,
        ends_at__gte=timezone.now() - timedelta(days=1),
    ).select_related("created_by")
    return render(request, "core/calendar.html", {
        "page_obj": page_for(request, events, 15),
        "can_create": can_create,
    })


@membership_required({Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN})
@station_module_required("calendar_enabled")
@require_http_methods(["GET", "POST"])
def calendar_create(request):
    form = CalendarEventForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            event = form.save(commit=False)
            event.station = request.membership.station
            event.created_by = request.user
            event.full_clean()
            event.save()
            audit(request.user, request.membership.station, "calendar.created", event, {"fields": [
                "title", "description", "starts_at", "ends_at"
            ]})
        messages.success(request, "Termin wurde angelegt.")
        return redirect("calendar")
    return render(request, "core/calendar_form.html", {"form": form})


@membership_required(CONTENT_ROLES)
@station_module_required("birthdays_enabled")
def birthdays(request):
    return render(request, "core/birthdays.html", {
        "birthdays": upcoming_birthdays(request.membership.station),
    })


@membership_required(CONTENT_ROLES)
@station_module_required("birthdays_enabled")
@require_http_methods(["GET", "POST"])
def birthday_settings(request):
    preference, _ = BirthdayPreference.objects.get_or_create(
        user=request.user,
        station=request.membership.station,
    )
    form = BirthdayForm(request.POST or None, instance=preference)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            saved = form.save()
            audit(request.user, request.membership.station, "birthday.preference_changed", saved, {
                "fields": ["day", "month", "is_visible"]
            })
        messages.success(request, "Geburtstagseinstellung wurde gespeichert.")
        return redirect("birthdays")
    return render(request, "core/birthday_settings.html", {
        "form": form,
    })


@membership_required(CONTENT_ROLES)
@station_module_required("coffee_enabled")
def coffee(request):
    station = request.membership.station
    can_book = request.membership.role in {Membership.Role.CASHIER, Membership.Role.ADMIN}
    all_entries = CoffeeEntry.objects.filter(station=station).select_related(
        "member", "created_by", "correction_of"
    ).prefetch_related("corrections")
    visible_entries = all_entries if can_book else all_entries.filter(member=request.user)
    total_cents = all_entries.aggregate(total=Sum("amount_cents"))["total"] or 0
    own_cents = all_entries.filter(member=request.user).aggregate(total=Sum("amount_cents"))["total"] or 0
    return render(request, "core/coffee.html", {
        "page_obj": page_for(request, visible_entries, 25),
        "total_euros": total_cents / 100,
        "own_euros": own_cents / 100,
        "can_book": can_book,
    })


@membership_required({Membership.Role.CASHIER, Membership.Role.ADMIN})
@station_module_required("coffee_enabled")
@require_http_methods(["GET", "POST"])
def coffee_create(request):
    station = request.membership.station
    form = CoffeeEntryForm(request.POST or None, station=station)
    if request.method == "POST" and form.is_valid():
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
        messages.success(request, "Kassenbuchung wurde erfasst.")
        return redirect("coffee")
    return render(request, "core/coffee_form.html", {"form": form})


@membership_required({Membership.Role.CASHIER, Membership.Role.ADMIN})
@station_module_required("coffee_enabled")
@require_http_methods(["GET", "POST"])
def coffee_correct(request, pk):
    original = get_object_or_404(
        CoffeeEntry.objects.select_related("member"),
        pk=pk,
        station=request.membership.station,
        correction_of__isnull=True,
    )
    if original.corrections.exists():
        messages.error(request, "Diese Buchung wurde bereits korrigiert.")
        return redirect("coffee")
    form = CoffeeCorrectionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            correction = CoffeeEntry.objects.create(
                station=original.station,
                member=original.member,
                amount_cents=-original.amount_cents,
                reason=form.cleaned_data["reason"],
                created_by=request.user,
                correction_of=original,
            )
            audit(request.user, original.station, "coffee.entry_corrected", correction, {
                "fields": ["reason", "correction_of"]
            })
        messages.success(request, "Gegenbuchung wurde erfasst.")
        return redirect("coffee")
    return render(request, "core/coffee_correction.html", {
        "form": form,
        "original": original,
        "correction_euros": -original.amount_cents / 100,
    })


@membership_required(CONTENT_ROLES)
@station_module_required("feeds_enabled")
def feeds(request):
    feed_type = "verkehr" if request.GET.get("typ") == "verkehr" else "meldungen"
    kind = FeedSource.Kind.CLOSURE_CSV if feed_type == "verkehr" else FeedSource.Kind.NEWS_RSS
    items = FeedItem.objects.filter(source__kind=kind).select_related("source")
    return render(request, "core/feeds.html", {
        "page_obj": page_for(request, items, 25),
        "feed_type": feed_type,
        "sources": FeedSource.objects.filter(is_enabled=True),
    })


def active_checklists(station):
    return (
        Checklist.objects.filter(station=station, is_active=True)
        .prefetch_related("items")
    )


@membership_required(CONTENT_ROLES)
@station_module_required("checklists_enabled")
def checklists(request):
    station = request.membership.station
    checklists_qs = list(active_checklists(station))
    latest = {}
    for completion in (
        ChecklistCompletion.objects.filter(station=station)
        .select_related("completed_by", "checklist")
        .order_by("checklist_id", "-created_at")
    ):
        latest.setdefault(completion.checklist_id, completion)
    for checklist in checklists_qs:
        checklist.latest_completion = latest.get(checklist.id)
    return render(request, "core/checklists.html", {"checklists": checklists_qs})


@membership_required(CONTENT_ROLES)
@station_module_required("checklists_enabled")
@require_POST
def checklist_complete(request, pk):
    station = request.membership.station
    checklist = get_object_or_404(Checklist, pk=pk, station=station, is_active=True)
    with transaction.atomic():
        completion = ChecklistCompletion.objects.create(
            station=station,
            checklist=checklist,
            completed_by=request.user,
            note=request.POST.get("note", "")[:300],
        )
        audit(request.user, station, "checklist.completed", completion, {
            "fields": ["checklist", "note"]
        })
    messages.success(request, "Checkliste wurde als erledigt vermerkt.")
    return redirect("checklists")


@membership_required(CONTENT_ROLES)
def more(request):
    return render(request, "core/more.html")


@membership_required({Membership.Role.ADMIN})
def team(request):
    station = request.membership.station
    members = Membership.objects.filter(station=station).select_related("user")
    pending_count = User.objects.filter(is_active=True).exclude(
        station_memberships__is_active=True
    ).count()
    return render(request, "core/team.html", {
        "page_obj": page_for(request, members, 25),
        "pending_count": pending_count,
    })


@membership_required({Membership.Role.ADMIN})
@require_http_methods(["GET", "POST"])
def team_create(request):
    form = MembershipAssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            membership = Membership.objects.create(
                user=form.cleaned_data["user"],
                station=request.membership.station,
                role=form.cleaned_data["role"],
            )
            audit(request.user, request.membership.station, "membership.created", membership, {
                "fields": ["user", "role", "is_active"]
            })
        messages.success(request, "Mitgliedschaft wurde freigegeben.")
        return redirect("team")
    return render(request, "core/team_form.html", {
        "form": form,
    })


@membership_required({Membership.Role.ADMIN})
@require_http_methods(["GET", "POST"])
def membership_update(request, pk):
    membership = get_object_or_404(Membership, pk=pk, station=request.membership.station)
    form = MembershipEditForm(request.POST or None, membership=membership)
    if request.method == "POST" and form.is_valid():
        new_role = form.cleaned_data["role"]
        new_active = form.cleaned_data["is_active"]
        removes_admin = (
            membership.role == Membership.Role.ADMIN
            and membership.is_active
            and (new_role != Membership.Role.ADMIN or not new_active)
        )
        if membership.user_id == request.user.id and removes_admin:
            form.add_error("role", "Die eigene Adminrolle kann hier nicht entzogen werden.")
        with transaction.atomic():
            if not form.errors:
                membership = Membership.objects.select_for_update().get(pk=membership.pk)
                if removes_admin:
                    admin_ids = list(Membership.objects.select_for_update().filter(
                        station=membership.station,
                        role=Membership.Role.ADMIN,
                        is_active=True,
                    ).values_list("pk", flat=True))
                    if len(admin_ids) <= 1:
                        form.add_error("role", "Mindestens ein aktiver Admin muss erhalten bleiben.")
            if not form.errors:
                membership.role = form.cleaned_data["role"]
                membership.is_active = form.cleaned_data["is_active"]
                membership.save(update_fields=["role", "is_active"])
                audit(request.user, request.membership.station, "membership.updated", membership, {
                    "fields": ["role", "is_active"]
                })
                messages.success(request, "Mitgliedschaft wurde aktualisiert.")
        if not form.errors:
            return redirect("team")
    return render(request, "core/membership_form.html", {
        "form": form,
        "edited_membership": membership,
    })


@membership_required({Membership.Role.ADMIN})
@require_http_methods(["GET", "POST"])
def station_settings(request):
    station = request.membership.station
    form = StationSettingsForm(request.POST or None, instance=station)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            changed_fields = [
                field for field in form.changed_data if field in form.fields
            ]
            saved = form.save()
            audit(request.user, station, "station.settings_updated", saved, {
                "fields": changed_fields,
            })
        messages.success(request, "Einstellungen wurden gespeichert.")
        return redirect("station_settings")
    return render(request, "core/station_settings.html", {"form": form})


@membership_required({Membership.Role.AUDITOR, Membership.Role.ADMIN})
def audit_log(request):
    events = AuditEvent.objects.filter(station=request.membership.station).select_related("actor")
    return render(request, "core/audit_log.html", {"page_obj": page_for(request, events, 30)})
