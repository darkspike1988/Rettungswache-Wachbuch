from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from .models import (
    BirthdayPreference,
    CalendarEvent,
    DailyTeamNote,
    FeedSource,
    HandoverEntry,
    Membership,
    Shift,
    Station,
    TaskItem,
    TaskList,
    validate_iban,
)


class EmailRequiredMixin:
    """Ohne hinterlegte E-Mail-Adresse kann sich niemand das Passwort selbst
    zuruecksetzen, deshalb ist die Adresse bei jedem Konto Pflicht."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True


class WachbuchUserCreationForm(EmailRequiredMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class WachbuchUserChangeForm(EmailRequiredMixin, UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


class WachbuchPasswordResetForm(PasswordResetForm):
    """Konten werden hier ueblicherweise mit der E-Mail-Adresse als Benutzername
    angelegt. Damit der Reset auch dann funktioniert, wenn das E-Mail-Feld leer
    geblieben ist, wird zusaetzlich der Benutzername geprueft."""

    def get_users(self, email):
        matches = User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email), is_active=True,
        )
        for user in matches:
            if not user.has_usable_password():
                continue
            target = user.email or (user.username if "@" in user.username else "")
            if not target:
                continue
            # Nur fuer den Versand dieser Nachricht, wird nicht gespeichert.
            user.email = target
            yield user


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"


class DateInput(forms.DateInput):
    input_type = "date"


class HandoverForm(forms.ModelForm):
    class Meta:
        model = HandoverEntry
        fields = ["category", "priority", "title", "details", "for_date"]
        widgets = {
            "details": forms.Textarea(attrs={"rows": 6}),
            "for_date": DateInput(),
        }
        labels = {"for_date": "Betrifft Tag"}


class DailyTeamForm(forms.ModelForm):
    class Meta:
        model = DailyTeamNote
        fields = ["note"]
        labels = {"note": "Team"}


class HandoverStatusForm(forms.ModelForm):
    class Meta:
        model = HandoverEntry
        fields = ["status"]


class CalendarEventForm(forms.ModelForm):
    class Meta:
        model = CalendarEvent
        fields = ["title", "description", "starts_at", "ends_at"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "starts_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
            "ends_at": DateTimeLocalInput(format="%Y-%m-%dT%H:%M"),
        }


class BirthdayForm(forms.ModelForm):
    consent = forms.BooleanField(
        required=False,
        label="Ich möchte meinen Geburtstag freiwillig im Team anzeigen.",
    )

    class Meta:
        model = BirthdayPreference
        fields = ["day", "month"]
        labels = {"day": "Tag", "month": "Monat"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["day"].widget.attrs.update({"min": 1, "max": 31})
        self.fields["month"].widget.attrs.update({"min": 1, "max": 12})
        self.fields["consent"].initial = self.instance.is_visible

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("consent") and (not cleaned.get("day") or not cleaned.get("month")):
            raise forms.ValidationError("Bitte Tag und Monat angeben oder die Anzeige deaktivieren.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        was_visible = instance.is_visible
        instance.is_visible = self.cleaned_data["consent"]
        if instance.is_visible and not was_visible:
            instance.consented_at = timezone.now()
            instance.withdrawn_at = None
        if not instance.is_visible and was_visible:
            instance.withdrawn_at = timezone.now()
            instance.day = None
            instance.month = None
            instance.consented_at = None
        if commit:
            instance.save()
        return instance


class CoffeeEntryForm(forms.Form):
    member = forms.ModelChoiceField(queryset=User.objects.none(), label="Teammitglied")
    direction = forms.ChoiceField(
        choices=(("credit", "Einzahlung/Gutschrift"), ("debit", "Entnahme/Verbrauch")),
        label="Buchungsart",
    )
    amount_eur = forms.DecimalField(
        min_value=Decimal("0.01"), max_digits=8, decimal_places=2, label="Betrag in EUR"
    )
    reason = forms.CharField(max_length=200, label="Grund")

    def __init__(self, *args, station, **kwargs):
        super().__init__(*args, **kwargs)
        member_ids = Membership.objects.filter(station=station, is_active=True).values("user_id")
        self.fields["member"].queryset = User.objects.filter(id__in=member_ids).order_by(
            "first_name", "username"
        )

    def amount_cents(self):
        cents = int((self.cleaned_data["amount_eur"] * 100).quantize(Decimal("1"), ROUND_HALF_UP))
        return cents if self.cleaned_data["direction"] == "credit" else -cents


class CoffeeCorrectionForm(forms.Form):
    reason = forms.CharField(max_length=200, label="Korrekturgrund")


class MembershipAssignmentForm(forms.Form):
    """Zugang wird ueber die genaue Adresse freigegeben statt ueber eine Liste
    aller Konten - sonst saehe jede Wache die Konten aller anderen."""

    email = forms.EmailField(label="E-Mail-Adresse des Kontos")
    role = forms.ChoiceField(choices=Membership.Role.choices, label="Rolle")

    def __init__(self, *args, station, **kwargs):
        super().__init__(*args, **kwargs)
        self.station = station

    def clean_email(self):
        address = self.cleaned_data["email"].strip()
        user = User.objects.filter(
            Q(email__iexact=address) | Q(username__iexact=address), is_active=True,
        ).first()
        if user is None:
            raise forms.ValidationError(
                "Zu dieser Adresse gibt es kein aktives Konto. Es muss zuerst "
                "in der technischen Verwaltung angelegt werden."
            )
        if Membership.objects.filter(user=user, station=self.station).exists():
            raise forms.ValidationError("Diese Person ist dieser Wache bereits zugeordnet.")
        self.user = user
        return address


class MembershipEditForm(forms.Form):
    role = forms.ChoiceField(choices=Membership.Role.choices, label="Rolle")
    is_active = forms.BooleanField(required=False, label="Zugang aktiv")

    def __init__(self, *args, membership, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].initial = membership.role
        self.fields["is_active"].initial = membership.is_active


def _retention_field(label):
    return forms.IntegerField(
        required=False, min_value=0, label=label,
        help_text="0 oder leer = keine automatische Loeschung.",
    )


class StationSettingsForm(forms.ModelForm):
    retention_handover_days = _retention_field("Erledigte Uebergaben loeschen nach (Tagen)")
    retention_calendar_days = _retention_field("Vergangene Termine loeschen nach (Tagen)")
    retention_audit_days = _retention_field("Audit-Ereignisse loeschen nach (Tagen)")
    retention_task_days = _retention_field("Erledigte Aufgaben loeschen nach (Tagen)")

    def clean_retention_task_days(self):
        return self.cleaned_data.get("retention_task_days") or 0

    def clean_retention_handover_days(self):
        return self.cleaned_data.get("retention_handover_days") or 0

    def clean_retention_calendar_days(self):
        return self.cleaned_data.get("retention_calendar_days") or 0

    def clean_retention_audit_days(self):
        return self.cleaned_data.get("retention_audit_days") or 0

    class Meta:
        model = Station
        fields = [
            "name",
            "location",
            "street",
            "postal_code",
            "city",
            "district",
            "day_start_time",
            "task_attribution",
            "calendar_enabled",
            "birthdays_enabled",
            "coffee_enabled",
            "tasks_enabled",
            "feeds_enabled",
            "retention_handover_days",
            "retention_calendar_days",
            "retention_audit_days",
            "retention_task_days",
        ]
        labels = {
            "name": "Name der Rettungswache",
            "location": "Standort (Anzeige im Kopfbereich)",
            "street": "Strasse und Hausnummer",
            "postal_code": "PLZ",
            "city": "Ort",
            "district": "Kreis/Landkreis",
        }
        widgets = {"day_start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}


class SetupBasicsForm(forms.ModelForm):
    class Meta:
        model = Station
        # Der Betriebstag steht bewusst schon hier und nicht erst in den
        # Einstellungen: er bestimmt, auf welchem Tag ein Haken um 02:00 Uhr
        # landet. Wer ihn nie sieht, merkt den Fehler erst Monate spaeter.
        fields = ["name", "location", "day_start_time"]
        labels = {
            "name": "Name der Rettungswache",
            "location": "Standort (Anzeige im Kopfbereich unter dem Namen)",
        }
        widgets = {"day_start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}


class SetupModulesForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = [
            "calendar_enabled", "birthdays_enabled", "coffee_enabled",
            "tasks_enabled", "feeds_enabled",
        ]


DEFAULT_DAILY_TASKS = """Wachenrundgang
Fahrzeugcheck
Müll und Wäsche
Kaffeemaschine reinigen"""


class SetupTasksForm(forms.Form):
    """Der schnellste Weg vom Papierbogen in die Anwendung: die vorhandenen
    Punkte einmal untereinander eintippen. Feinheiten wie Rhythmus und
    Reihenfolge kommen danach im Wachenbereich dazu."""

    titles = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 8}),
        label="Eine Aufgabe je Zeile",
        help_text="Leer lassen, wenn ihr das später machen wollt.",
        initial=DEFAULT_DAILY_TASKS,
    )

    def clean_titles(self):
        lines = [line.strip() for line in self.cleaned_data["titles"].splitlines()]
        titles = [line[:160] for line in lines if line]
        if len(titles) > 40:
            raise forms.ValidationError("Bitte höchstens 40 Aufgaben auf einmal anlegen.")
        return titles


class WasteSourceForm(forms.ModelForm):
    class Meta:
        model = FeedSource
        fields = ["url"]
        labels = {"url": "ICS-Abo-Link des Abfallkalenders"}


WEEKDAY_CHOICES = [
    ("1", "Montag"), ("2", "Dienstag"), ("3", "Mittwoch"), ("4", "Donnerstag"),
    ("5", "Freitag"), ("6", "Samstag"), ("7", "Sonntag"),
]


class ShiftForm(forms.ModelForm):
    """Die Schichten einer Wache. Vorgegeben wird nichts - im Rettungsdienst
    laufen 24-Stunden-Dienste neben 12-Stunden-Wechseln und Tagesstandorten."""

    PRESETS = [
        ("24-Stunden-Dienst", "07:00", 1440),
        ("Tagdienst", "07:00", 720),
        ("Nachtdienst", "19:00", 720),
    ]

    class Meta:
        model = Shift
        fields = ["name", "start_time", "duration_minutes"]
        labels = {"name": "Bezeichnung"}
        help_texts = {
            "name": "Zum Beispiel „24-Stunden-Dienst“, „Tagdienst“ oder „Nachtdienst“.",
        }
        widgets = {"start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M")}

    def __init__(self, *args, station=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.station = station
        self.fields["duration_minutes"].widget.attrs.update({"min": 1, "max": 1440})

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        existing = Shift.objects.filter(station=self.station, name__iexact=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Eine Schicht mit dieser Bezeichnung gibt es schon.")
        return name


class TaskListForm(forms.ModelForm):
    """Wochentage sind Ankreuzfelder, im Modell stehen sie als Ziffernkette.
    Der Umbau passiert hier, damit im Formular nichts zu tippen ist."""

    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="An diesen Wochentagen",
        initial=[value for value, _ in WEEKDAY_CHOICES],
    )

    class Meta:
        model = TaskList
        fields = ["title", "rhythm", "weekdays", "day_of_month", "shift"]
        help_texts = {
            "title": "Zum Beispiel „Tagesaufgaben“, „Fahrzeugcheck RTW 1“ oder „Wachenrundgang“.",
        }

    def __init__(self, *args, station=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["day_of_month"].widget.attrs.update({"min": 1, "max": 31})
        # Nur die Schichten der eigenen Wache, und nur solange es welche gibt:
        # eine Wache mit einer Besetzung je Tag soll das Feld nicht sehen.
        shifts = Shift.objects.filter(station=station, is_active=True) if station else Shift.objects.none()
        if shifts.exists():
            self.fields["shift"].queryset = shifts
            self.fields["shift"].empty_label = "Einmal je Wachentag"
        else:
            del self.fields["shift"]
        if self.instance.pk:
            # Muss in self.initial stehen, nicht am Feld: der Modellwert ist
            # eine Zeichenkette und wuerde sonst als *ein* Wert gelesen, sodass
            # kein einziges Haekchen gesetzt waere.
            self.initial["weekdays"] = list(self.instance.weekdays)

    def clean_weekdays(self):
        return "".join(sorted(self.cleaned_data["weekdays"]))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("rhythm") == TaskList.Rhythm.MONTHLY:
            # Wochentage sind bei monatlichen Listen bedeutungslos, duerfen aber
            # nicht leer in die Datenbank - sonst schlaegt die Modellpruefung zu.
            cleaned["weekdays"] = cleaned.get("weekdays") or "1234567"
        elif not cleaned.get("weekdays"):
            self.add_error("weekdays", "Bitte mindestens einen Wochentag auswählen.")
        return cleaned


class TaskItemForm(forms.ModelForm):
    class Meta:
        model = TaskItem
        fields = ["title", "note"]


class TaskDefectForm(forms.Form):
    note = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Was fehlt oder ist defekt?",
        help_text="Landet wörtlich in der Übergabe. Keine Patienten- oder Einsatzdaten.",
    )


class CoffeePaymentForm(forms.ModelForm):
    # Etwas laenger als das Modellfeld, damit gruppierte Eingaben wie
    # "DE89 3704 ..." erst nach dem Entfernen der Leerzeichen gemessen werden.
    coffee_iban = forms.CharField(max_length=42, required=False, label="IBAN")

    class Meta:
        model = Station
        fields = ["coffee_paypal_link", "coffee_wero_link", "coffee_iban", "coffee_account_holder"]
        labels = {
            "coffee_paypal_link": "PayPal.me-Link",
            "coffee_wero_link": "Wero-Zahlungslink oder -Kontakt",
            "coffee_account_holder": "Kontoinhaber/in",
        }

    def clean_coffee_iban(self):
        value = self.cleaned_data["coffee_iban"].replace(" ", "").upper()
        validate_iban(value)
        return value
