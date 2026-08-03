from __future__ import annotations

import hashlib
import uuid
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def hash_key(raw: str) -> str:
    salt = getattr(settings, "RATELIMIT_KEY_SALT", "wachbuch")
    payload = f"{salt}|{raw}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def consume(bucket: str, raw_key: str, *, limit: int, window_seconds: int) -> bool:
    """Webhook-/Registration-Style Rate-Limit. Returns True if request is allowed.

    Multi-worker-safe through DB-backed counter (PostgreSQL).
    """
    from .models import RateLimit

    if limit <= 0:
        return False

    key_hash = hash_key(raw_key)
    now = timezone.now()
    window_seconds = max(1, int(window_seconds))
    window_start = now.replace(microsecond=0)
    window_start = window_start - timedelta(
        seconds=int(window_start.timestamp()) % window_seconds
    )

    from django.db import transaction

    with transaction.atomic():
        try:
            row = (
                RateLimit.objects
                .select_for_update()
                .get(bucket=bucket, key_hash=key_hash, window_start=window_start)
            )
        except RateLimit.DoesNotExist:
            row = RateLimit.objects.create(
                bucket=bucket,
                key_hash=key_hash,
                window_start=window_start,
                count=1,
            )
            return True
        if row.count >= limit:
            return False
        row.count = row.count + 1
        row.save(update_fields=["count"])
        return True


def cleanup_expired(*, older_than_seconds: int = 7 * 24 * 3600) -> int:
    """Delete rate-limit rows older than the retention window."""
    from .models import RateLimit

    cutoff = timezone.now() - timedelta(seconds=older_than_seconds)
    deleted, _ = RateLimit.objects.filter(window_start__lt=cutoff).delete()
    return deleted
