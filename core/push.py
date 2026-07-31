"""Web Push helpers for urgent handover alerts."""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


def web_push_enabled():
    return bool(getattr(settings, "WEB_PUSH_ENABLED", False)) and bool(
        getattr(settings, "VAPID_PUBLIC_KEY", "")
    ) and bool(getattr(settings, "VAPID_PRIVATE_KEY", ""))


def vapid_public_key():
    return getattr(settings, "VAPID_PUBLIC_KEY", "") or ""


def notify_urgent_handover(handover, actor):
    """Best-effort push to station members (except actor). Never raises to callers."""
    if not web_push_enabled():
        return 0
    if handover.priority != handover.Priority.URGENT:
        return 0
    try:
        from pywebpush import WebPushException, webpush

        from .models import PushSubscription
    except Exception as exc:  # pragma: no cover - import guard
        logger.warning("Web-Push nicht verfügbar: %s", exc)
        return 0

    url = reverse("handover_detail", args=[handover.pk])
    payload = json.dumps({
        "title": "Dringende Übergabe",
        "body": handover.title[:120],
        "url": url,
    })
    vapid_claims = {
        "sub": f"mailto:{getattr(settings, 'VAPID_ADMIN_EMAIL', 'ops@localhost')}",
    }
    sent = 0
    subscriptions = PushSubscription.objects.filter(station=handover.station).exclude(
        user=actor
    )
    for item in subscriptions:
        subscription_info = {
            "endpoint": item.endpoint,
            "keys": {"p256dh": item.p256dh, "auth": item.auth},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                item.delete()
            else:
                logger.info("Web-Push fehlgeschlagen für %s: %s", item.pk, exc)
        except Exception as exc:  # pragma: no cover
            logger.info("Web-Push Fehler für %s: %s", item.pk, exc)
    return sent
