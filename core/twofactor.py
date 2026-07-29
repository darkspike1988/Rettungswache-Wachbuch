"""Zweiter Faktor per TOTP (Google Authenticator und kompatible Apps)."""

import io
import secrets
import time
from urllib.parse import quote

import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from qrcode.image.svg import SvgPathImage

from .models import RecoveryCode, TotpDevice

TIMESTEP = 30
# Ein Schritt Toleranz in beide Richtungen faengt ungenaue Geraeteuhren ab.
VALID_WINDOW = 1
RECOVERY_CODE_COUNT = 8


def new_secret():
    return pyotp.random_base32()


def provisioning_uri(user, secret):
    """otpauth-URI, den die Authenticator-App einliest."""
    label = user.get_username()
    issuer = settings.APP_NAME
    return pyotp.TOTP(secret).provisioning_uri(name=label, issuer_name=issuer)


def qr_svg(uri):
    """QR-Code als eingebettetes SVG - kein externes Bild, kein Pillow."""
    image = qrcode.make(uri, image_factory=SvgPathImage, box_size=10, border=2)
    buffer = io.BytesIO()
    image.save(buffer)
    svg = buffer.getvalue().decode("utf-8")
    # XML-Deklaration entfernen, damit das SVG inline im HTML stehen kann.
    return svg.split("?>", 1)[-1].strip()


def _matches(secret, code):
    return pyotp.TOTP(secret).verify(code, valid_window=VALID_WINDOW)


def verify_code(device, code):
    """Prueft einen Code und verhindert die Wiederverwendung desselben
    Zeitschritts."""
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit():
        return False
    if not _matches(device.secret, code):
        return False
    timestep = int(time.time()) // TIMESTEP
    if timestep <= device.last_timestep:
        return False
    device.last_timestep = timestep
    if device.pk:
        device.save(update_fields=["last_timestep"])
    # Bei der Einrichtung ist das Geraet noch nicht gespeichert; der Wert geht
    # dann mit dem anschliessenden vollstaendigen save() mit.
    return True


def _normalise_recovery(value):
    return (value or "").strip().replace(" ", "").replace("-", "").lower()


def verify_recovery_code(device, value):
    """Verbraucht einen Wiederherstellungscode, falls er passt."""
    candidate = _normalise_recovery(value)
    if not candidate:
        return False
    for entry in device.recovery_codes.filter(used_at__isnull=True):
        if check_password(candidate, entry.code_hash):
            entry.used_at = timezone.now()
            entry.save(update_fields=["used_at"])
            return True
    return False


@transaction.atomic
def issue_recovery_codes(device):
    """Erzeugt einen frischen Satz Codes und gibt sie im Klartext zurueck -
    danach sind nur noch die Hashes gespeichert."""
    device.recovery_codes.all().delete()
    plain_codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        code = f"{secrets.randbelow(10**5):05d}-{secrets.randbelow(10**5):05d}"
        plain_codes.append(code)
        RecoveryCode.objects.create(
            device=device, code_hash=make_password(_normalise_recovery(code)),
        )
    return plain_codes


def device_for(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return TotpDevice.objects.filter(user=user, confirmed=True).first()


def is_enabled(user):
    return device_for(user) is not None


def manual_entry_key(secret):
    """Der Schluessel in Vierergruppen, falls der QR-Code nicht scannbar ist."""
    return " ".join(secret[index:index + 4] for index in range(0, len(secret), 4))


def account_label(user):
    return quote(user.get_username())
