"""Middleware-Schicht fuer das Wachbuch.

Sammelt nur technische, nicht personenbezogene Daten (Pfad, Methode,
Korrelations-ID). Request-Bodies, Formularfelder und Auth-Header werden
nicht geloggt.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .errors import (
    REQUEST_ATTR_CORRELATION_ID,
    RESPONSE_CORRELATION_HEADER,
    correlation_id_for_request,
    log_exception,
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Scheme-relative redirects such as //example.org are interpreted as
        # external destinations by browsers. The Wachbuch has no intentional
        # cross-origin redirects, so fail closed to the local root.
        location = response.headers.get("Location")
        if location and location.startswith("//"):
            response.headers["Location"] = "/"

        # Content Security Policy - strenge Richtlinie
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "  # Inline für Django Templates
            "style-src 'self' 'unsafe-inline'; "  # Inline für Django Templates
            "img-src 'self' data: https:; "  # Daten-URIs + HTTPS für externe Bilder
            "font-src 'self'; "
            "connect-src 'self' https:; "  # HTTPS für API, WebSockets, etc.
            "frame-ancestors 'none'; "  # Kein Embedding in iframes
            "base-uri 'self'; "  # Keine externen base-URLs
            "form-action 'self'; "  # Formulare nur an eigene Domain
            "object-src 'none'; "  # Keine Plugins (Flash, Java, etc.)
            "upgrade-insecure-requests; "  # HTTP → HTTPS Upgrade
            "block-all-mixed-content; "  # Kein Mixed Content
            "require-sri-for 'script' 'style'"  # SRI für externe Ressourcen
        )
        
        # Permissions Policy - restriktiv
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "ambient-light-sensor=(), "
            "autoplay=(), "
            "battery=(), "
            "camera=(), "
            "display-capture=(), "
            "document-domain=(), "
            "encrypted-media=(), "
            "fullscreen=(self), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "midi=(), "
            "payment=(), "
            "picture-in-picture=(), "
            "publickey-credentials-get=(self), "
            "publickey-credentials-create=(self), "
            "screen-wake-lock=(), "
            "sync-xhr=(), "
            "usb=(), "
            "vr=(), "
            "xr-spatial-tracking=()"
        )
        
        # Weitere Sicherheitsheader
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        
        # HSTS (nur bei HTTPS)
        if request.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


class CorrelationIdMiddleware:
    """Stellt pro Request eine Korrelations-ID bereit.

    * Uebernimmt eine gueltige ``X-Correlation-ID`` aus dem Request (Pattern
      ``[A-Za-z0-9_-]{1,128}``), erzeugt sonst eine frische UUID4.
    * Legt die ID auf ``request.correlation_id`` ab.
    * Setzt sie als ``X-Correlation-ID`` in jede Antwort.
    * Schreibt sie als ``correlation_id`` Log-``extra`` fuer strukturierte Logs.
    """

    HEADER = RESPONSE_CORRELATION_HEADER

    def __init__(self, get_response):
        self.get_response = get_response
        self._logger = logging.getLogger("wachbuch.requests")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = correlation_id_for_request(request)
        setattr(request, REQUEST_ATTR_CORRELATION_ID, correlation_id)
        self._logger.info(
            "request_started method=%s path=%s correlation_id=%s",
            request.method or "",
            request.path or "",
            correlation_id,
            extra={"correlation_id": correlation_id},
        )
        try:
            response = self.get_response(request)
        except Exception:
            log_exception(request, message="request_failed")
            raise
        response[self.HEADER] = correlation_id
        return response


class ClientIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.client_ip = self._extract(request)
        return self.get_response(request)

    def _extract(self, request):
        trusted = bool(getattr(settings, "TRUSTED_PROXY", False))
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if trusted and forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = (request.META.get("REMOTE_ADDR") or "unknown").strip()
        if not ip or len(ip) > 64:
            ip = "unknown"
        return ip


__all__ = ["SecurityHeadersMiddleware", "CorrelationIdMiddleware", "ClientIPMiddleware"]
