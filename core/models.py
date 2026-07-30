import re
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def validate_iban(value):
    """Akzeptiert IBANs mit und ohne Gruppierungsleerzeichen."""
    if not value:
        return
    compact = value.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}", compact):
        raise ValidationError("Das sieht nicht nach einer gueltigen IBAN aus.")


class Station(models.Model):
    class TaskAttribution(models.TextChoices):
        PERSON = "person", "Name der Person anzeigen"
        NONE = "none", "Keinen Namen anzeigen (gemeinsames Wachengeraet)"

    name = models.CharField(max_length=120)
    location = models.CharField(max_length=160, blank=True, verbose_name="Standort")
    street = models.CharField(max_length=160, blank=True, verbose_name="Strasse und Hausnummer")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    city = models.CharField(max_length=120, blank=True, verbose_name="Ort")
    district = models.CharField(max_length=120, blank=True, verbose_name="Kreis/Landkreis")
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    calendar_enabled = models.BooleanField(default=True, verbose_name="Kalender aktiviert")
    birthdays_enabled = models.BooleanField(default=True, verbose_name="Geburtstage aktiviert")
    coffee_enabled = models.BooleanField(default=True, verbose_name="Kaffeekasse aktiviert")
    tasks_enabled = models.BooleanField(default=True, verbose_name="Aufgaben aktiviert")
    feeds_enabled = models.BooleanField(default=False, verbose_name="Externe Meldungen aktiviert")
    coffee_paypal_link = models.CharField(
        max_length=200, blank=True, verbose_name="PayPal.me-Link",
    )
    coffee_wero_link = models.CharField(
        max_length=200, blank=True, verbose_name="Wero-Zahlungslink oder -Kontakt",
    )
    coffee_iban = models.CharField(
        max_length=34, blank=True, verbose_name="IBAN", validators=[validate_iban],
    )
    coffee_account_holder = models.CharField(
        max_length=120, blank=True, verbose_name="Kontoinhaber/in",
    )
    # Ein Wachentag ist kein Kalendertag. Wo im 24-Stunden-Dienst um 07:00
    # uebergeben wird, gehoert der Haken um 02:00 Uhr noch zum Dienst, der am
    # Vortag begonnen hat. Ohne diese Angabe wuerde er auf dem falschen Tag
    # landen - und zwar in der Nacht, in der niemand nachrechnet.
    # 00:00 bedeutet: Betriebstag gleich Kalendertag.
    day_start_time = models.TimeField(
        default=time(7, 0), verbose_name="Betriebstag beginnt um",
        help_text=(
            "Uhrzeit, zu der auf dieser Wache der neue Wachentag anfaengt - "
            "in der Regel der Dienstbeginn der Fruehschicht. 00:00 bedeutet, "
            "dass der Wachentag dem Kalendertag entspricht."
        ),
    )
    task_attribution = models.CharField(
        max_length=10, choices=TaskAttribution.choices, default=TaskAttribution.PERSON,
        verbose_name="Namen bei Aufgaben",
        help_text=(
            "Haengt an der Wache ein gemeinsam genutztes Geraet, steht an jedem "
            "Haken derselbe Name. Dann ist es ehrlicher, gar keinen anzuzeigen."
        ),
    )
    onboarded = models.BooleanField(default=False, verbose_name="Einrichtung abgeschlossen")
    # 0 = keine automatische Loeschung. Die Fristen legt die verantwortliche
    # Stelle fest; Kassenbuchungen bleiben bewusst ausgenommen.
    retention_handover_days = models.PositiveIntegerField(
        default=0, verbose_name="Erledigte Uebergaben loeschen nach (Tagen)",
    )
    retention_calendar_days = models.PositiveIntegerField(
        default=0, verbose_name="Vergangene Termine loeschen nach (Tagen)",
    )
    retention_audit_days = models.PositiveIntegerField(
        default=0, verbose_name="Audit-Ereignisse loeschen nach (Tagen)",
    )
    retention_task_days = models.PositiveIntegerField(
        default=0, verbose_name="Erledigte Aufgaben loeschen nach (Tagen)",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def current_day(self, when=None):
        """Der Wachentag, der zu einem Zeitpunkt laeuft.

        Beginnt der Betriebstag um 07:00, dann gehoert alles zwischen 00:00 und
        06:59 noch zum Tag davor. Genau diese Stunden sind der Grund fuer die
        Methode: die Nachtstunden eines 24-Stunden-Dienstes.
        """
        local = timezone.localtime(when or timezone.now())
        day = local.date()
        if local.time() < self.day_start_time:
            day -= timedelta(days=1)
        return day

    def day_bounds(self, day):
        """Anfang und Ende eines Wachentages als Zeitpunkte - fuer Auswertungen
        und fuer die Zuordnung einer Schicht zu einem Tag."""
        start = timezone.make_aware(
            datetime.combine(day, self.day_start_time),
            timezone.get_current_timezone(),
        )
        return start, start + timedelta(days=1)

    @property
    def uses_calendar_day(self):
        return self.day_start_time == time(0, 0)

    @property
    def shows_task_person(self):
        return self.task_attribution == self.TaskAttribution.PERSON

    @property
    def localities(self):
        return {value for value in (self.city, self.district) if value}

    @property
    def has_coffee_payment_info(self):
        return bool(
            self.coffee_paypal_link or self.coffee_wero_link
            or (self.coffee_iban and self.coffee_account_holder)
        )

    @classmethod
    def get_default(cls):
        station = cls.objects.filter(slug=settings.DEFAULT_STATION_SLUG).first()
        if station is None and cls.objects.count() == 1:
            station = cls.objects.first()
        if station is None:
            station = cls.objects.create(
                slug=settings.DEFAULT_STATION_SLUG,
                name=settings.DEFAULT_STATION_NAME,
            )
        return station


class Membership(models.Model):
    class Role(models.TextChoices):
        MEMBER = "member", "Mitglied"
        SHIFT_LEAD = "shift_lead", "Schichtleitung"
        CASHIER = "cashier", "Kassenwart"
        ADMIN = "admin", "Admin"
        AUDITOR = "auditor", "Auditor"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="station_memberships")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MEMBER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Eine Mitgliedschaft je Person und Wache. Mehrere Wachen sind
        # ausdruecklich erlaubt: im Rettungsdienst arbeiten Springer und
        # Aushilfen regelmaessig auf mehr als einer Wache.
        constraints = [
            models.UniqueConstraint(fields=["user", "station"], name="unique_station_membership"),
        ]
        ordering = ["station", "user_id"]

    def __str__(self):
        return f"{self.user} - {self.station} ({self.get_role_display()})"


class TotpDevice(models.Model):
    """Zweiter Faktor per Authenticator-App (Google Authenticator, Aegis, ...).

    Der Schluessel liegt im Klartext in der Datenbank - so arbeiten auch die
    gaengigen Django-Bibliotheken, weil der Server ihn zum Pruefen im Klartext
    braucht. Wer die Datenbank lesen kann, kann Codes erzeugen; entsprechend
    zaehlt der Datenbankschutz zur Sicherheit des zweiten Faktors dazu.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp_device")
    secret = models.CharField(max_length=64)
    confirmed = models.BooleanField(default=False)
    # Verbrauchter Zeitschritt, damit ein abgefangener Code nicht erneut geht.
    last_timestep = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Zwei-Faktor fuer {self.user}"


class RecoveryCode(models.Model):
    """Einmalcodes fuer den Fall, dass das Geraet verloren geht. Gespeichert
    wird nur der Hash."""

    device = models.ForeignKey(TotpDevice, on_delete=models.CASCADE, related_name="recovery_codes")
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]


class HandoverEntry(models.Model):
    class Category(models.TextChoices):
        STATION = "station", "Wache"
        VEHICLE = "vehicle", "Fahrzeugstatus"
        MATERIAL = "material", "Material"
        TASK = "task", "Offene Aufgabe"
        SAFETY = "safety", "Sicherheit/Mangel"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        IMPORTANT = "important", "Wichtig"
        URGENT = "urgent", "Dringend"

    class Status(models.TextChoices):
        OPEN = "open", "Offen"
        IN_PROGRESS = "in_progress", "In Bearbeitung"
        DONE = "done", "Erledigt"

    station = models.ForeignKey(Station, on_delete=models.PROTECT, related_name="handovers")
    category = models.CharField(max_length=20, choices=Category.choices)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=160)
    details = models.TextField(max_length=3000)
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="authored_handovers")
    version = models.PositiveIntegerField(default=1)
    for_date = models.DateField(
        null=True, blank=True, verbose_name="Betrifft Tag",
        help_text="Leer lassen fuer Allgemeines ohne Tagesbezug.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [
            models.Index(fields=["station", "status", "-created_at"]),
            models.Index(fields=["station", "for_date"]),
        ]

    def __str__(self):
        return self.title


class HandoverRevision(models.Model):
    handover = models.ForeignKey(HandoverEntry, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveIntegerField()
    snapshot = models.JSONField()
    changed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["handover", "version"], name="unique_handover_version")
        ]
        ordering = ["-version"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Uebergaberevisionen duerfen nicht veraendert werden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Uebergaberevisionen duerfen nicht geloescht werden.")


class HandoverAcknowledgement(models.Model):
    """Bestaetigung, dass ein dringender Eintrag gelesen wurde. Bewusst ohne
    Auswertung je Person - nur die Wache sieht, wer noch fehlt."""

    handover = models.ForeignKey(
        HandoverEntry, on_delete=models.CASCADE, related_name="acknowledgements",
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="handover_acknowledgements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["handover", "user"], name="unique_handover_acknowledgement",
            )
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} hat {self.handover_id} gelesen"


class DailyTeamNote(models.Model):
    """Wer an einem Wachentag Dienst hatte.

    Bei zwei oder drei Besetzungen je Tag haengt der Eintrag an der Schicht.
    Wo nur eine Besetzung existiert, bleibt die Schicht leer und es gibt wie
    bisher genau eine Zeile je Tag.
    """

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="daily_team_notes")
    date = models.DateField()
    shift = models.ForeignKey(
        "Shift", on_delete=models.CASCADE, null=True, blank=True,
        related_name="team_notes", verbose_name="Schicht",
    )
    note = models.CharField(max_length=200, verbose_name="Team")
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Zwei Bedingungen statt einer: in SQL sind zwei NULL nicht gleich,
        # eine gemeinsame Bedingung ueber station/date/shift wuerde beliebig
        # viele schichtlose Zeilen je Tag durchlassen.
        constraints = [
            models.UniqueConstraint(
                fields=["station", "date"], condition=Q(shift__isnull=True),
                name="unique_station_day_team",
            ),
            models.UniqueConstraint(
                fields=["station", "date", "shift"], condition=Q(shift__isnull=False),
                name="unique_station_day_shift_team",
            ),
        ]
        ordering = ["date", "shift__position", "shift__start_time"]

    def __str__(self):
        label = f"{self.station} {self.date}"
        if self.shift_id:
            label = f"{label} {self.shift.name}"
        return f"{label}: {self.note}"


class Shift(models.Model):
    """Eine Besetzung innerhalb eines Wachentages.

    Der Rettungsdienst kennt kein einheitliches Schichtmodell: im Kreis
    Guetersloh laufen Fahrzeuge im 24-Stunden-Dienst, andere im 12-Stunden-
    Wechsel, und ein Tages-Standort wie Langenberg ist nur einen Teil des Tages
    besetzt. Die Wache beschreibt ihr Modell deshalb selbst, statt dass die
    Anwendung eines vorgibt.

    Wer nur eine Besetzung je Tag hat, legt genau eine Schicht an - oder gar
    keine, dann bleibt alles beim Wachentag.
    """

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=60, verbose_name="Bezeichnung")
    start_time = models.TimeField(verbose_name="Beginn")
    duration_minutes = models.PositiveIntegerField(
        default=1440, verbose_name="Dauer in Minuten",
        help_text="1440 Minuten sind 24 Stunden, 720 Minuten sind 12 Stunden.",
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "start_time", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["station", "name"], name="unique_station_shift_name"),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if not 1 <= (self.duration_minutes or 0) <= 1440:
            raise ValidationError({
                "duration_minutes": "Bitte eine Dauer zwischen 1 Minute und 24 Stunden angeben.",
            })

    @property
    def end_time(self):
        end = datetime.combine(date.min, self.start_time) + timedelta(
            minutes=self.duration_minutes
        )
        return end.time()

    @property
    def duration_label(self):
        hours, minutes = divmod(self.duration_minutes, 60)
        if minutes == 0:
            return f"{hours} h"
        return f"{hours}:{minutes:02d} h"

    @property
    def window_label(self):
        """"07:00 - 07:00 (24 h)" - die Form, in der Dienstplaene sie nennen."""
        return (
            f"{self.start_time.strftime('%H:%M')} - "
            f"{self.end_time.strftime('%H:%M')} ({self.duration_label})"
        )


WEEKDAY_NAMES = {
    1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa", 7: "So",
}


def validate_weekdays(value):
    """Wochentage stehen als ISO-Ziffern in einer Zeichenkette: "12345" ist
    Montag bis Freitag. Kompakt, ohne zusaetzliche Tabelle und in jeder
    Datenbank gleich."""
    if not value:
        raise ValidationError("Mindestens ein Wochentag muss ausgewaehlt sein.")
    digits = set(value)
    if not digits <= set("1234567") or len(digits) != len(value):
        raise ValidationError("Wochentage werden als Ziffern 1-7 ohne Wiederholung angegeben.")


class TaskList(models.Model):
    """Eine wiederkehrende Aufgabenliste einer Wache - das digitale Gegenstueck
    zu den Ankreuzfeldern unter "Tagesaufgaben" auf dem Papierbogen.

    Die Liste beschreibt nur, *was* wann faellig ist. Was an einem konkreten Tag
    tatsaechlich passiert ist, steht in TaskRun und TaskResult.
    """

    class Rhythm(models.TextChoices):
        WEEKDAYS = "weekdays", "An bestimmten Wochentagen"
        MONTHLY = "monthly", "Einmal im Monat"

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="task_lists")
    title = models.CharField(max_length=120, verbose_name="Name der Liste")
    rhythm = models.CharField(
        max_length=20, choices=Rhythm.choices, default=Rhythm.WEEKDAYS,
        verbose_name="Rhythmus",
    )
    weekdays = models.CharField(
        max_length=7, default="1234567", validators=[validate_weekdays],
        verbose_name="Wochentage",
    )
    day_of_month = models.PositiveSmallIntegerField(
        default=1, verbose_name="Tag im Monat",
        help_text="Faellt der Tag in einem Monat aus, gilt der letzte Tag des Monats.",
    )
    shift = models.ForeignKey(
        "Shift", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="task_lists", verbose_name="Schicht",
        help_text="Leer lassen, wenn die Liste einmal je Wachentag gilt.",
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.rhythm == self.Rhythm.MONTHLY and not 1 <= (self.day_of_month or 0) <= 31:
            raise ValidationError({"day_of_month": "Bitte einen Tag zwischen 1 und 31 angeben."})

    def occurs_on(self, day):
        if not self.is_active:
            return False
        if self.rhythm == self.Rhythm.MONTHLY:
            last = monthrange(day.year, day.month)[1]
            return day.day == min(self.day_of_month, last)
        return str(day.isoweekday()) in self.weekdays

    @property
    def rhythm_label(self):
        """Kurzform fuer die Anzeige, damit niemand Ziffernketten lesen muss."""
        if self.rhythm == self.Rhythm.MONTHLY:
            return f"Monatlich am {self.day_of_month}."
        if self.weekdays == "1234567":
            return "Täglich"
        if self.weekdays == "12345":
            return "Montag bis Freitag"
        return ", ".join(WEEKDAY_NAMES[int(digit)] for digit in sorted(self.weekdays))


class TaskItem(models.Model):
    """Ein abhakbarer Punkt einer Liste.

    Punkte werden nie geloescht, sondern nur deaktiviert: sonst waere nicht
    mehr nachvollziehbar, was an einem vergangenen Tag abgehakt wurde.
    """

    task_list = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=160, verbose_name="Aufgabe")
    note = models.CharField(
        max_length=300, blank=True, verbose_name="Hinweis",
        help_text="Optional, zum Beispiel wo etwas liegt oder worauf zu achten ist.",
    )
    position = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self):
        return self.title


class TaskRun(models.Model):
    """Eine Liste an einem konkreten Tag. Entsteht erst, wenn jemand den ersten
    Punkt abhakt - leere Tage erzeugen keine Datensaetze."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="task_runs")
    task_list = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="runs")
    date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task_list", "date"], name="unique_task_run_per_day")
        ]
        ordering = ["date"]
        indexes = [models.Index(fields=["station", "date"])]

    def __str__(self):
        return f"{self.task_list} am {self.date}"


class TaskResult(models.Model):
    """Der Haken an einem Punkt.

    Anders als Kassenbuchungen und Uebergaberevisionen ist ein Haken
    veraenderbar - auf einem Tablet vertippt man sich, und ein Wachbuch, in dem
    ein Fehlgriff fuer immer stehenbleibt, wird nicht benutzt. Jede Aenderung
    schreibt stattdessen ein Audit-Ereignis mit altem und neuem Stand.
    """

    class State(models.TextChoices):
        DONE = "done", "Erledigt"
        DEFECT = "defect", "Mangel"
        SKIPPED = "skipped", "Entfällt"

    run = models.ForeignKey(TaskRun, on_delete=models.CASCADE, related_name="results")
    item = models.ForeignKey(TaskItem, on_delete=models.PROTECT, related_name="results")
    state = models.CharField(max_length=20, choices=State.choices)
    note = models.CharField(max_length=300, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="task_results")
    recorded_at = models.DateTimeField(auto_now=True)
    handover = models.ForeignKey(
        HandoverEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="task_results",
        help_text="Der Uebergabe-Eintrag, der aus einem Mangel entstanden ist.",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["run", "item"], name="unique_task_result_per_item")
        ]
        ordering = ["item__position", "pk"]

    def __str__(self):
        return f"{self.item}: {self.get_state_display()}"


class CalendarEvent(models.Model):
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="calendar_events")
    title = models.CharField(max_length=160)
    description = models.TextField(max_length=1500, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at"]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at < self.starts_at:
            raise ValidationError({"ends_at": "Das Ende darf nicht vor dem Beginn liegen."})

    def __str__(self):
        return self.title


class BirthdayPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="birthday_preferences")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="birthdays")
    day = models.PositiveSmallIntegerField(null=True, blank=True)
    month = models.PositiveSmallIntegerField(null=True, blank=True)
    is_visible = models.BooleanField(default=False)
    consented_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "station"], name="unique_station_birthday")
        ]

    def clean(self):
        if self.is_visible and (not self.day or not self.month):
            raise ValidationError("Fuer die Anzeige werden Tag und Monat benoetigt.")
        if self.day and not 1 <= self.day <= 31:
            raise ValidationError({"day": "Ungueltiger Tag."})
        if self.month and not 1 <= self.month <= 12:
            raise ValidationError({"month": "Ungueltiger Monat."})


class CoffeeEntry(models.Model):
    station = models.ForeignKey(Station, on_delete=models.PROTECT, related_name="coffee_entries")
    member = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coffee_entries")
    amount_cents = models.IntegerField()
    reason = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recorded_coffee_entries")
    correction_of = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="corrections"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=~Q(amount_cents=0), name="coffee_amount_nonzero"),
            models.UniqueConstraint(
                fields=["correction_of"],
                condition=Q(correction_of__isnull=False),
                name="unique_coffee_correction",
            ),
        ]

    def clean(self):
        if self.correction_of:
            if self.correction_of.station_id != self.station_id:
                raise ValidationError("Die Korrektur muss zur gleichen Wache gehoeren.")
            if self.correction_of.member_id != self.member_id:
                raise ValidationError("Die Korrektur muss dieselbe Person betreffen.")
            if self.amount_cents != -self.correction_of.amount_cents:
                raise ValidationError("Eine Korrektur muss den exakten Gegenbetrag buchen.")
            if self.correction_of.correction_of_id:
                raise ValidationError("Eine Korrekturbuchung kann nicht erneut korrigiert werden.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Kassenbuchungen duerfen nicht veraendert werden.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Kassenbuchungen duerfen nicht geloescht werden.")

    @property
    def amount_euros(self):
        return self.amount_cents / 100


class FeedSource(models.Model):
    class Kind(models.TextChoices):
        NEWS_RSS = "news_rss", "Nachrichten (RSS)"
        CLOSURE_CSV = "closure_csv", "Verkehrsmeldungen (CSV)"
        WASTE_ICS = "waste_ics", "Muellabfuhr (ICS)"

    name = models.CharField(max_length=120, unique=True)
    url = models.URLField(max_length=600)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    locality = models.CharField(max_length=80, blank=True)
    attribution = models.CharField(max_length=200, blank=True)
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, null=True, blank=True, related_name="feed_sources",
        help_text="Nur fuer stationsbezogene Quellen wie den Muellkalender gesetzt.",
    )
    is_enabled = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["station"],
                condition=Q(kind="waste_ics"),
                name="unique_station_waste_source",
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        parsed = urlparse(self.url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValidationError({"url": "Die Portangabe ist ungueltig."}) from exc
        if parsed.scheme != "https" or port not in {None, 443}:
            raise ValidationError({"url": "Quellen muessen HTTPS auf Port 443 verwenden."})
        if parsed.hostname not in settings.FEED_ALLOWED_HOSTS:
            raise ValidationError({
                "url": "Der Host muss zuerst in FEED_ALLOWED_HOSTS freigegeben werden."
            })


class FeedItem(models.Model):
    source = models.ForeignKey(FeedSource, on_delete=models.CASCADE, related_name="items")
    external_id = models.CharField(max_length=300)
    title = models.CharField(max_length=300)
    summary = models.TextField(max_length=1500, blank=True)
    url = models.URLField(max_length=600, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "external_id"], name="unique_feed_item")
        ]
        ordering = ["-published_at", "-imported_at"]
        indexes = [models.Index(fields=["source", "-published_at"])]

    def __str__(self):
        return self.title


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    station = models.ForeignKey(Station, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=80)
    object_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["station", "-created_at"])]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Audit-Ereignisse duerfen nicht veraendert werden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit-Ereignisse duerfen nicht geloescht werden.")
