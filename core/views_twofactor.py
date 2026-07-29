"""Anmeldung mit zweitem Faktor und dessen Verwaltung."""

from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .services import audit
from .throttle import exceeds_limit
from .twofactor import (
    device_for,
    is_enabled,
    issue_recovery_codes,
    manual_entry_key,
    new_secret,
    provisioning_uri,
    qr_svg,
    verify_code,
    verify_recovery_code,
)
from .models import TotpDevice

PENDING_USER_KEY = "totp_pending_user"
PENDING_SINCE_KEY = "totp_pending_since"
PENDING_MAX_AGE = timedelta(minutes=5)
SETUP_SECRET_KEY = "totp_setup_secret"


class CodeForm(forms.Form):
    code = forms.CharField(label="Code aus der App", max_length=32)


class LoginCodeForm(forms.Form):
    code = forms.CharField(
        label="Code aus der App oder Wiederherstellungscode", max_length=32,
    )


def _station_of(user):
    membership = user.station_memberships.select_related("station").filter(
        is_active=True
    ).first()
    return membership.station if membership else None


class TwoFactorLoginView(auth_views.LoginView):
    """Passwort geprueft, aber noch keine Sitzung: wer einen zweiten Faktor
    eingerichtet hat, muss erst den Code bestaetigen."""

    def form_valid(self, form):
        user = form.get_user()
        if not is_enabled(user):
            return super().form_valid(form)
        self.request.session[PENDING_USER_KEY] = user.pk
        self.request.session[PENDING_SINCE_KEY] = timezone.now().isoformat()
        return redirect("login_totp")


def _pending_user(request):
    user_id = request.session.get(PENDING_USER_KEY)
    started = request.session.get(PENDING_SINCE_KEY)
    if not user_id or not started:
        return None
    try:
        began = timezone.datetime.fromisoformat(started)
    except ValueError:
        return None
    if timezone.now() - began > PENDING_MAX_AGE:
        return None
    return User.objects.filter(pk=user_id, is_active=True).first()


def _clear_pending(request):
    request.session.pop(PENDING_USER_KEY, None)
    request.session.pop(PENDING_SINCE_KEY, None)


@require_http_methods(["GET", "POST"])
def login_totp(request):
    user = _pending_user(request)
    if user is None:
        _clear_pending(request)
        messages.error(request, "Die Anmeldung ist abgelaufen. Bitte erneut anmelden.")
        return redirect("login")

    device = device_for(user)
    if device is None:
        # Zweiter Faktor wurde zwischenzeitlich entfernt.
        _clear_pending(request)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("access")

    form = LoginCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if exceeds_limit("totp-login", str(user.pk), 10, 900):
            messages.error(request, "Zu viele Versuche. Bitte spaeter erneut anmelden.")
            _clear_pending(request)
            return redirect("login")
        value = form.cleaned_data["code"]
        if verify_code(device, value):
            _clear_pending(request)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("access")
        if verify_recovery_code(device, value):
            _clear_pending(request)
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            audit(user, _station_of(user), "twofactor.recovery_code_used", device, {})
            messages.warning(
                request,
                "Wiederherstellungscode verwendet. Er ist jetzt verbraucht - "
                "richte bei Gelegenheit neue Codes ein.",
            )
            return redirect("access")
        messages.error(request, "Der Code stimmt nicht.")

    return render(request, "registration/login_totp.html", {"form": form})


@login_required
def twofactor_status(request):
    return render(request, "core/twofactor_status.html", {
        "enabled": is_enabled(request.user),
        "unused_codes": (
            device_for(request.user).recovery_codes.filter(used_at__isnull=True).count()
            if is_enabled(request.user) else 0
        ),
    })


@login_required
@require_http_methods(["GET", "POST"])
def twofactor_setup(request):
    if is_enabled(request.user):
        return redirect("twofactor_status")

    secret = request.session.get(SETUP_SECRET_KEY)
    if not secret:
        secret = new_secret()
        request.session[SETUP_SECRET_KEY] = secret

    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        device = TotpDevice(user=request.user, secret=secret)
        if verify_code(device, form.cleaned_data["code"]):
            with transaction.atomic():
                TotpDevice.objects.filter(user=request.user).delete()
                device.confirmed = True
                device.confirmed_at = timezone.now()
                device.save()
                codes = issue_recovery_codes(device)
                audit(
                    request.user, _station_of(request.user), "twofactor.enabled", device, {},
                )
            request.session.pop(SETUP_SECRET_KEY, None)
            request.session["totp_fresh_codes"] = codes
            return redirect("twofactor_codes")
        form.add_error("code", "Der Code stimmt nicht. Stimmt die Uhrzeit des Geraets?")

    uri = provisioning_uri(request.user, secret)
    return render(request, "core/twofactor_setup.html", {
        "form": form,
        "qr_svg": qr_svg(uri),
        "manual_key": manual_entry_key(secret),
    })


@login_required
def twofactor_codes(request):
    """Zeigt frisch erzeugte Codes genau einmal an."""
    codes = request.session.pop("totp_fresh_codes", None)
    if not codes:
        return redirect("twofactor_status")
    return render(request, "core/twofactor_codes.html", {"codes": codes})


@login_required
@require_http_methods(["GET", "POST"])
def twofactor_regenerate(request):
    device = device_for(request.user)
    if device is None:
        return redirect("twofactor_status")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if verify_code(device, form.cleaned_data["code"]):
            codes = issue_recovery_codes(device)
            audit(
                request.user, _station_of(request.user),
                "twofactor.recovery_codes_reissued", device, {},
            )
            request.session["totp_fresh_codes"] = codes
            return redirect("twofactor_codes")
        form.add_error("code", "Der Code stimmt nicht.")
    return render(request, "core/twofactor_regenerate.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def twofactor_disable(request):
    device = device_for(request.user)
    if device is None:
        return redirect("twofactor_status")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if verify_code(device, form.cleaned_data["code"]):
            audit(
                request.user, _station_of(request.user), "twofactor.disabled", device, {},
            )
            device.delete()
            messages.success(request, "Zwei-Faktor-Anmeldung ist deaktiviert.")
            return redirect("twofactor_status")
        form.add_error("code", "Der Code stimmt nicht.")
    return render(request, "core/twofactor_disable.html", {"form": form})
