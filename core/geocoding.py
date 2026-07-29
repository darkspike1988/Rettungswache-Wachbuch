import json
from urllib.parse import urlencode

from django.conf import settings

from .net import UnsafeUrlError, fetch_https


class GeocodingError(Exception):
    pass


def lookup_district(street, postal_code, city):
    """Ermittelt Ort und Kreis/Landkreis zu einer Adresse ueber einen
    Nominatim-kompatiblen, offenen Geocoding-Dienst (z.B. selbst gehostet
    oder nominatim.openstreetmap.org). Deaktiviert, solange GEOCODING_HOST
    nicht gesetzt ist."""
    if not settings.GEOCODING_HOST:
        raise GeocodingError("Kein Geocoding-Dienst konfiguriert (GEOCODING_HOST).")
    query = ", ".join(part.strip() for part in [street, postal_code, city] if part and part.strip())
    if not query:
        raise GeocodingError("Bitte zuerst Strasse, PLZ oder Ort eintragen.")
    params = urlencode({"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 1})
    url = f"https://{settings.GEOCODING_HOST}/search?{params}"
    try:
        payload = fetch_https(
            url,
            allowed_hosts={settings.GEOCODING_HOST},
            max_bytes=200_000,
            user_agent=f"{settings.APP_NAME}/1.0 (+{settings.SOURCE_URL})",
        )
    except UnsafeUrlError as exc:
        raise GeocodingError(str(exc)) from exc
    try:
        results = json.loads(payload)
    except ValueError as exc:
        raise GeocodingError("Antwort des Geocoding-Dienstes konnte nicht gelesen werden.") from exc
    if not results:
        raise GeocodingError("Zu dieser Adresse wurde kein Ort gefunden.")
    address = results[0].get("address", {})
    district = address.get("county") or address.get("state_district") or ""
    city_name = (
        address.get("city") or address.get("town") or address.get("village")
        or address.get("municipality") or ""
    )
    if not district and not city_name:
        raise GeocodingError("Der Dienst lieferte keinen Ort oder Kreis zu dieser Adresse.")
    return {"district": district, "city": city_name}
