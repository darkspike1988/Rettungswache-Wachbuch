# Rettungswache-Wachbuch

[![CI](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml/badge.svg)](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License:AGPL_v3-blue.svg)](LICENSE)

Ein selbst gehostetes, mobiles **Wachbuch** fuer die interne Organisation einer
Rettungswache (Repository: Rettungswache-Wachbuch). Die Anwendung ist kein
Einsatzleit-, Alarmierungs-, Dienstplanungs- oder Patientendokumentationssystem.

## Funktionen

- versionierte Uebergaben mit Prioritaet und Status
- einfacher Wachenkalender
- freiwillige Geburtstagsanzeige ohne Geburtsjahr
- unveraenderliches Kaffeekassen-Ledger mit Korrekturbuchungen
- optionale offizielle RSS- und Verkehrsquellen
- stationsbezogene Rollen und nachvollziehbare Audit-Ereignisse
- lokaler Login mit persoenlichen Konten
- installierbare PWA fuer Handy und Wachenterminals
- responsive App-Shell mit Offline-Hinweis fuer gelesene Seiten

## Stack

Ein Docker-Compose-Projekt startet alles:

| Dienst | Aufgabe |
| --- | --- |
| `db` | PostgreSQL 17 mit getrennten App-/Feed-Rollen |
| `migrate` | einmalige Schema- und Bootstrap-Migration |
| `web` | Gunicorn/Django hinter Loopback-Port |
| `feed-worker` | periodischer Abruf freigegebener HTTPS-Quellen |
| `backup` | taegliche lokale PostgreSQL-Dumps |

Authentifizierung laeuft ausschliesslich ueber lokale Django-Konten. TLS und
Netzfreigabe liegen beim Reverse-Proxy vor dem Container. Die Oberflaeche kann
ueber den Browser als App installiert werden; Schreibvorgänge brauchen weiterhin
eine aktive Verbindung.

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

Danach ist die oeffentliche Startseite unter `http://127.0.0.1:8090/` und die
Anmeldung unter `/anmelden/` erreichbar. Die Fachfunktionen (Uebersicht,
Uebergaben usw.) stehen erst nach Login mit aktiver Mitgliedschaft bereit. Der
Port bindet absichtlich nur an Loopback. `SECURE_COOKIES=false` ist
ausschliesslich fuer diesen lokalen HTTP-Schnellstart vorgesehen.

Weitere Teamkonten legt der **Master-Admin** unter `/team/anlegen/` an und gibt sie
sofort der Wache frei. Optional kann `REGISTRATION_ENABLED=true` eine oeffentliche
Kontoanfrage erlauben; Freigabe bleibt beim Master-Admin unter `/team/`.
Technische Systemkonten bleiben unter `/django-admin/`. `createsuperuser` erzeugt
einen globalen technischen Administrator; die stationsbezogene Master-Admin-Rolle
allein vergibt keine Django-Superuser-Rechte.

Tests:

```bash
docker compose exec web python manage.py test --settings=config.test_settings
```

## Reverse-Proxy mit TLS

Fuer Handys oder gemeinsame Wachenterminals steht vor dem Loopback-Port ein
Reverse-Proxy mit TLS. In `.env` dann mindestens:

```dotenv
SECURE_COOKIES=true
ALLOWED_HOSTS=wache.example.org
CSRF_TRUSTED_ORIGINS=https://wache.example.org
```

Der Proxy leitet auf `127.0.0.1:8090` weiter und setzt `X-Forwarded-Proto=https`.
Details stehen in [`docs/OPERATIONS.md`](docs/OPERATIONS.md).

## Administration

Stations-Master-Admins koennen unter `/einstellungen/` den Namen der Wache und
die sichtbaren Module selbst festlegen. Unter `/team/` legen sie Nutzer an und
verwalten Freigaben sowie Rollen. Technische Administratoren konfigurieren unter
`/django-admin/` Systemkonten und externe Quellen. Fachliche Datensaetze sind
dort bewusst nur lesbar, damit Versionierung und Audit nicht umgangen werden.

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
- [API fuer Mobile-/Drittclients](docs/API.md)
- [AGPL-Client iOS/Android](docs/CLIENT.md)
- [Betrieb, Backup und Updates](docs/OPERATIONS.md)
- [Datenschutz und Sicherheit](docs/SECURITY-PRIVACY.md)
- [Compliance: DSGVO, Cookies, AI Act, NRW](docs/COMPLIANCE.md)
- [Test- und Go-live-Checkliste](docs/GO-LIVE-CHECKLIST.md)
- [Recherche und Quellen](docs/RESEARCH.md)
- [Audit und Folgeplan](docs/AUDIT-2026-07.md)
- [Wandbausteine Tagesaufgaben](docs/WALL-BLOCKS.md)
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
