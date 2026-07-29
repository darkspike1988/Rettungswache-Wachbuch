from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    BirthdayPreference,
    CalendarEvent,
    DailyTeamNote,
    FeedSource,
    HandoverEntry,
    Membership,
    Station,
)


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
            "location",
            "street",
            "postal_code",
            "city",
            "district",
            "calendar_enabled",
            "birthdays_enabled",
            "coffee_enabled",
            "feeds_enabled",
        ]
        labels = {
            "name": "Name der Rettungswache",
            "location": "Standort (Anzeige im Kopfbereich)",
            "street": "Strasse und Hausnummer",
            "postal_code": "PLZ",
            "city": "Ort",
            "district": "Kreis/Landkreis",
        }


class WasteSourceForm(forms.ModelForm):
    class Meta:
        model = FeedSource
        fields = ["url"]
        labels = {"url": "ICS-Abo-Link des Abfallkalenders"}
