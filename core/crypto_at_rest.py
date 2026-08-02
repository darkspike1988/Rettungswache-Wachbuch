"""AES-256-GCM helpers for secrets at rest (BSI TR-02102 aligned).

Uses a key derived from Django SECRET_KEY via HKDF-SHA256.
Format: ``v1.<nonce_b64url>.<ciphertext_b64url>``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

PREFIX = "v1."
_INFO = b"wachbuch-at-rest-v1"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _master_key() -> bytes:
    material = (settings.SECRET_KEY or "").encode("utf-8")
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=b"wachbuch-totp-secret-v1",
        info=_INFO,
    ).derive(material)


def is_encrypted(value: str | None) -> bool:
    return bool(value) and str(value).startswith(PREFIX)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        raise ValueError("Leerer Geheimwert.")
    if is_encrypted(plaintext):
        return plaintext
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(_master_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return f"{PREFIX}{_b64e(nonce)}.{_b64e(ciphertext)}"


def decrypt_secret(value: str) -> str:
    if not value:
        return value
    if not is_encrypted(value):
        # Legacy plaintext (pre-0.13) – still usable until re-saved.
        return value
    try:
        _, nonce_b64, data_b64 = value.split(".", 2)
        nonce = _b64d(nonce_b64)
        plaintext = AESGCM(_master_key()).decrypt(nonce, _b64d(data_b64), None)
        return plaintext.decode("utf-8")
    except Exception as exc:  # noqa: BLE001 – surface as ValueError to callers
        raise ValueError("Gespeichertes Geheimnis konnte nicht entschlüsselt werden.") from exc


def digest_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode("utf-8")).digest(),
        hashlib.sha256(right.encode("utf-8")).digest(),
    )
