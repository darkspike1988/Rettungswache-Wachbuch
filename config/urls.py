from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import account_views, community_views, secure_views
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
    path("registrieren/", community_views.register, name="register"),
    path("konto/", community_views.account_home, name="account_home"),
    path("konto/avatar/<int:user_id>/", community_views.avatar_image, name="avatar_image"),
    path("konto/crypto/", secure_views.crypto_setup, name="crypto_setup"),
    path("konto/crypto/bundle.json", secure_views.crypto_bundle, name="crypto_bundle"),
    path("anmelden/mfa/", mfa_verify, name="mfa_verify"),
    path("anmelden/passkey/optionen/", account_views.passkey_login_options, name="passkey_login_options"),
    path("anmelden/passkey/pruefen/", account_views.passkey_login_verify, name="passkey_login_verify"),
    path("anmelden/mfa/passkey/optionen/", account_views.passkey_mfa_options, name="passkey_mfa_options"),
    path("anmelden/mfa/passkey/pruefen/", account_views.passkey_mfa_verify, name="passkey_mfa_verify"),
    path("konto/mfa/", mfa_setup, name="mfa_setup"),
    path("konto/mfa/deaktivieren/", mfa_disable, name="mfa_disable"),
    path("konto/mfa/passkey/optionen/", account_views.passkey_register_options, name="passkey_register_options"),
    path("konto/mfa/passkey/pruefen/", account_views.passkey_register_verify, name="passkey_register_verify"),
    path("konto/mfa/passkey/<int:pk>/entfernen/", account_views.passkey_delete, name="passkey_delete"),
    path("konto/api/", account_views.api_tokens_manage, name="api_tokens_manage"),
    path("abmelden/", auth_views.LogoutView.as_view(), name="logout"),
    path("django-admin/", admin.site.urls),
    path("api/v1/", include("core.api.urls")),
    path("", include("core.urls")),
]
