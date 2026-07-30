# Rettungswache-Wachbuch

[![CI](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml/badge.svg)](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Ein selbst gehostetes, mobiles Wachbuch fuer die interne Organisation einer
Rettungswache. Die Anwendung ist kein Einsatzleit-, Alarmierungs-,
Dienstplanungs- oder Patientendokumentationssystem.

## Funktionen

- versionierte Uebergaben mit Prioritaet und Status
- einfacher Wachenkalender
- freiwillige Geburtstagsanzeige ohne Geburtsjahr
- unveraenderliches Kaffeekassen-Ledger mit Korrekturbuchungen
- optionale offizielle RSS- und Verkehrsquellen
- stationsbezogene Rollen und nachvollziehbare Audit-Ereignisse
- lokaler Login oder Anmeldung ueber Tailscale-Identitaetsheader
- responsive, JavaScript-freie Oberflaeche

## Administration

Stationsadministratoren koennen unter `/einstellungen/` den Namen der Wache und
die sichtbaren Module selbst festlegen. Unter `/team/` verwalten sie Freigaben
und Rollen. Technische Administratoren konfigurieren unter `/django-admin/`
Systemkonten und externe Quellen. Fachliche Datensaetze sind dort bewusst nur
lesbar, damit Versionierung und Audit nicht umgangen werden.

## Schnellstart mit Docker

Voraussetzungen sind Docker Engine mit Compose v2 und ein freier lokaler Port.

```bash
git clone https://github.com/Darkspike1988/Rettungswache-Wachbuch.git
cd Rettungswache-Wachbuch
cp .env.example .env
```

In `.env` muessen alle Platzhalter durch unabhaengige Zufallswerte ersetzt
werden. Geeignete Werte erzeugt beispielsweise `openssl rand -hex 32`. Das
Backup-Verzeichnis muss fuer den PostgreSQL-Benutzer im Container schreibbar
sein:

```bash
sudo chown 70:70 backups
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py grant_station_admin BENUTZERNAME
```

Danach ist die Anwendung standardmaessig unter `http://127.0.0.1:8090` und die
Anmeldung unter `/anmelden/` erreichbar. Der Port bindet absichtlich nur an
Loopback. Fuer andere Geraete ist ein abgesicherter Reverse-Proxy mit TLS oder
Tailscale Serve erforderlich. `SECURE_COOKIES=false` ist ausschliesslich fuer
diesen lokalen HTTP-Schnellstart vorgesehen.

Tests:

```bash
docker compose exec web python manage.py test --settings=config.test_settings
```

## Tailscale-Anmeldung

Fuer eine Tailnet-only-Installation werden in `.env` mindestens diese Werte
gesetzt:

```dotenv
TRUST_TAILSCALE_HEADERS=true
TAILSCALE_ADMIN_LOGIN=admin@example.org
SECURE_COOKIES=true
ALLOWED_HOSTS=your-host.example.ts.net
CSRF_TRUSTED_ORIGINS=https://your-host.example.ts.net
```

Die Identitaetsheader duerfen nur an einem nicht oeffentlich erreichbaren
Loopback-Port akzeptiert werden. Hinweise zur Proxy-Konfiguration stehen in
[`docs/OPERATIONS.md`](docs/OPERATIONS.md).

`createsuperuser` erzeugt bewusst einen globalen technischen Administrator fuer
den Django-Admin. Eine stationsbezogene Adminrolle allein vergibt keine globalen
Systemrechte.

## Externe Quellen

Zulaessige Quellhosts werden zuerst kommasepariert mit `FEED_ALLOWED_HOSTS` in
`.env` freigegeben. Anschliessend koennen HTTPS-RSS-Quellen unter
`/django-admin/core/feedsource/` angelegt werden. Der CSV-Importer unterstuetzt
das dokumentierte Bielefelder Verkehrsmeldungsformat. Private Zieladressen,
Weiterleitungen, andere Ports und Antworten ueber 2 MB werden abgewiesen.
Bei einem Upgrade von Version 0.2 muessen die Hosts bereits vorhandener Quellen
vor dem Neustart explizit in diese Liste uebernommen werden.

## Datenschutz

Nicht in das Wachbuch gehoeren:

- Patienten-, Gesundheits-, Einsatz- oder Alarmierungsdaten
- Krankheitsgruende, Leistungsbewertungen oder private Konflikte
- gemeinsam genutzte Konten

Ein technischer Betrieb ersetzt keine Datenschutzpruefung, Mitbestimmung,
Loeschfristen oder organisatorische Freigabe. Details stehen in
[`docs/SECURITY-PRIVACY.md`](docs/SECURITY-PRIVACY.md).

## Dokumentation

- [Architektur](docs/ARCHITECTURE.md)
- [Betrieb, Backup und Updates](docs/OPERATIONS.md)
- [Datenschutz und Sicherheit](docs/SECURITY-PRIVACY.md)
- [Test- und Go-live-Checkliste](docs/GO-LIVE-CHECKLIST.md)
- [Recherche und Quellen](docs/RESEARCH.md)
- [Audit und Folgeplan](docs/AUDIT-2026-07.md)
- [Roadmap](docs/ROADMAP.md)
- [Designregeln](docs/DESIGN-SYSTEM.md)

## Mitwirken

Beitraege sind willkommen. Vor einem Pull Request bitte
[`CONTRIBUTING.md`](CONTRIBUTING.md) und fuer vertrauliche Meldungen
[`SECURITY.md`](SECURITY.md) beachten.

## Lizenz

Copyright (C) 2026 Darkspike1988. Veroeffentlicht unter der GNU Affero General
Public License v3.0 oder spaeter. Wer eine geaenderte Fassung als Netzwerkdienst
betreibt, muss den Benutzern den zugehoerigen Quellcode anbieten.
