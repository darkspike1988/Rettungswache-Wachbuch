from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forms import InitialSetupForm, SetupAuthorizationForm
from .models import Membership, Station
from .services import audit
from .setup import (
    SETUP_SESSION_KEY,
    installation_complete,
    setup_token_is_secure,
    setup_token_matches,
)
from .task_board import ensure_default_station_tasks


@never_cache
@require_http_methods(["GET", "POST"])
def initial_setup(request):
    if not getattr(settings, "SETUP_WIZARD_ENABLED", True):
        raise Http404
    if installation_complete():
        return redirect("login")

    token_from_url = request.GET.get("token", "")
    if token_from_url and setup_token_matches(token_from_url):
        request.session[SETUP_SESSION_KEY] = True
        return redirect("initial_setup")

    authorized = bool(request.session.get(SETUP_SESSION_KEY))
    authorization_form = SetupAuthorizationForm()
    if (
        not authorized
        and request.method == "POST"
        and request.POST.get("action") == "authorize"
    ):
        authorization_form = SetupAuthorizationForm(request.POST)
        if authorization_form.is_valid() and setup_token_matches(
            authorization_form.cleaned_data["setup_token"]
        ):
            request.session[SETUP_SESSION_KEY] = True
            return redirect("initial_setup")
        authorization_form.add_error("setup_token", "Einrichtungs-Code ist ungültig.")

    setup_form = InitialSetupForm()
    if (
        authorized
        and request.method == "POST"
        and request.POST.get("action") == "configure"
    ):
        setup_form = InitialSetupForm(request.POST)
        if setup_form.is_valid():
            with transaction.atomic():
                station = Station.get_default()
                Station.objects.select_for_update().get(pk=station.pk)
                if installation_complete():
                    messages.error(
                        request, "Die Einrichtung wurde bereits abgeschlossen."
                    )
                    return redirect("login")
                station.name = setup_form.cleaned_data["station_name"]
                for field in (
                    "calendar_enabled",
                    "tasks_enabled",
                    "chat_enabled",
                    "coffee_enabled",
                    "birthdays_enabled",
                ):
                    setattr(station, field, setup_form.cleaned_data[field])
                station.save(
                    update_fields=[
                        "name",
                        "calendar_enabled",
                        "tasks_enabled",
                        "chat_enabled",
                        "coffee_enabled",
                        "birthdays_enabled",
                    ]
                )
                user = User.objects.create_user(
                    username=setup_form.cleaned_data["username"],
                    email=setup_form.cleaned_data["email"],
                    password=setup_form.cleaned_data["password1"],
                    first_name=setup_form.cleaned_data["first_name"],
                    last_name=setup_form.cleaned_data["last_name"],
                )
                Membership.objects.create(
                    user=user,
                    station=station,
                    role=Membership.Role.ADMIN,
                    is_active=True,
                )
                ensure_default_station_tasks(station)
                audit(
                    user,
                    station,
                    "installation.setup_completed",
                    station,
                    {
                        "fields": ["name", "modules", "master_admin"],
                        "setup_wizard": True,
                    },
                )
            request.session.pop(SETUP_SESSION_KEY, None)
            request.session["rwsth_setup_just_completed"] = True
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("setup_complete")

    return render(
        request,
        "core/initial_setup.html",
        {
            "authorized": authorized,
            "authorization_form": authorization_form,
            "setup_form": setup_form,
            "setup_token_ready": setup_token_is_secure(),
        },
    )


@never_cache
def setup_complete(request):
    if not request.user.is_authenticated or not request.session.pop(
        "rwsth_setup_just_completed", False
    ):
        return redirect("landing")
    return render(
        request,
        "core/setup_complete.html",
        {
            "mfa_setup_url": reverse("mfa_setup"),
        },
    )
