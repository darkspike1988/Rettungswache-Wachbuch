"""WebAuthn / Passkey helpers (registration and authentication)."""

from __future__ import annotations

import json

from django.conf import settings
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from .models import WebAuthnCredential


def webauthn_enabled():
    return bool(getattr(settings, "WEBAUTHN_ENABLED", True)) and bool(rp_id()) and bool(rp_origin())


def rp_id():
    return (getattr(settings, "WEBAUTHN_RP_ID", "") or "").strip()


def rp_origin():
    return (getattr(settings, "WEBAUTHN_ORIGIN", "") or "").strip()


def rp_name():
    return getattr(settings, "APP_NAME", "Wachbuch")


def user_has_passkey(user):
    return WebAuthnCredential.objects.filter(user=user).exists()


def _exclude_credentials(user):
    return [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(item.credential_id))
        for item in WebAuthnCredential.objects.filter(user=user)
    ]


def registration_options_for(user):
    options = generate_registration_options(
        rp_id=rp_id(),
        rp_name=rp_name(),
        user_id=str(user.pk).encode("utf-8"),
        user_name=user.get_username(),
        user_display_name=user.get_full_name() or user.get_username(),
        exclude_credentials=_exclude_credentials(user),
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    return options, options_to_json(options)


def verify_and_store_registration(user, credential_json, expected_challenge, device_name=""):
    verification = verify_registration_response(
        credential=json.loads(credential_json),
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_rp_id=rp_id(),
        expected_origin=rp_origin(),
        require_user_verification=False,
    )
    credential_id = bytes_to_base64url(verification.credential_id)
    public_key = bytes_to_base64url(verification.credential_public_key)
    credential, created = WebAuthnCredential.objects.update_or_create(
        credential_id=credential_id,
        defaults={
            "user": user,
            "public_key": public_key,
            "sign_count": verification.sign_count,
            "device_name": (device_name or "")[:120],
        },
    )
    return credential, created


def authentication_options(user=None):
    allow = []
    if user is not None:
        allow = _exclude_credentials(user)
    options = generate_authentication_options(
        rp_id=rp_id(),
        allow_credentials=allow or None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    return options, options_to_json(options)


def verify_authentication(credential_json, expected_challenge, expected_user=None):
    payload = json.loads(credential_json)
    raw_id = payload.get("rawId") or payload.get("id")
    if not raw_id:
        raise ValueError("Passkey-Antwort ohne Credential-ID.")
    credential_id = raw_id if isinstance(raw_id, str) else bytes_to_base64url(raw_id)
    stored = WebAuthnCredential.objects.select_related("user").filter(
        credential_id=credential_id
    ).first()
    if stored is None:
        raise ValueError("Unbekannter Passkey.")
    if expected_user is not None and stored.user_id != expected_user.pk:
        raise ValueError("Passkey gehört zu einem anderen Konto.")
    verification = verify_authentication_response(
        credential=payload,
        expected_challenge=base64url_to_bytes(expected_challenge),
        expected_rp_id=rp_id(),
        expected_origin=rp_origin(),
        credential_public_key=base64url_to_bytes(stored.public_key),
        credential_current_sign_count=stored.sign_count,
        require_user_verification=False,
    )
    stored.sign_count = verification.new_sign_count
    stored.last_used_at = timezone.now()
    stored.save(update_fields=["sign_count", "last_used_at"])
    return stored.user
