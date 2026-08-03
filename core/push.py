"""Web Push helpers for urgent handover alerts.

The handover transaction writes one ``PushOutbox`` row per active subscription
in the same DB transaction; a separate worker (``push_worker``) performs the
external HTTP call with retry, backoff and idempotency. The Gunicorn request
never opens a network connection to a push service.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.db import transaction
from django.urls import reverse

logger = logging.getLogger(__name__)


def web_push_enabled():
    return bool(getattr(settings, "WEB_PUSH_ENABLED", False)) and bool(
        getattr(settings, "VAPID_PUBLIC_KEY", "")
    ) and bool(getattr(settings, "VAPID_PRIVATE_KEY", ""))


def vapid_public_key():
    return getattr(settings, "VAPID_PUBLIC_KEY", "") or ""


def _build_payload(handover):
    url = reverse("handover_detail", args=[handover.pk])
    return json.dumps({
        "title": "Dringende Uebergabe",
        "body": handover.title[:120],
        "url": url,
    })


def _enqueue_outbox_rows(handover, actor):
    """Write one ``PushOutbox`` row per subscription in the current transaction.

    Must be called inside a ``transaction.atomic`` block so the outbox row is
    only persisted when the handover write commits. Returns the number of
    outbox rows created.
    """
    from .models import PushOutbox, PushSubscription

    payload = _build_payload(handover)
    subscriptions = PushSubscription.objects.filter(station=handover.station).exclude(
        user=actor
    )
    rows = [
        PushOutbox(
            station=handover.station,
            user=item.user,
            subscription=item,
            payload=payload,
        )
        for item in subscriptions
    ]
    if rows:
        PushOutbox.objects.bulk_create(rows)
    return len(rows)


@transaction.atomic
def notify_urgent_handover(handover, actor):
    """Schedule Web-Push notifications for an urgent handover via the outbox.

    No external network call happens here. The caller must already run inside
    a transaction (the handover service does); when that transaction commits,
    the worker can pick up the outbox rows.
    """
    if not web_push_enabled():
        return 0
    if handover.priority != handover.Priority.URGENT:
        return 0
    try:
        from .models import PushOutbox  # noqa: F401
    except Exception as exc:  # pragma: no cover - import guard
        logger.warning("Web-Push-Outbox nicht verfuegbar: %s", exc)
        return 0
    return _enqueue_outbox_rows(handover, actor)
