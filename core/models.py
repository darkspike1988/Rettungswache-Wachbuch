from datetime import date
from urllib.parse import urlparse
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Station(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    calendar_enabled = models.BooleanField(default=True, verbose_name="Kalender aktiviert")
    birthdays_enabled = models.BooleanField(default=True, verbose_name="Geburtstage aktiviert")
    coffee_enabled = models.BooleanField(default=True, verbose_name="Kaffeekasse aktiviert")
    feeds_enabled = models.BooleanField(default=False, verbose_name="Externe Meldungen aktiviert")
    tasks_enabled = models.BooleanField(default=True, verbose_name="Tagesaufgaben aktiviert")
    chat_enabled = models.BooleanField(default=True, verbose_name="Wachenchat aktiviert")
    holidays_enabled = models.BooleanField(default=True, verbose_name="Feiertage (NRW) im Kalender")
    checklists_enabled = models.BooleanField(default=False, verbose_name="Checklisten aktiviert")
    paypal_me_url = models.URLField(blank=True, default="", verbose_name="PayPal.me-Link")
    wero_link = models.URLField(blank=True, default="", verbose_name="Wero-Link")
    iban = models.CharField(max_length=34, blank=True, default="", verbose_name="IBAN")
    bic = models.CharField(max_length=12, blank=True, default="", verbose_name="BIC")
    payment_note = models.TextField(blank=True, default="", verbose_name="Zahlungshinweis")

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
        ADMIN = "admin", "Master-Admin"
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
        if self.day and self.month:
            try:
                # Schaltjahr, damit der 29. Februar zulaessig bleibt.
                date(2000, self.month, self.day)
            except ValueError as exc:
                raise ValidationError("Tag und Monat ergeben kein gueltiges Datum.") from exc


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


class StationTask(models.Model):
    """Wachaufgaben analog zur Wandtafel: gruen taeglich, gelb Wochentag, blau zusaetzlich."""

    class Band(models.TextChoices):
        DAILY = "daily", "Taeglich"
        WEEKDAY = "weekday", "Wochentag"
        EXTRA = "extra", "Zusaetzlich"

    WEEKDAY_LABELS = (
        (0, "Montag"),
        (1, "Dienstag"),
        (2, "Mittwoch"),
        (3, "Donnerstag"),
        (4, "Freitag"),
        (5, "Samstag"),
        (6, "Sonntag"),
    )

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="station_tasks")
    title = models.CharField(max_length=160)
    band = models.CharField(max_length=20, choices=Band.choices, default=Band.DAILY)
    weekday = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=WEEKDAY_LABELS,
        help_text="Nur fuer Wochentagsaufgaben noetig (0=Montag).",
    )
    notes = models.CharField(max_length=240, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["band", "weekday", "sort_order", "title"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(band="weekday") & Q(weekday__isnull=False))
                    | (~Q(band="weekday") & Q(weekday__isnull=True))
                ),
                name="station_task_weekday_matches_band",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.band == self.Band.WEEKDAY:
            if self.weekday is None or not 0 <= self.weekday <= 6:
                raise ValidationError({"weekday": "Wochentagsaufgaben brauchen einen Wochentag."})
        elif self.weekday is not None:
            raise ValidationError({"weekday": "Nur Wochentagsaufgaben duerfen einen Wochentag haben."})

    def applies_to_date(self, work_date):
        if not self.is_active:
            return False
        if self.band == self.Band.DAILY:
            return True
        if self.band == self.Band.WEEKDAY:
            return self.weekday == work_date.weekday()
        return True

    @property
    def band_css(self):
        return {
            self.Band.DAILY: "band-daily",
            self.Band.WEEKDAY: "band-weekday",
            self.Band.EXTRA: "band-extra",
        }.get(self.band, "band-extra")


class StationTaskCompletion(models.Model):
    task = models.ForeignKey(StationTask, on_delete=models.CASCADE, related_name="completions")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="task_completions")
    work_date = models.DateField()
    completed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="station_task_completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["-work_date", "-completed_at"]
        constraints = [
            models.UniqueConstraint(fields=["task", "work_date"], name="unique_task_completion_day"),
        ]

    def __str__(self):
        return f"{self.task_id} @ {self.work_date}"


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
    first_imported_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "external_id"], name="unique_feed_item")
        ]
        ordering = [F("published_at").desc(nulls_last=True), "-last_seen_at"]
        indexes = [models.Index(fields=["source", "-published_at"])]

    def __str__(self):
        return self.title


class TotpDevice(models.Model):
    """Optional TOTP second factor for a local account (RFC 6238)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="totp_device")
    secret = models.CharField(max_length=255)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        state = "aktiv" if self.is_confirmed else "unbestätigt"
        return f"TOTP {self.user_id} ({state})"


class WebAuthnCredential(models.Model):
    """Passkey / WebAuthn public-key credential for phishing-resistant login or MFA."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webauthn_credentials")
    credential_id = models.CharField(max_length=512, unique=True)
    public_key = models.TextField()
    sign_count = models.PositiveIntegerField(default=0)
    device_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.device_name or f"Passkey {self.pk}"


class PushSubscription(models.Model):
    """Browser Web-Push subscription for urgent station alerts."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_subscriptions")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=500)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["endpoint"], name="unique_push_endpoint"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Push {self.user_id}@{self.station_id}"


class PushOutbox(models.Model):
    """Transactional outbox row for Web-Push delivery.

    A request that creates an urgent handover writes one PushOutbox per
    subscription in the same DB transaction. A separate worker picks the
    rows, performs the external HTTP call, and updates the status. The
    Gunicorn request never opens a network connection to a push service.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        DISCARDED = "discarded", "Discarded"

    BACKOFF_SECONDS = (60, 300, 900, 3600, 21600)
    MAX_ATTEMPTS = 10
    RETENTION_DAYS = 30

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="push_outbox")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="push_outbox")
    # SET_NULL keeps the forensic outbox row when a subscription is purged.
    # The worker nulls the reference first so the cascade never fires.
    subscription = models.ForeignKey(
        PushSubscription, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="outbox_entries",
    )
    payload = models.JSONField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at"]),
            models.Index(fields=["station", "status"]),
        ]

    def __str__(self):
        return f"PushOutbox {self.id} ({self.status})"

    @property
    def next_backoff_seconds(self) -> int:
        """Return the wait time for the next attempt.

        ``attempts`` counts the deliveries that already failed. After the
        first failure we wait ``BACKOFF_SECONDS[0]`` (60s), after the second
        ``BACKOFF_SECONDS[1]`` (5 min), and so on. Beyond the defined
        schedule the last step is reused so ``MAX_ATTEMPTS`` still leaves
        room for a final retry.
        """
        idx = min(self.attempts, len(self.BACKOFF_SECONDS) - 1)
        return self.BACKOFF_SECONDS[idx]


class CalendarFeedToken(models.Model):
    """Read-only token for external calendar apps (webcal/ICS subscribe)."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="calendar_feed_tokens")
    token = models.CharField(max_length=64, unique=True)
    label = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="calendar_feed_tokens")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.label or f"Kalender-Abo {self.pk}"


class ApiToken(models.Model):
    """Revocable app token for /api/v1/ (Paperless/Nextcloud-style mobile clients)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    label = models.CharField(max_length=120)
    token_prefix = models.CharField(max_length=16)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.token_prefix}…)"


class RegistrationRequest(models.Model):
    """Optional self-service signup waiting for Master-Admin approval."""

    class Status(models.TextChoices):
        PENDING = "pending", "Wartend"
        APPROVED = "approved", "Freigegeben"
        REJECTED = "rejected", "Abgelehnt"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="registration_request")
    preferred_station = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registration_requests",
    )
    note = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_registrations",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Registrierung {self.user_id} ({self.status})"


class UserProfile(models.Model):
    """Personal extras for /konto/. Avatar bytes only – no general uploads."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    avatar = models.BinaryField(null=True, blank=True, editable=False)
    avatar_content_type = models.CharField(max_length=32, blank=True, default="")
    avatar_updated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profil {self.user_id}"

    @property
    def has_avatar(self):
        return bool(self.avatar)

    @classmethod
    def for_user(cls, user):
        profile, _ = cls.objects.get_or_create(user=user)
        return profile


class UserCryptoIdentity(models.Model):
    """Public identity + passphrase-wrapped private key for E2EE messaging."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="crypto")
    public_jwk = models.JSONField()
    wrapped_private_jwk = models.TextField()
    kdf_salt = models.CharField(max_length=128)
    kdf_iterations = models.PositiveIntegerField(default=210_000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Crypto {self.user_id}"


class ChatMessage(models.Model):
    """Station-scoped short colleague messages. Bodies are E2EE ciphertext when encrypted."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="chat_messages")
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="chat_messages")
    body = models.TextField(max_length=1000, blank=True, default="")
    ciphertext = models.TextField(blank=True, default="")
    nonce = models.CharField(max_length=64, blank=True, default="")
    key_wraps = models.JSONField(default=dict, blank=True)
    algo = models.CharField(max_length=40, blank=True, default="")
    is_encrypted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["station", "-created_at"])]

    def __str__(self):
        return f"Chat {self.pk}"


class PrivateConversation(models.Model):
    """1:1 private thread. Only the two participants can fetch ciphertext."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="private_conversations")
    user_low = models.ForeignKey(User, on_delete=models.CASCADE, related_name="private_conversations_low")
    user_high = models.ForeignKey(User, on_delete=models.CASCADE, related_name="private_conversations_high")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["station", "user_low", "user_high"],
                name="unique_private_conversation_pair",
            ),
            models.CheckConstraint(
                condition=~Q(user_low=F("user_high")),
                name="private_conversation_distinct_users",
            ),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Privat {self.pk}"

    def other_user(self, user):
        return self.user_high if user.id == self.user_low_id else self.user_low


class PrivateMessage(models.Model):
    conversation = models.ForeignKey(
        PrivateConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(User, on_delete=models.PROTECT, related_name="private_messages")
    ciphertext = models.TextField()
    nonce = models.CharField(max_length=64)
    key_wraps = models.JSONField(default=dict)
    algo = models.CharField(max_length=40, default="A256GCM+ECDH-ES")
    created_at = models.DateTimeField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["conversation", "-created_at"])]

    @property
    def is_encrypted(self):
        return True

    def __str__(self):
        return f"PrivateMessage {self.pk}"


class SecureMail(models.Model):
    """Encrypted internal mail. Only sender and recipients hold key wraps."""

    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="secure_mails")
    sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sent_secure_mails")
    ciphertext = models.TextField()
    nonce = models.CharField(max_length=64)
    key_wraps = models.JSONField(default=dict)
    algo = models.CharField(max_length=40, default="A256GCM+ECDH-ES")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["station", "-created_at"])]

    @property
    def is_encrypted(self):
        return True

    @property
    def author_id(self):
        return self.sender_id

    def __str__(self):
        return f"SecureMail {self.pk}"


class SecureMailRecipient(models.Model):
    mail = models.ForeignKey(SecureMail, on_delete=models.CASCADE, related_name="recipients")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_secure_mails")
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["mail", "user"], name="unique_secure_mail_recipient"),
        ]

    def __str__(self):
        return f"MailRecipient {self.mail_id}:{self.user_id}"


class Checklist(models.Model):
    """Wiederkehrende Prüfvorlage einer Wache (admin-gepflegt)."""

    station = models.ForeignKey(Station, on_delete=models.PROTECT, related_name="checklists")
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class ChecklistItem(models.Model):
    checklist = models.ForeignKey(Checklist, on_delete=models.CASCADE, related_name="items")
    text = models.CharField(max_length=200)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.text


class ChecklistCompletion(models.Model):
    """Append-only Abschluss einer Checkliste."""

    station = models.ForeignKey(
        Station, on_delete=models.PROTECT, related_name="checklist_completions"
    )
    checklist = models.ForeignKey(
        Checklist, on_delete=models.PROTECT, related_name="completions"
    )
    completed_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="checklist_completions"
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["station", "-created_at"])]

    def clean(self):
        super().clean()
        if self.checklist_id and self.station_id and self.checklist.station_id != self.station_id:
            raise ValidationError("Checkliste gehört nicht zu dieser Wache.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Checklisten-Abschlüsse dürfen nicht verändert werden.")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Checklisten-Abschlüsse dürfen nicht gelöscht werden.")


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
            raise ValidationError("Audit-Ereignisse dürfen nicht verändert werden.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit-Ereignisse dürfen nicht gelöscht werden.")


class RateLimit(models.Model):
    bucket = models.CharField(max_length=64)
    key_hash = models.CharField(max_length=64)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (("bucket", "key_hash", "window_start"),)
        indexes = [
            models.Index(fields=["bucket", "window_start"]),
        ]

    def __str__(self):
        return f"{self.bucket}:{self.key_hash}:{self.window_start.isoformat()}"
