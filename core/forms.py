from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import BirthdayPreference, CalendarEvent, HandoverEntry, Membership, Station, StationTask


class DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"


class HandoverForm(forms.ModelForm):
    class Meta:
        model = HandoverEntry
        fields = ["category", "priority", "title", "details"]
        widgets = {"details": forms.Textarea(attrs={"rows": 6})}


class HandoverEditForm(forms.ModelForm):
    class Meta:
        model = HandoverEntry
        fields = ["category", "priority", "title", "details"]
        widgets = {"details": forms.Textarea(attrs={"rows": 6})}
        labels = {
            "category": "Kategorie",
            "priority": "Priorität",
            "title": "Titel",
            "details": "Details",
        }


class HandoverStatusForm(forms.ModelForm):
    class Meta:
        model = HandoverEntry
        fields = ["status"]


class TotpConfirmForm(forms.Form):
    token = forms.CharField(
        max_length=8,
        label="Einmalcode",
        widget=forms.TextInput(attrs={
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "pattern": "[0-9]*",
        }),
    )


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
        day = cleaned.get("day")
        month = cleaned.get("month")
        if cleaned.get("consent") and (not day or not month):
            raise forms.ValidationError("Bitte Tag und Monat angeben oder die Anzeige deaktivieren.")
        if day and month:
            try:
                date(2000, month, day)
            except ValueError as exc:
                raise forms.ValidationError("Tag und Monat ergeben kein gültiges Datum.") from exc
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        was_visible = instance.is_visible
        instance.is_visible = self.cleaned_data["consent"]
        if instance.is_visible and not was_visible:
            instance.consented_at = timezone.now()
            instance.withdrawn_at = None
        if not instance.is_visible:
            if was_visible:
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
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Benutzerkonto")
    role = forms.ChoiceField(choices=Membership.Role.choices, label="Rolle")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True).exclude(
            station_memberships__is_active=True
        ).order_by("first_name", "username")


class MembershipEditForm(forms.Form):
    role = forms.ChoiceField(choices=Membership.Role.choices, label="Rolle")
    is_active = forms.BooleanField(required=False, label="Zugang aktiv")

    def __init__(self, *args, membership, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].initial = membership.role
        self.fields["is_active"].initial = membership.is_active


class StationSettingsForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = [
            "name",
            "calendar_enabled",
            "birthdays_enabled",
            "coffee_enabled",
            "feeds_enabled",
            "tasks_enabled",
            "chat_enabled",
        ]
        labels = {"name": "Name der Rettungswache"}


class RegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, label="Benutzername (z. B. E-Mail)")
    first_name = forms.CharField(max_length=150, label="Vorname", required=False)
    preferred_station = forms.ModelChoiceField(
        queryset=Station.objects.none(),
        required=False,
        label="Gewünschte Wache",
        empty_label="Noch offen / bitte zuordnen",
    )
    note = forms.CharField(
        max_length=300,
        required=False,
        label="Hinweis an die Verwaltung",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    password1 = forms.CharField(label="Passwort", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Passwort wiederholen", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_station"].queryset = Station.objects.filter(
            is_active=True
        ).order_by("name")

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Dieser Benutzername ist bereits vergeben.")
        return username

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Die Passwörter stimmen nicht überein.")
        if password1:
            from django.contrib.auth.password_validation import validate_password

            validate_password(password1)
        return cleaned


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        labels = {
            "first_name": "Vorname",
            "last_name": "Nachname",
            "email": "E-Mail",
        }


class ChatMessageForm(forms.Form):
    body = forms.CharField(
        max_length=1000,
        label="Nachricht",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Kurzer Hinweis für die Wache …"}),
    )


class StationTaskForm(forms.ModelForm):
    class Meta:
        model = StationTask
        fields = ["title", "band", "weekday", "notes", "sort_order", "is_active"]
        labels = {
            "title": "Aufgabe",
            "band": "Farbe / Bereich",
            "weekday": "Wochentag",
            "notes": "Hinweis",
            "sort_order": "Reihenfolge",
            "is_active": "Aktiv",
        }
        help_texts = {
            "band": "Grün = täglich, Gelb = Wochentag, Blau = zusätzlich.",
            "weekday": "Nur bei gelben Wochentagsaufgaben setzen.",
        }

    def clean(self):
        cleaned = super().clean()
        band = cleaned.get("band")
        weekday = cleaned.get("weekday")
        if band == StationTask.Band.WEEKDAY and weekday is None:
            self.add_error("weekday", "Bitte einen Wochentag wählen.")
        if band != StationTask.Band.WEEKDAY:
            cleaned["weekday"] = None
        return cleaned
