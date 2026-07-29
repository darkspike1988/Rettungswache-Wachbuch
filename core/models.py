from urllib.parse import urlparse

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Station(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    calendar_enabled = models.BooleanField(default=True, verbose_name="Kalender aktiviert")
    birthdays_enabled = models.BooleanField(default=True, verbose_name="Geburtstage aktiviert")
    coffee_enabled = models.BooleanField(default=True, verbose_name="Kaffeekasse aktiviert")
    feeds_enabled = models.BooleanField(default=False, verbose_name="Externe Meldungen aktiviert")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

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
        constraints = [
            models.UniqueConstraint(fields=["user", "station"], name="unique_station_membership"),
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(is_active=True),
                name="unique_active_membership",
            ),
        ]
        ordering = ["station", "user_id"]

    def __str__(self):
        return f"{self.user} - {self.station} ({self.get_role_display()})"


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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["status", "-created_at"]
        indexes = [models.Index(fields=["station", "status", "-created_at"])]

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

    name = models.CharField(max_length=120, unique=True)
    url = models.URLField(max_length=600)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    locality = models.CharField(max_length=80)
    attribution = models.CharField(max_length=200)
    is_enabled = models.BooleanField(default=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["name"]

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
