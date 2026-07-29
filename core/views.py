from datetime import date, timedelta
from io import BytesIO

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Case, IntegerField, Q, Sum, Value, When
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .access import (
    CONTENT_ROLES,
    SESSION_STATION_KEY,
    available_memberships,
    get_membership,
    membership_required,
    station_module_required,
)

from .forms import (
    BirthdayForm,
    CalendarEventForm,
    CoffeeCorrectionForm,
    CoffeeEntryForm,
    CoffeePaymentForm,
    DailyTeamForm,
    HandoverForm,
    HandoverStatusForm,
    MembershipAssignmentForm,
    MembershipEditForm,
    SetupBasicsForm,
    SetupModulesForm,
    StationSettingsForm,
    WasteSourceForm,
)
from .geocoding import GeocodingError, lookup_district
from .pdf import build_week_pdf
from .models import (
    AuditEvent,
    BirthdayPreference,
    CalendarEvent,
    CoffeeEntry,
    DailyTeamNote,
    FeedItem,
    FeedSource,
    HandoverEntry,
    Membership,
    Station,
)
from .throttle import password_reset_is_throttled
from .services import (
    acknowledge_handover,
    audit,
    change_handover_status,
    create_handover,
    set_daily_team,
    update_handover,
)


class ThrottledPasswordResetView(auth_views.PasswordResetView):
    """Ohne Drosselung koennte jemand beliebig viele Reset-Mails an eine
    bekannte Adresse ausloesen. Gedrosselte Versuche bekommen dieselbe Antwort
    wie erfolgreiche, damit sich daraus nichts ueber vorhandene Konten ablesen
    laesst."""

    def post(self, request, *args, **kwargs):
        if password_reset_is_throttled(
            request.POST.get("email", ""), request.META.get("REMOTE_ADDR", ""),
        ):
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)


def healthz(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})


def imprint(request):
    return render(request, "core/imprint.html")


def privacy(request):
    return render(request, "core/privacy.html")


def accessibility(request):
    return render(request, "core/accessibility.html")


DEMO_SESSION_KEY = "is_demo_session"


def demo(request):
    return render(request, "core/demo.html", {
        "demo_available": settings.DEMO_MODE and _demo_visitor() is not None,
    })


def _demo_visitor():
    """Das Demokonto, sofern die Demowache eingerichtet ist."""
    if not settings.DEMO_MODE:
        return None
    station = Station.objects.filter(slug=settings.DEMO_STATION_SLUG, is_active=True).first()
    if station is None:
        return None
    membership = Membership.objects.select_related("user").filter(
        station=station, user__username=settings.DEMO_USERNAME, is_active=True,
    ).first()
    return membership.user if membership else None


@require_POST
def demo_start(request):
    """Meldet Besucher als Demokonto an. Nur bei DEMO_MODE=true erreichbar -
    eine Instanz mit echten Wachendaten laesst das nicht zu."""
    visitor = _demo_visitor()
    if visitor is None:
        raise Http404
    login(request, visitor, backend="django.contrib.auth.backends.ModelBackend")
    request.session[DEMO_SESSION_KEY] = True
    # Kein Hinweis als Meldung: der dauerhafte Banner sagt bereits dasselbe.
    return redirect("dashboard")


def access(request):
    membership = None
    if request.user.is_authenticated:
        membership = get_membership(request.user, request.session)
        if membership:
            if membership.role == Membership.Role.AUDITOR:
                return redirect("audit_log")
            return redirect("dashboard")
    return render(request, "core/access.html", {"membership": membership})


@membership_required(CONTENT_ROLES)
def dashboard(request):
    station = request.membership.station
    if request.membership.role == Membership.Role.ADMIN and not station.onboarded:
        return redirect("setup_wizard")
    now = timezone.now()
    active = prioritized_handovers(station)
    events = CalendarEvent.objects.none()
    if station.calendar_enabled:
        events = CalendarEvent.objects.filter(
            station=station, ends_at__gte=now
        ).order_by("starts_at")[:3]
    unread_urgent = active.filter(priority=HandoverEntry.Priority.URGENT).exclude(
        acknowledgements__user=request.user
    )
    context = {
        "open_handovers": active[:5],
        "open_count": active.count(),
        "urgent_count": active.filter(priority=HandoverEntry.Priority.URGENT).count(),
        "unread_urgent": unread_urgent[:5],
        "unread_urgent_count": unread_urgent.count(),
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


SETUP_STEPS = ["basics", "modules", "done"]
SETUP_TITLES = {
    "basics": "Name und Standort",
    "modules": "Module aktivieren",
    "done": "Fertig eingerichtet",
}
SETUP_HINTS = {
    "basics": "So heisst die Wache im Kopfbereich der Anwendung.",
    "modules": "Nur aktivierte Module erscheinen im Menue. Jederzeit spaeter unter Einstellungen aenderbar.",
    "done": "",
}
SETUP_FORMS = {
    "basics": SetupBasicsForm,
    "modules": SetupModulesForm,
}


@membership_required({Membership.Role.ADMIN})
def setup_wizard(request, step="basics"):
    if step not in SETUP_STEPS:
        raise Http404
    station = request.membership.station
    step_index = SETUP_STEPS.index(step)
    context = {
        "step": step,
        "steps": SETUP_STEPS,
        "step_index": step_index,
        "step_number": step_index + 1,
        "step_count": len(SETUP_STEPS),
        "step_title": SETUP_TITLES[step],
        "step_hint": SETUP_HINTS[step],
        "station": station,
    }

    if request.method == "POST" and "skip_all" in request.POST:
        station.onboarded = True
        station.save(update_fields=["onboarded"])
        audit(request.user, station, "station.onboarding_skipped", station, {"step": step})
        messages.info(
            request,
            "Einrichtung übersprungen - alles lässt sich jederzeit unter Einstellungen anpassen.",
        )
        return redirect("dashboard")

    if step == "done":
        if request.method == "POST":
            station.onboarded = True
            station.save(update_fields=["onboarded"])
            audit(request.user, station, "station.onboarding_completed", station, {})
            messages.success(request, "Einrichtung abgeschlossen.")
            return redirect("dashboard")
        return render(request, "core/setup_wizard.html", context)

    form_class = SETUP_FORMS[step]
    form = form_class(request.POST or None, instance=station)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            changed_fields = [field for field in form.changed_data if field in form.fields]
            form.save()
            if changed_fields:
                audit(request.user, station, "station.onboarding_step_saved", station, {
                    "step": step, "fields": changed_fields,
                })
        return redirect("setup_wizard", step=SETUP_STEPS[step_index + 1])
    context["form"] = form
    return render(request, "core/setup_wizard.html", context)


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
    query = request.GET.get("q", "").strip()
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
    if query:
        handovers = handovers.filter(
            Q(title__icontains=query) | Q(details__icontains=query)
        )
    return render(request, "core/handover_list.html", {
        "page_obj": page_for(request, handovers),
        "scope": scope,
        "query": query,
        "result_count": handovers.count() if query else None,
    })


@membership_required(CONTENT_ROLES)
@require_http_methods(["GET", "POST"])
def handover_create(request):
    form = HandoverForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        handover = create_handover(form, request.membership)
        messages.success(request, "Uebergabe wurde angelegt.")
        return redirect("handover_detail", pk=handover.pk)
    return render(request, "core/handover_form.html", {"form": form})


def may_edit_handover(membership, handover):
    """Verfasserin/Verfasser korrigiert eigene Eintraege, Schichtleitung und
    Admin auch fremde. Jede Aenderung erzeugt eine Revision."""
    return (
        handover.author_id == membership.user_id
        or membership.role in {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN}
    )


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
    needs_ack = handover.priority == HandoverEntry.Priority.URGENT
    team_size = Membership.objects.filter(
        station=request.membership.station, is_active=True,
    ).exclude(role=Membership.Role.AUDITOR).count() if needs_ack else 0
    ack_count = handover.acknowledgements.count() if needs_ack else 0
    return render(request, "core/handover_detail.html", {
        "handover": handover,
        "status_form": HandoverStatusForm(instance=handover),
        "can_change_status": can_change_status,
        "can_edit": may_edit_handover(request.membership, handover),
        "needs_acknowledgement": needs_ack,
        "acknowledged_by_me": needs_ack and handover.acknowledgements.filter(
            user=request.user
        ).exists(),
        "acknowledgements": handover.acknowledgements.select_related("user") if needs_ack else [],
        "team_size": team_size,
        "ack_count": ack_count,
        # In 5er-Schritten als CSS-Klasse: die Content-Security-Policy
        # verbietet Inline-Styles, deshalb keine berechnete style-Angabe.
        "ack_step": round(ack_count / team_size * 20) * 5 if team_size else 0,
    })


@membership_required(CONTENT_ROLES)
@require_POST
def handover_acknowledge(request, pk):
    handover = get_object_or_404(
        HandoverEntry, pk=pk, station=request.membership.station,
        priority=HandoverEntry.Priority.URGENT,
    )
    acknowledge_handover(handover, request.membership)
    messages.success(request, "Danke, als gelesen vermerkt.")
    return redirect("handover_detail", pk=pk)


@membership_required(CONTENT_ROLES)
@require_http_methods(["GET", "POST"])
def handover_edit(request, pk):
    handover = get_object_or_404(
        HandoverEntry, pk=pk, station=request.membership.station,
    )
    if not may_edit_handover(request.membership, handover):
        raise PermissionDenied
    form = HandoverForm(request.POST or None, instance=handover)
    if request.method == "POST" and form.is_valid():
        update_handover(handover, form, request.membership)
        messages.success(request, "Uebergabe wurde aktualisiert.")
        return redirect("handover_detail", pk=handover.pk)
    return render(request, "core/handover_form.html", {
        "form": form,
        "handover": handover,
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


def _week_start(year, week):
    try:
        return date.fromisocalendar(int(year), int(week), 1)
    except (ValueError, TypeError):
        today = timezone.localdate()
        return today - timedelta(days=today.isoweekday() - 1)


def week_protocol(station, monday):
    """Tage der Woche mit Team und Eintraegen sowie die Eintraege ohne
    Tagesbezug - gemeinsame Grundlage fuer Web-Ansicht und PDF."""
    week_days = [monday + timedelta(days=offset) for offset in range(7)]
    team_notes = {
        note.date: note
        for note in DailyTeamNote.objects.filter(station=station, date__in=week_days)
    }
    day_entries = {day: [] for day in week_days}
    for entry in HandoverEntry.objects.filter(
        station=station, for_date__in=week_days
    ).select_related("author"):
        day_entries[entry.for_date].append(entry)

    days = [
        {"date": day, "team_note": team_notes.get(day), "entries": day_entries[day]}
        for day in week_days
    ]
    general_entries = (
        HandoverEntry.objects.filter(station=station, for_date__isnull=True)
        .exclude(status=HandoverEntry.Status.DONE)
        .select_related("author")[:20]
    )
    return days, general_entries


@membership_required(CONTENT_ROLES)
def handover_week_pdf(request):
    station = request.membership.station
    today = timezone.localdate()
    default_year, default_week, _ = today.isocalendar()
    monday = _week_start(
        request.GET.get("jahr", default_year), request.GET.get("kw", default_week)
    )
    year, week, _ = monday.isocalendar()
    days, general_entries = week_protocol(station, monday)

    buffer = BytesIO()
    build_week_pdf(buffer, station, year, week, days, general_entries)
    buffer.seek(0)
    filename = f"wochenprotokoll-kw{week:02d}-{year}.pdf"
    response = FileResponse(buffer, as_attachment=True, filename=filename)
    audit(request.user, station, "handover.week_exported", station, {
        "year": year, "week": week,
    })
    return response


@membership_required(CONTENT_ROLES)
def handover_week(request):
    station = request.membership.station
    today = timezone.localdate()
    default_year, default_week, _ = today.isocalendar()
    monday = _week_start(
        request.GET.get("jahr", default_year), request.GET.get("kw", default_week)
    )
    week_days = [monday + timedelta(days=offset) for offset in range(7)]
    year, week, _ = monday.isocalendar()
    days, general_entries = week_protocol(station, monday)

    previous_monday = monday - timedelta(days=7)
    next_monday = monday + timedelta(days=7)
    prev_year, prev_week, _ = previous_monday.isocalendar()
    next_year, next_week, _ = next_monday.isocalendar()

    return render(request, "core/handover_week.html", {
        "days": days,
        "general_entries": general_entries,
        "year": year,
        "week": week,
        "monday": monday,
        "sunday": week_days[-1],
        "prev_year": prev_year,
        "prev_week": prev_week,
        "next_year": next_year,
        "next_week": next_week,
        "can_edit_team": request.membership.role in {Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN},
    })


@membership_required({Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN})
@require_POST
def daily_team_update(request, tag):
    try:
        day = date.fromisoformat(tag)
    except ValueError as exc:
        raise Http404 from exc
    form = DailyTeamForm(request.POST)
    if form.is_valid():
        set_daily_team(request.membership.station, day, form.cleaned_data["note"], request.membership)
        messages.success(request, "Team wurde gespeichert.")
    else:
        messages.error(request, "Team konnte nicht gespeichert werden.")
    year, week, _ = day.isocalendar()
    return redirect(f"{reverse('handover_week')}?jahr={year}&kw={week}")


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
    is_admin = request.membership.role == Membership.Role.ADMIN
    return render(request, "core/coffee.html", {
        "page_obj": page_for(request, visible_entries, 25),
        "total_euros": total_cents / 100,
        "own_euros": own_cents / 100,
        "can_book": can_book,
        "station": station,
        "payment_form": CoffeePaymentForm(instance=station) if is_admin else None,
    })


@membership_required({Membership.Role.ADMIN})
@station_module_required("coffee_enabled")
@require_POST
def coffee_payment_update(request):
    station = request.membership.station
    form = CoffeePaymentForm(request.POST, instance=station)
    if form.is_valid():
        with transaction.atomic():
            changed_fields = [field for field in form.changed_data if field in form.fields]
            saved = form.save()
            audit(request.user, station, "coffee.payment_settings_updated", saved, {
                "fields": changed_fields,
            })
        messages.success(request, "Zahlungsangaben wurden gespeichert.")
    else:
        errors = " ".join(f"{field}: {', '.join(msgs)}" for field, msgs in form.errors.items())
        messages.error(request, f"Zahlungsangaben konnten nicht gespeichert werden. {errors}")
    return redirect("coffee")


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
    station = request.membership.station
    feed_type = request.GET.get("typ", "meldungen")
    if feed_type not in {"meldungen", "verkehr", "muell"}:
        feed_type = "meldungen"

    if feed_type == "muell":
        waste_source = FeedSource.objects.filter(
            station=station, kind=FeedSource.Kind.WASTE_ICS
        ).first()
        items = (
            FeedItem.objects.filter(source=waste_source, starts_on__gte=timezone.localdate())
            .order_by("starts_on")
            if waste_source else FeedItem.objects.none()
        )
        return render(request, "core/feeds.html", {
            "page_obj": page_for(request, items, 25),
            "feed_type": feed_type,
            "sources": [waste_source] if waste_source else [],
            "waste_form": WasteSourceForm(instance=waste_source),
            "can_configure_waste": request.membership.role == Membership.Role.ADMIN,
        })

    kind = FeedSource.Kind.CLOSURE_CSV if feed_type == "verkehr" else FeedSource.Kind.NEWS_RSS
    sources = FeedSource.objects.filter(is_enabled=True, kind=kind, station__isnull=True)
    localities = station.localities
    if localities:
        locality_match = Q()
        for value in localities:
            locality_match |= Q(locality__iexact=value)
        sources = sources.filter(locality_match)
    items = FeedItem.objects.filter(source__in=sources).select_related("source")
    return render(request, "core/feeds.html", {
        "page_obj": page_for(request, items, 25),
        "feed_type": feed_type,
        "sources": sources,
    })


@membership_required({Membership.Role.ADMIN})
@station_module_required("feeds_enabled")
@require_POST
def waste_source_update(request):
    station = request.membership.station
    source = FeedSource.objects.filter(station=station, kind=FeedSource.Kind.WASTE_ICS).first()
    form = WasteSourceForm(request.POST, instance=source)
    if form.is_valid():
        with transaction.atomic():
            saved = form.save(commit=False)
            saved.station = station
            saved.kind = FeedSource.Kind.WASTE_ICS
            saved.is_enabled = True
            if not saved.pk:
                saved.name = f"Muellabfuhr {station.slug}"
                saved.locality = station.city or station.name
                saved.attribution = "Oertliche Abfallwirtschaft"
            saved.full_clean()
            saved.save()
            audit(request.user, station, "feeds.waste_source_updated", saved, {"fields": ["url"]})
        messages.success(
            request,
            "Abfallkalender wurde gespeichert. Die naechste Synchronisierung zeigt die Termine an.",
        )
    else:
        messages.error(request, "Abfallkalender-Link konnte nicht gespeichert werden.")
    return redirect(f"{reverse('feeds')}?typ=muell")


@membership_required({Membership.Role.ADMIN})
@require_POST
def station_geocode(request):
    station = request.membership.station
    try:
        result = lookup_district(station.street, station.postal_code, station.city)
    except GeocodingError as exc:
        messages.error(request, str(exc))
        return redirect("station_settings")
    changed_fields = []
    if result["district"] and result["district"] != station.district:
        station.district = result["district"]
        changed_fields.append("district")
    if result["city"] and result["city"] != station.city:
        station.city = result["city"]
        changed_fields.append("city")
    if not station.location and (result["city"] or result["district"]):
        station.location = result["city"] or result["district"]
        changed_fields.append("location")
    if changed_fields:
        with transaction.atomic():
            station.save(update_fields=changed_fields)
            audit(request.user, station, "station.geocoded", station, {"fields": changed_fields})
        messages.success(request, "Ort/Kreis wurden anhand der Adresse aktualisiert.")
    else:
        messages.info(request, "Keine Aenderung: Ort/Kreis stimmen bereits mit der Adresse ueberein.")
    return redirect("station_settings")


@membership_required(CONTENT_ROLES)
def more(request):
    return render(request, "core/more.html")


@membership_required()
@require_POST
def switch_station(request):
    """Wechsel zwischen den Wachen, auf denen jemand freigegeben ist."""
    try:
        target = int(request.POST.get("station", ""))
    except (TypeError, ValueError):
        raise Http404
    membership = available_memberships(request.user).filter(station_id=target).first()
    if membership is None:
        raise PermissionDenied
    request.session[SESSION_STATION_KEY] = membership.station_id
    messages.success(request, f"Aktive Wache: {membership.station.name}.")
    if membership.role == Membership.Role.AUDITOR:
        return redirect("audit_log")
    return redirect("dashboard")


@membership_required({Membership.Role.ADMIN})
def team(request):
    station = request.membership.station
    members = Membership.objects.filter(station=station).select_related("user")
    # Nur Konten ganz ohne Wache gelten als wartend. Konten anderer Wachen
    # bleiben bewusst unsichtbar.
    pending_count = User.objects.filter(is_active=True, station_memberships__isnull=True).count()
    return render(request, "core/team.html", {
        "page_obj": page_for(request, members, 25),
        "pending_count": pending_count,
    })


@membership_required({Membership.Role.ADMIN})
@require_http_methods(["GET", "POST"])
def team_create(request):
    form = MembershipAssignmentForm(
        request.POST or None, station=request.membership.station,
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            membership = Membership.objects.create(
                user=form.user,
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
