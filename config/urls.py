from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import healthz, offline, privacy_notice, service_worker, web_manifest


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("manifest.webmanifest", web_manifest, name="web_manifest"),
    path("service-worker.js", service_worker, name="service_worker"),
    path("offline/", offline, name="offline"),
    path("datenschutz/", privacy_notice, name="privacy"),
    path(
        "anmelden/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("abmelden/", auth_views.LogoutView.as_view(), name="logout"),
    path("django-admin/", admin.site.urls),
    path("", include("core.urls")),
]
