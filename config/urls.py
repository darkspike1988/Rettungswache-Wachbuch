from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.auth_views import PasswordLoginView
from core.views import (
    healthz,
    mfa_disable,
    mfa_setup,
    mfa_verify,
    offline,
    privacy_notice,
    service_worker,
    web_manifest,
)


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("manifest.webmanifest", web_manifest, name="web_manifest"),
    path("service-worker.js", service_worker, name="service_worker"),
    path("offline/", offline, name="offline"),
    path("datenschutz/", privacy_notice, name="privacy"),
    path("anmelden/", PasswordLoginView.as_view(), name="login"),
    path("anmelden/mfa/", mfa_verify, name="mfa_verify"),
    path("konto/mfa/", mfa_setup, name="mfa_setup"),
    path("konto/mfa/deaktivieren/", mfa_disable, name="mfa_disable"),
    path("abmelden/", auth_views.LogoutView.as_view(), name="logout"),
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
]
