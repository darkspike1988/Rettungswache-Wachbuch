"""AES-256-GCM helpers for secrets at rest (BSI TR-02102 aligned).

The master key is sourced, in priority order:

1. ``CRYPTO_MASTER_KEY`` (hex-encoded 32 bytes) – independent of
   ``SECRET_KEY`` and therefore rotatable without invalidating existing
   envelopes (see ``rotate_crypto_key`` management command).
2. HKDF-SHA256 derived from ``SECRET_KEY`` – backwards-compatible default.

During a key rotation ``CRYPTO_PREVIOUS_MASTER_KEY`` is consulted as a
decryption fallback so that envelopes still encrypted with the old key
remain readable until they are re-encrypted.

Envelope format: ``v1.<nonce_b64url>.<ciphertext_b64url>``
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

PREFIX = "v1."
_INFO = b"wachbuch-at-rest-v1"
_HKDF_SALT = b"wachbuch-totp-secret-v1"


class MasterKeyError(ValueError):
    """Raised when a configured master key is malformed."""


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _decode_hex_key(raw: str, env_name: str) -> bytes:
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise MasterKeyError(f"{env_name} muss Hex-codiert sein.") from exc
    if len(key) != 32:
        raise MasterKeyError(
            f"{env_name} muss genau 32 Byte (64 Hex-Zeichen) lang sein."
        )
    return key


def derive_master_key(source: str | None = None) -> bytes:
    """Return the active AES-256 master key.

    ``source`` accepts ``"master"`` (the ``CRYPTO_MASTER_KEY`` env var),
    ``"previous"`` (the ``CRYPTO_PREVIOUS_MASTER_KEY`` env var) or ``None``
    for the normal resolution priority (``CRYPTO_MASTER_KEY`` first, then
    HKDF of ``SECRET_KEY``).
    """
    if source == "previous":
        raw = os.getenv("CRYPTO_PREVIOUS_MASTER_KEY", "").strip()
        if not raw:
            raise MasterKeyError("CRYPTO_PREVIOUS_MASTER_KEY ist nicht gesetzt.")
        return _decode_hex_key(raw, "CRYPTO_PREVIOUS_MASTER_KEY")

    if source == "master":
        raw = os.getenv("CRYPTO_MASTER_KEY", "").strip()
        if not raw:
            raise MasterKeyError("CRYPTO_MASTER_KEY ist nicht gesetzt.")
        return _decode_hex_key(raw, "CRYPTO_MASTER_KEY")

    raw = os.getenv("CRYPTO_MASTER_KEY", "").strip()
    if raw:
        return _decode_hex_key(raw, "CRYPTO_MASTER_KEY")
    material = (settings.SECRET_KEY or "").encode("utf-8")
    return HKDF(
        algorithm=SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_INFO,
    ).derive(material)


def _master_key() -> bytes:
    return derive_master_key()


def _previous_master_key() -> bytes | None:
    raw = os.getenv("CRYPTO_PREVIOUS_MASTER_KEY", "").strip()
    if not raw:
        return None
    return _decode_hex_key(raw, "CRYPTO_PREVIOUS_MASTER_KEY")


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
    _, nonce_b64, data_b64 = value.split(".", 2)
    nonce = _b64d(nonce_b64)
    blob = _b64d(data_b64)
    for key in _candidate_keys():
        try:
            plaintext = AESGCM(key).decrypt(nonce, blob, None)
        except InvalidTag:
            continue
        return plaintext.decode("utf-8")
    raise ValueError("Gespeichertes Geheimnis konnte nicht entschlüsselt werden.")


def _candidate_keys() -> list[bytes]:
    """Keys tried during decryption (active key first, then migration fallback)."""
    keys = [_master_key()]
    previous = _previous_master_key()
    if previous is not None and previous != keys[0]:
        keys.append(previous)
    return keys


def try_decrypt_with_key(value: str, key: bytes) -> str | None:
    """Attempt AES-GCM decryption with ``key``; return ``None`` on failure."""
    if not value or not is_encrypted(value):
        return None
    try:
        _, nonce_b64, data_b64 = value.split(".", 2)
        nonce = _b64d(nonce_b64)
        blob = _b64d(data_b64)
        return AESGCM(key).decrypt(nonce, blob, None).decode("utf-8")
    except Exception:  # noqa: BLE001 – caller distinguishes key-miss from real error
        return None


def digest_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(
        hashlib.sha256(left.encode("utf-8")).digest(),
        hashlib.sha256(right.encode("utf-8")).digest(),
    )
