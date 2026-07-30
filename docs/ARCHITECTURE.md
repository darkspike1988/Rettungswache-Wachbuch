# Architektur

## Ueberblick

Das Wachbuch ist ein modularer Monolith aus Django und PostgreSQL. Webprozess,
Feed-Worker, Migrationen und Backup verwenden dasselbe Image bzw. Repository,
aber getrennte Container und Datenbankrollen.

```text
Browser
  |
TLS-Reverse-Proxy
  |
127.0.0.1:8090
  |
Django/Gunicorn -------- Feed-Worker -------- freigegebene HTTPS-Quellen
  |                            |
  +--------- PostgreSQL ------+
```

## Container

| Dienst | Image / Rolle |
| --- | --- |
| `db` | PostgreSQL 17, interne Netze, Init fuer App-/Feed-Rollen |
| `migrate` | einmalig, Owner-Rechte, Schema und Bootstrap |
| `web` | Gunicorn, eingeschraenktes App-DB-Konto, Loopback-Port |
| `feed-worker` | Sync-Kommando, Feed-DB-Konto, nur Egress-Netz |
| `backup` | Dump-Schleife und Restore-Test gegen Owner-Konto |

Das Anwendungsimage ist read-only, laeuft als Non-root-Benutzer `app`, droppt
Capabilities und besitzt einen eingebauten Healthcheck.

## Vertrauensgrenzen

- Docker bindet den Webport standardmaessig nur an Host-Loopback.
- Authentifizierung erfolgt ausschliesslich ueber lokale Django-Konten mit
  Passwort und Login-Drosselung. Es gibt keinen Header-basierten Auto-Login.
- Web, Feed-Worker und Backup erreichen PostgreSQL ueber getrennte interne
  Netze. Der Worker hat keinen TCP-Pfad zum Webcontainer.
- Ein kurzlebiger `migrate`-Container besitzt die Datenbank-Owner-Rechte. Der
  dauerhafte Webprozess kennt ausschliesslich das eingeschraenkte App-Konto.
- Die Datenbank verhindert Updates und Loeschungen an Audit-Ereignissen,
  Kassenbuchungen und Uebergaberevisionen auch unterhalb der Anwendungsschicht.
- Feed-Hosts brauchen eine explizite Allowlist. Private Ziel-IP-Adressen,
  Redirects, andere Ports und uebergrosse Antworten werden abgewiesen.

## Datenmodell

- `Station`, `Membership`: Wachen, Modulschalter, Rollen und Freigaben
- `HandoverEntry`, `HandoverRevision`: Arbeitsstand und unveraenderte Revisionen
- `CalendarEvent`: Wachen-, kein Dienstplankalender
- `BirthdayPreference`: freiwillig, nur Tag und Monat
- `CoffeeEntry`: append-only Buchungen in Cent und Korrekturbezug
- `FeedSource`, `FeedItem`: optionale externe Meldungen
- `AuditEvent`: Akteur, Aktion, Objekt und Zeitpunkt ohne Freitextkopien

## Authentifizierung

Django authentifiziert lokale Benutzer. Der Befehl `grant_station_admin`
verbindet einen bestehenden Benutzer mit der Standardwache als Admin.
Weitere Konten werden unter `/django-admin/` angelegt und unter `/team/`
freigegeben. Gemeinschaftskonten sind nicht vorgesehen.

## Wiederherstellung

Der Backup-Container schreibt taeglich PostgreSQL-Custom-Dumps in `./backups`
und behaelt sieben Tage. Das Verzeichnis gehoert nicht zum Docker-Build und wird
nicht von Git erfasst. Ein Restore-Test laeuft mit:

```bash
docker compose exec -T backup /bin/sh /backup/restore-test.sh
```

Lokale Dumps sind kein Offsite-Backup. Betreiber muessen Verschluesselung,
externes Ziel, RPO, RTO und regelmaessige Restore-Tests selbst festlegen.
