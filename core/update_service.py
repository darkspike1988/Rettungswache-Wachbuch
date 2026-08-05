from __future__ import annotations

import json
import re
from dataclasses import dataclass

import certifi
import urllib3
from django.conf import settings

_REPOSITORY_RE = re.compile(r"\A[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
_VERSION_RE = re.compile(
    r"\Av?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?P<suffix>-[0-9A-Za-z.-]+)?\Z"
)
_MAX_RELEASE_RESPONSE = 256 * 1024


class UpdateCheckError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    url: str
    published_at: str
    notes: str


def normalize_version(value: str) -> str:
    match = _VERSION_RE.fullmatch(str(value or "").strip())
    if not match:
        raise UpdateCheckError("Die Release-Version ist kein gültiges SemVer.")
    suffix = match.group("suffix") or ""
    return (
        f"{match.group('major')}.{match.group('minor')}.{match.group('patch')}{suffix}"
    )


def version_key(value: str) -> tuple[int, int, int, int, str]:
    normalized = normalize_version(value)
    core, separator, prerelease = normalized.partition("-")
    major, minor, patch = (int(part) for part in core.split("."))
    return major, minor, patch, 0 if separator else 1, prerelease


def is_newer_version(candidate: str, current: str) -> bool:
    return version_key(candidate) > version_key(current)


def fetch_latest_release() -> ReleaseInfo:
    if not getattr(settings, "UPDATE_CHECK_ENABLED", True):
        raise UpdateCheckError("Die Online-Updateprüfung ist deaktiviert.")
    repository = str(getattr(settings, "UPDATE_REPOSITORY", "") or "").strip()
    if not _REPOSITORY_RE.fullmatch(repository):
        raise UpdateCheckError("UPDATE_REPOSITORY ist ungültig konfiguriert.")

    pool = urllib3.PoolManager(
        cert_reqs="CERT_REQUIRED",
        ca_certs=certifi.where(),
        timeout=urllib3.Timeout(connect=5, read=10),
        retries=False,
    )
    try:
        response = pool.request(
            "GET",
            f"https://api.github.com/repos/{repository}/releases/latest",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Rettungswache-Wachbuch-Update-Check",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            redirect=False,
            preload_content=False,
        )
    except urllib3.exceptions.HTTPError as exc:
        pool.clear()
        raise UpdateCheckError("GitHub Releases ist derzeit nicht erreichbar.") from exc
    try:
        if 300 <= response.status < 400:
            raise UpdateCheckError("Die Release-Abfrage wurde unerwartet umgeleitet.")
        if response.status != 200:
            raise UpdateCheckError(
                f"Release-Abfrage fehlgeschlagen (HTTP {response.status})."
            )
        payload = response.read(_MAX_RELEASE_RESPONSE + 1)
        if len(payload) > _MAX_RELEASE_RESPONSE:
            raise UpdateCheckError("Die Release-Antwort ist unerwartet groß.")
    finally:
        response.release_conn()
        pool.clear()

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateCheckError(
            "Die Release-Antwort konnte nicht gelesen werden."
        ) from exc
    if data.get("draft") or data.get("prerelease"):
        raise UpdateCheckError(
            "Das neueste Release ist nicht für automatische Updates freigegeben."
        )
    tag = str(data.get("tag_name") or "")
    version = normalize_version(tag)
    expected_prefix = f"https://github.com/{repository}/releases/"
    release_url = str(data.get("html_url") or "")
    if not release_url.startswith(expected_prefix):
        raise UpdateCheckError(
            "Die Release-URL gehört nicht zum konfigurierten Repository."
        )
    return ReleaseInfo(
        version=version,
        tag=tag,
        url=release_url,
        published_at=str(data.get("published_at") or ""),
        notes=str(data.get("body") or "")[:2000],
    )
