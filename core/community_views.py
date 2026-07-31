"""Registration, personal account area, and station chat."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .access import CONTENT_ROLES, get_membership, membership_required, station_module_required
from .forms import ChatMessageForm, ProfileForm, RegistrationForm
from .models import ChatMessage, Membership, RegistrationRequest
from .services import audit


def registration_enabled():
    return bool(getattr(settings, "REGISTRATION_ENABLED", True))


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "unknown")[:64]


def _registration_rate_limited(request):
    key = f"rwsth-register:{_client_ip(request)}"
    count = cache.get(key, 0)
    limit = int(getattr(settings, "REGISTRATION_RATE_LIMIT", 5) or 5)
    if count >= limit:
        return True
    cache.set(key, count + 1, timeout=3600)
    return False


@require_http_methods(["GET", "POST"])
def register(request):
    if not registration_enabled():
        raise Http404
    if request.user.is_authenticated:
        return redirect("landing")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if _registration_rate_limited(request):
            messages.error(request, "Zu viele Registrierungen von dieser Adresse. Bitte später erneut versuchen.")
            return render(request, "registration/register.html", {"form": form})
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
                first_name=form.cleaned_data.get("first_name") or "",
            )
            RegistrationRequest.objects.create(
                user=user,
                preferred_station=form.cleaned_data.get("preferred_station"),
                note=form.cleaned_data.get("note") or "",
            )
            audit(user, form.cleaned_data.get("preferred_station"), "registration.submitted", user, {
                "fields": ["username", "preferred_station"],
            })
        messages.success(
            request,
            "Konto angelegt. Nach der Anmeldung freigibt ein Administrator den Wachenzugang.",
        )
        return redirect("login")
    return render(request, "registration/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def account_home(request):
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('account_home')}")
    membership = get_membership(request.user)
    registration = RegistrationRequest.objects.filter(user=request.user).first()
    action = request.POST.get("action") if request.method == "POST" else None
    if action == "profile":
        profile_form = ProfileForm(request.POST, instance=request.user, prefix="profile")
        password_form = PasswordChangeForm(request.user, prefix="password")
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Profil wurde gespeichert.")
            return redirect("account_home")
    elif action == "password":
        profile_form = ProfileForm(instance=request.user, prefix="profile")
        password_form = PasswordChangeForm(request.user, request.POST, prefix="password")
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Passwort wurde geändert.")
            return redirect("account_home")
    else:
        profile_form = ProfileForm(instance=request.user, prefix="profile")
        password_form = PasswordChangeForm(request.user, prefix="password")
    return render(request, "core/account.html", {
        "profile_form": profile_form,
        "password_form": password_form,
        "membership": membership,
        "registration": registration,
    })


@membership_required(CONTENT_ROLES)
@station_module_required("chat_enabled")
@require_http_methods(["GET", "POST"])
def chat(request):
    station = request.membership.station
    form = ChatMessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = ChatMessage.objects.create(
            station=station,
            author=request.user,
            body=form.cleaned_data["body"].strip(),
        )
        audit(request.user, station, "chat.message_created", message, {
            "fields": ["body"],
        })
        messages.success(request, "Nachricht gesendet.")
        return redirect("chat")
    page = ChatMessage.objects.filter(station=station, is_hidden=False).select_related("author")[:80]
    # chronological for display
    thread = list(reversed(list(page)))
    return render(request, "core/chat.html", {
        "form": form,
        "thread": thread,
        "can_moderate": request.membership.role in {
            Membership.Role.SHIFT_LEAD,
            Membership.Role.ADMIN,
        },
    })


@membership_required({Membership.Role.SHIFT_LEAD, Membership.Role.ADMIN})
@station_module_required("chat_enabled")
@require_POST
def chat_hide(request, pk):
    message = get_object_or_404(ChatMessage, pk=pk, station=request.membership.station)
    if not message.is_hidden:
        message.is_hidden = True
        message.save(update_fields=["is_hidden"])
        audit(request.user, request.membership.station, "chat.message_hidden", message, {
            "fields": ["is_hidden"],
            "changes": {"is_hidden": {"from": False, "to": True}},
        })
        messages.success(request, "Nachricht wurde ausgeblendet.")
    return redirect("chat")


@membership_required({Membership.Role.ADMIN})
@require_POST
def registration_reject(request, pk):
    item = get_object_or_404(
        RegistrationRequest,
        pk=pk,
        status=RegistrationRequest.Status.PENDING,
    )
    item.status = RegistrationRequest.Status.REJECTED
    item.reviewed_at = timezone.now()
    item.reviewed_by = request.user
    item.save(update_fields=["status", "reviewed_at", "reviewed_by"])
    item.user.is_active = False
    item.user.save(update_fields=["is_active"])
    audit(request.user, request.membership.station, "registration.rejected", item.user, {
        "fields": ["status"],
    })
    messages.success(request, "Registrierung wurde abgelehnt.")
    return redirect("team")
