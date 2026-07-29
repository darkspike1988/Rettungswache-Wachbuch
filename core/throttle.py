import hashlib

from django.conf import settings
from django.core.cache import cache


def _counter_key(prefix, value):
    """Der Zaehler haengt an einem Hash, damit keine E-Mail-Adressen im Cache
    stehen."""
    digest = hashlib.sha256(
        f"{settings.SECRET_KEY}:{prefix}:{value}".encode("utf-8")
    ).hexdigest()[:32]
    return f"throttle:{prefix}:{digest}"


def exceeds_limit(prefix, value, limit, window):
    """Zaehlt einen Versuch und meldet, ob das Limit ueberschritten ist."""
    if not value or limit <= 0:
        return False
    key = _counter_key(prefix, value)
    cache.add(key, 0, window)
    try:
        count = cache.incr(key)
    except ValueError:
        # Der Eintrag ist zwischen add und incr abgelaufen.
        cache.set(key, 1, window)
        count = 1
    return count > limit


def password_reset_is_throttled(email, ip_address):
    window = settings.PASSWORD_RESET_WINDOW_SECONDS
    # Beide Zaehler bewusst auswerten, damit jeder Versuch in beiden zaehlt.
    by_email = exceeds_limit(
        "pwreset-mail", email.strip().lower(),
        settings.PASSWORD_RESET_MAX_PER_EMAIL, window,
    )
    by_ip = exceeds_limit(
        "pwreset-ip", ip_address, settings.PASSWORD_RESET_MAX_PER_IP, window,
    )
    return by_email or by_ip
