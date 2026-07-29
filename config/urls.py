from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.views import healthz


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
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
