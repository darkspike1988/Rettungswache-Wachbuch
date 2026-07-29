import calendar
import csv
import hashlib
import io
from datetime import datetime, timezone as datetime_timezone
from urllib.parse import urlparse

import feedparser
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.html import strip_tags
from icalendar import Calendar

from .models import FeedItem, FeedSource
from .net import UnsafeUrlError, fetch_https


def fetch_source(source):
    try:
        return fetch_https(
            source.url,
            allowed_hosts=settings.FEED_ALLOWED_HOSTS,
            max_bytes=settings.FEED_MAX_BYTES,
            user_agent="Rettungswache-Wachbuch/1.0",
        )
    except UnsafeUrlError as exc:
        raise ValueError(str(exc)) from exc


def sync_source(source):
    try:
        payload = fetch_source(source)
        if source.kind == FeedSource.Kind.NEWS_RSS:
            count = sync_rss(source, payload)
        elif source.kind == FeedSource.Kind.CLOSURE_CSV:
            count = sync_closure_csv(source, payload)
        elif source.kind == FeedSource.Kind.WASTE_ICS:
            count = sync_waste_ics(source, payload)
        else:
            raise ValueError("Unbekannter Quelltyp.")
        source.last_success_at = timezone.now()
        source.last_error = ""
        source.save(update_fields=["last_success_at", "last_error"])
        return count
    except Exception as exc:
        source.last_error_at = timezone.now()
        source.last_error = str(exc)[:300]
        source.save(update_fields=["last_error_at", "last_error"])
        raise


@transaction.atomic
def sync_rss(source, payload):
    parsed = feedparser.parse(payload)
    if parsed.bozo and not parsed.entries:
        raise ValueError(f"RSS konnte nicht gelesen werden: {parsed.bozo_exception}")
    count = 0
    for entry in parsed.entries[:100]:
        link = safe_item_url(str(entry.get("link", "")))
        external_id = str(entry.get("id") or link or hashlib.sha256(
            str(entry.get("title", "")).encode("utf-8")
        ).hexdigest())[:300]
        published = None
        if entry.get("published_parsed"):
            published = datetime.fromtimestamp(
                calendar.timegm(entry.published_parsed), tz=datetime_timezone.utc
            )
        FeedItem.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults={
                "title": strip_tags(str(entry.get("title", "")))[:300],
                "summary": strip_tags(str(entry.get("summary", "")))[:1500],
                "url": link[:600],
                "published_at": published,
            },
        )
        count += 1
    return count


def safe_item_url(value):
    parsed = urlparse(value)
    if (
        parsed.scheme == "https"
        and parsed.hostname in settings.FEED_ALLOWED_HOSTS
        and parsed.port in {None, 443}
    ):
        return value[:600]
    return ""


@transaction.atomic
def sync_closure_csv(source, payload):
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    expected = {"gid", "strasse", "beginn", "ende", "art_arb"}
    if not reader.fieldnames or not expected.issubset(set(reader.fieldnames)):
        raise ValueError("CSV-Schema der Verkehrsmeldungen ist unerwartet.")
    seen = []
    count = 0
    for row in reader:
        external_id = str(row.get("gid", "")).strip()
        if not external_id:
            continue
        seen.append(external_id)
        street = row.get("strasse", "").strip() or "Verkehrsmeldung"
        district = row.get("ortsteil", "").strip()
        title = f"{street} - {district}" if district else street
        summary_parts = [
            row.get("art_arb", "").strip(),
            row.get("art_vb", "").strip(),
            row.get("vonbis", "").strip(),
        ]
        FeedItem.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults={
                "title": title[:300],
                "summary": " | ".join(part for part in summary_parts if part)[:1500],
                "url": "https://open-data.bielefeld.de/dataset/verkehrsmeldungen",
                "starts_on": parse_csv_date(row.get("beginn")),
                "ends_on": parse_csv_date(row.get("ende")),
            },
        )
        count += 1
    source.items.exclude(external_id__in=seen).delete()
    return count


def parse_csv_date(value):
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y/%m/%d").date()


def as_date(value):
    return value.date() if hasattr(value, "date") else value


@transaction.atomic
def sync_waste_ics(source, payload):
    try:
        calendar_data = Calendar.from_ical(payload)
    except ValueError as exc:
        raise ValueError(f"ICS-Kalender konnte nicht gelesen werden: {exc}") from exc
    today = timezone.localdate()
    seen = []
    count = 0
    for component in calendar_data.walk("VEVENT"):
        start = component.get("dtstart")
        if not start:
            continue
        pickup_date = as_date(start.dt)
        if pickup_date < today:
            continue
        uid = str(component.get("uid") or f"{pickup_date.isoformat()}-{component.get('summary')}")
        external_id = uid[:300]
        seen.append(external_id)
        FeedItem.objects.update_or_create(
            source=source,
            external_id=external_id,
            defaults={
                "title": str(component.get("summary", "Abholung"))[:300],
                "summary": str(component.get("description", ""))[:1500],
                "starts_on": pickup_date,
            },
        )
        count += 1
    source.items.filter(starts_on__lt=today).delete()
    source.items.exclude(external_id__in=seen).filter(starts_on__gte=today).delete()
    return count
