"""Helpers for end-to-end encrypted messaging (ciphertext only on server)."""

from __future__ import annotations

import re

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .access import CONTENT_ROLES
from .models import UserCryptoIdentity


B64_RE = re.compile(r"^[A-Za-z0-9_\-=]+$")
MAX_CIPHER_CHARS = 8000
MAX_WRAPS = 80


def b64url_ok(value, *, max_len=4096):
    if not isinstance(value, str) or not value or len(value) > max_len:
        return False
    return bool(B64_RE.match(value))


def station_content_users(station):
    return User.objects.filter(
        is_active=True,
        station_memberships__station=station,
        station_memberships__is_active=True,
        station_memberships__role__in=CONTENT_ROLES,
    ).distinct().order_by("first_name", "username")


def key_fingerprint(public_jwk):
    """Deterministic fingerprint of an EC P-256 public key.

    Computed over the canonical form ``crv|x|y`` (base64url values as stored),
    hex-encoded SHA-256, grouped into 8 blocks of 8 hex characters. Identical
    on server and client so colleagues can compare visually or via QR.
    """
    import base64
    import hashlib

    if not isinstance(public_jwk, dict):
        return None
    crv = public_jwk.get("crv") or ""
    x = public_jwk.get("x") or ""
    y = public_jwk.get("y") or ""
    if not x or not y:
        return None
    canonical = f"{crv}|{x}|{y}".encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return " ".join(digest[i : i + 8] for i in range(0, 32, 8))


def _fingerprint_payload(user_id, label, public_jwk):
    fingerprint = key_fingerprint(public_jwk)
    return {
        "user_id": user_id,
        "label": label,
        "public_jwk": public_jwk,
        "has_keys": public_jwk is not None,
        "fingerprint": fingerprint,
    }


def public_keys_for_users(users):
    identities = {
        item.user_id: item.public_jwk
        for item in UserCryptoIdentity.objects.filter(user__in=users)
    }
    payload = []
    for user in users:
        payload.append(
            _fingerprint_payload(
                user.id,
                (user.first_name or user.username),
                identities.get(user.id),
            )
        )
    return payload


def validate_encrypted_payload(data, *, required_recipient_ids):
    """Validate client ciphertext without ever decrypting it."""
    if not isinstance(data, dict):
        raise ValidationError("Ungültige verschlüsselte Nachricht.")
    ciphertext = data.get("ciphertext")
    nonce = data.get("nonce")
    wraps = data.get("key_wraps")
    if not b64url_ok(ciphertext, max_len=MAX_CIPHER_CHARS):
        raise ValidationError("Ciphertext fehlt oder ist ungültig.")
    if not b64url_ok(nonce, max_len=64):
        raise ValidationError("Nonce fehlt oder ist ungültig.")
    if not isinstance(wraps, dict) or not wraps or len(wraps) > MAX_WRAPS:
        raise ValidationError("Schlüsselumschläge fehlen oder sind ungültig.")
    required = {str(int(item)) for item in required_recipient_ids}
    wrap_ids = set(wraps.keys())
    missing = required - wrap_ids
    if missing:
        raise ValidationError("Nicht alle Empfänger haben einen Schlüsselumschlag.")
    cleaned_wraps = {}
    for user_id, wrap in wraps.items():
        if user_id not in required:
            # Ignore unknown extras, but keep required set exact for privacy channels.
            continue
        if not isinstance(wrap, dict):
            raise ValidationError("Schlüsselumschlag ungültig.")
        epk = wrap.get("epk")
        wrapped = wrap.get("wrapped_key")
        if not isinstance(epk, dict) or not isinstance(wrapped, str) or "." not in wrapped:
            raise ValidationError("Schlüsselumschlag ungültig.")
        iv_part, data_part = wrapped.split(".", 1)
        if not b64url_ok(iv_part, max_len=64) or not b64url_ok(data_part, max_len=512):
            raise ValidationError("Schlüsselumschlag ungültig.")
        cleaned_wraps[user_id] = {
            "epk": {
                "kty": epk.get("kty"),
                "crv": epk.get("crv"),
                "x": epk.get("x"),
                "y": epk.get("y"),
            },
            "wrapped_key": wrapped,
        }
        if cleaned_wraps[user_id]["epk"]["kty"] != "EC" or cleaned_wraps[user_id]["epk"]["crv"] != "P-256":
            raise ValidationError("Nur ECDH P-256 wird unterstützt.")
        if not b64url_ok(cleaned_wraps[user_id]["epk"]["x"], max_len=128):
            raise ValidationError("Öffentlicher Ephemeral-Schlüssel ungültig.")
        if not b64url_ok(cleaned_wraps[user_id]["epk"]["y"], max_len=128):
            raise ValidationError("Öffentlicher Ephemeral-Schlüssel ungültig.")
    if set(cleaned_wraps) != required:
        raise ValidationError("Schlüsselumschläge passen nicht zu den Empfängern.")
    return {
        "ciphertext": ciphertext,
        "nonce": nonce,
        "key_wraps": cleaned_wraps,
        "algo": "A256GCM+ECDH-ES",
    }


def ordered_pair(user_a_id, user_b_id):
    low, high = sorted((int(user_a_id), int(user_b_id)))
    if low == high:
        raise ValidationError("Privater Chat braucht zwei unterschiedliche Personen.")
    return low, high


def user_can_access_conversation(user, conversation):
    return user.id in {conversation.user_low_id, conversation.user_high_id}


def serialize_message_for_client(message, viewer_id):
    """Return ciphertext envelope; never include legacy plaintext for encrypted rows."""
    if message.is_encrypted:
        wraps = message.key_wraps or {}
        mine = wraps.get(str(viewer_id))
        return {
            "id": message.pk,
            "author_id": message.author_id,
            "created_at": message.created_at.isoformat(),
            "is_encrypted": True,
            "ciphertext": message.ciphertext,
            "nonce": message.nonce,
            "wrap": mine,
            "algo": message.algo,
        }
    return {
        "id": message.pk,
        "author_id": message.author_id,
        "created_at": message.created_at.isoformat(),
        "is_encrypted": False,
        "legacy_body": message.body,
    }
