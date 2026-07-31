import pyotp
from django.conf import settings
from django.utils import timezone

from .models import TotpDevice


def mfa_enabled():
    return bool(getattr(settings, "MFA_ENABLED", True))


def mfa_required():
    return bool(getattr(settings, "MFA_REQUIRED", False))


def user_has_confirmed_mfa(user):
    return TotpDevice.objects.filter(user=user, is_confirmed=True).exists()


def provisioning_uri(device, issuer=None):
    issuer = issuer or settings.APP_NAME
    return pyotp.TOTP(device.secret).provisioning_uri(
        name=user_label(device.user),
        issuer_name=issuer,
    )


def user_label(user):
    return user.get_username()


def create_pending_device(user):
    secret = pyotp.random_base32()
    device, _ = TotpDevice.objects.update_or_create(
        user=user,
        defaults={
            "secret": secret,
            "is_confirmed": False,
            "confirmed_at": None,
        },
    )
    return device


def verify_totp(device, token):
    token = (token or "").strip().replace(" ", "")
    if not token.isdigit():
        return False
    totp = pyotp.TOTP(device.secret)
    return totp.verify(token, valid_window=1)


def confirm_device(device, token):
    if not verify_totp(device, token):
        return False
    device.is_confirmed = True
    device.confirmed_at = timezone.now()
    device.save(update_fields=["is_confirmed", "confirmed_at"])
    return True


def disable_device(user):
    TotpDevice.objects.filter(user=user).delete()
