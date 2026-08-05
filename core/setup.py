from __future__ import annotations

import hmac

from django.conf import settings

from .models import Membership

SETUP_SESSION_KEY = "rwsth_setup_authorized"


def installation_complete() -> bool:
    """A usable installation always has an active station Master-Admin."""
    if not getattr(settings, "SETUP_WIZARD_ENABLED", True):
        return True
    return Membership.objects.filter(
        role=Membership.Role.ADMIN,
        is_active=True,
        station__is_active=True,
        user__is_active=True,
    ).exists()


def configured_setup_token() -> str:
    return str(getattr(settings, "SETUP_TOKEN", "") or "")


def setup_token_is_secure() -> bool:
    token = configured_setup_token()
    return len(token) >= 32 and not token.lower().startswith("replace-")


def setup_token_matches(candidate: str) -> bool:
    if not setup_token_is_secure() or not candidate:
        return False
    return hmac.compare_digest(configured_setup_token(), str(candidate))
