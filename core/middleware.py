from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.models import User

from .models import Membership, Station


class TailscaleAuthMiddleware:
    """Use identity headers injected by the loopback-only Tailscale proxy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.TRUST_TAILSCALE_HEADERS:
            login_name = request.META.get("HTTP_TAILSCALE_USER_LOGIN", "").strip().lower()
            display_name = request.META.get("HTTP_TAILSCALE_USER_NAME", "").strip()
            if not login_name:
                if request.user.is_authenticated:
                    logout(request)
                return self.get_response(request)
            if request.user.is_authenticated and request.user.username != login_name:
                logout(request)
            if not request.user.is_authenticated:
                user, _ = User.objects.get_or_create(
                    username=login_name,
                    defaults={"email": login_name, "first_name": display_name[:150]},
                )
                if not user.is_active:
                    return self.get_response(request)
                if display_name and user.first_name != display_name[:150]:
                    user.first_name = display_name[:150]
                    user.save(update_fields=["first_name"])
                if login_name == settings.TAILSCALE_ADMIN_LOGIN:
                    self._ensure_admin(user)
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return self.get_response(request)

    @staticmethod
    def _ensure_admin(user):
        membership = user.station_memberships.filter(is_active=True).select_related(
            "station"
        ).first()
        if membership:
            station = membership.station
        else:
            station = Station.get_default()
        Membership.objects.update_or_create(
            user=user,
            station=station,
            defaults={"role": Membership.Role.ADMIN, "is_active": True},
        )


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        return response
