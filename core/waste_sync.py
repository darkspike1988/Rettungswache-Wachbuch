"""Müllkalender-Sync: HTTPS-ICS-Feed pro Station abrufen und parsen.

SSRF-Schutz wie bei ``core.feed_sync``: HTTPS-only, Port 443, DNS wird
aufgelöst und nur globale IP-Adressen akzeptiert, direkter Connect zur IP mit
``assert_hostname``/``server_hostname``, Zertifikatsprüfung aktiv, keine
Weiterleitungen, Groessenlimit. Der Host kann zusaetzlich ueber
``WASTE_CALENDAR_ALLOWED_HOSTS`` eingeschraenkt werden.

Das ICS wird mit einem minimalen Parser gelesen, damit keine neue
Abhaengigkeit (``icalendar``) noetig wird. Unterstuetzt werden ``VEVENT`` mit
``SUMMARY``, ``UID`` und ``DTSTART`` als ``DATE`` (ganztuegig) oder
``DATETIME`` (mit/ohne ``Z``). Zeilen-Folding (RFC 5545) wird aufgehoben.
"""

from __future__ import annotations

import ipaddress
import socket
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from urllib.parse import urlparse

import certifi
import urllib3
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import WasteCollection


class WasteSyncError(ValueError):
    """Erwartbare Fehlermeldung, die am Station-Objekt protokolliert wird."""


def fetch_waste_ics(url: str) -> bytes:
    """Ruft den ICS-Feed unter SSRF-Hardening ab und liefert die rohen Bytes."""
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
    ):
        raise WasteSyncError("Müllkalender-Quelle muss HTTPS ohne Anmeldedaten sein.")
    if parsed.port not in {None, 443}:
        raise WasteSyncError("Müllkalender-Quellen dürfen nur HTTPS-Port 443 verwenden.")
    allowed = getattr(settings, "WASTE_CALENDAR_ALLOWED_HOSTS", set())
    if allowed and (parsed.hostname or "").lower() not in allowed:
        raise WasteSyncError("Müllkalender-Host ist nicht in WASTE_CALENDAR_ALLOWED_HOSTS.")
    resolved = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(item[4][0] for item in resolved))
    if not addresses or any(not ipaddress.ip_address(value).is_global for value in addresses):
        raise WasteSyncError("Müllkalender-Quelle zeigt nicht ausschliesslich auf globale IPs.")
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    timeout = urllib3.Timeout(connect=5, read=20)
    max_bytes = getattr(settings, "WASTE_CALENDAR_MAX_BYTES", 1_000_000)
    connection_error = None
    for address in addresses:
        pool = urllib3.HTTPSConnectionPool(
            address,
            port=443,
            assert_hostname=parsed.hostname,
            server_hostname=parsed.hostname,
            cert_reqs="CERT_REQUIRED",
            ca_certs=certifi.where(),
            timeout=timeout,
            maxsize=1,
        )
        try:
            response = pool.request(
                "GET",
                target,
                headers={"Host": parsed.hostname, "User-Agent": "Wachbuch/1.0"},
                preload_content=False,
                redirect=False,
                retries=False,
            )
        except urllib3.exceptions.HTTPError as exc:
            connection_error = exc
            pool.close()
            continue
        try:
            if 300 <= response.status < 400:
                raise WasteSyncError("Weiterleitungen sind für Müllkalender deaktiviert.")
            if response.status >= 400:
                raise WasteSyncError(f"Müllkalender-Quelle antwortet mit HTTP {response.status}.")
            content = bytearray()
            for chunk in response.stream(64 * 1024):
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise WasteSyncError("Müllkalender-Quelle überschreitet das Größenlimit.")
            return bytes(content)
        finally:
            response.release_conn()
            pool.close()
    raise WasteSyncError(f"Müllkalender-Quelle ist nicht erreichbar: {connection_error}")


def _unfold(lines):
    """Hebt RFC-5545 Zeilen-Folding (führende Leerzeichen/Tab) auf."""
    unfolded = []
    for raw in lines:
        if raw.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw[1:]
        else:
            unfolded.append(raw)
    return unfolded


def _parse_ics_datetime(value: str):
    value = value.strip()
    if value.endswith("Z"):
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=datetime_timezone.utc)
    if "T" in value:
        return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=datetime_timezone.utc)
    day = datetime.strptime(value, "%Y%m%d").date()
    return day


def parse_ics(payload: bytes):
    """Liefert eine Liste von Dicts {uid, summary, start, all_day} aus dem ICS."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        text = payload.decode("latin-1", errors="replace")
    lines = _unfold(text.replace("\r\n", "\n").split("\n"))
    events = []
    current = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {"uid": "", "summary": "", "start": None, "all_day": False}
            continue
        if line == "END:VEVENT":
            if current is not None and current["start"] is not None:
                events.append(current)
            current = None
            continue
        if current is None:
            continue
        key, _, value = line.partition(":")
        key = key.split(";", 1)[0].upper()
        if key == "UID":
            current["uid"] = value.strip()[:300]
        elif key == "SUMMARY":
            current["summary"] = _unescape(value).strip()[:200] or "Abfuhr"
        elif key == "DTSTART":
            current["all_day"] = ";VALUE=DATE" in line.upper() or "T" not in value
            current["start"] = _parse_ics_datetime(value)
    return events


def _unescape(value: str) -> str:
    return (
        value.replace("\\N", "\n")
        .replace("\\n", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


@transaction.atomic
def store_waste_collections(station, events, *, source_url: str, source_label: str) -> int:
    station.waste_collections.all().delete()
    tz = timezone.get_current_timezone()
    rows = []
    for event in events:
        start = event["start"]
        if isinstance(start, datetime):
            starts_at = start.astimezone(datetime_timezone.utc) if start.utcoffset() else start.replace(tzinfo=datetime_timezone.utc)
            ends_at = starts_at
        else:
            starts_at = timezone.make_aware(datetime.combine(start, time.min), tz)
            ends_at = starts_at + timedelta(days=1)
        rows.append(WasteCollection(
            station=station,
            title=event["summary"] or "Abfuhr",
            starts_at=starts_at,
            ends_at=ends_at,
            source_url=source_url[:600],
            source_label=(source_label or "Müll")[:80],
            external_uid=event["uid"][:300],
        ))
    if rows:
        WasteCollection.objects.bulk_create(rows)
    return len(rows)


def sync_station_waste(station) -> int:
    """Ruft den ICS-Feed ab, parst und ersetzt die WasteCollections der Station."""
    if not station.waste_calendar_enabled or not station.waste_calendar_url:
        return 0
    payload = fetch_waste_ics(station.waste_calendar_url)
    events = parse_ics(payload)
    return store_waste_collections(
        station,
        events,
        source_url=station.waste_calendar_url,
        source_label=station.waste_calendar_label or "Müll",
    )
