# Architektur

## Ueberblick

Das Wachbuch ist ein modularer Monolith aus Django und PostgreSQL. Webprozess,
Feed-Worker, Migrationen und Backup verwenden dasselbe Repository, aber getrennte
Container und Datenbankrollen.

```text
Browser
  |
TLS-Reverse-Proxy oder Tailscale Serve
  |
127.0.0.1:8090
  |
Django/Gunicorn -------- Feed-Worker -------- freigegebene HTTPS-Quellen
  |                            |
  +--------- PostgreSQL ------+
```

## Vertrauensgrenzen

- Docker bindet den Webport standardmaessig nur an Host-Loopback.
- Tailscale-Identitaetsheader werden nur bei explizitem
  `TRUST_TAILSCALE_HEADERS=true` ausgewertet. In diesem Modus darf kein
  ungefilterter Client den Anwendungsport erreichen.
- Web, Feed-Worker und Backup erreichen PostgreSQL ueber getrennte interne
  Netze. Der Worker hat keinen TCP-Pfad zum Webcontainer.
- Ein kurzlebiger `migrate`-Container besitzt die Datenbank-Owner-Rechte. Der
  dauerhafte Webprozess kennt ausschliesslich das eingeschraenkte App-Konto.
- Die Datenbank verhindert Updates und Loeschungen an Audit-Ereignissen,
  Kassenbuchungen und Uebergaberevisionen auch unterhalb der Anwendungsschicht.
- Feed-Hosts brauchen eine explizite Allowlist. Private Ziel-IP-Adressen,
  Redirects, andere Ports und uebergrosse Antworten werden abgewiesen.

## Datenmodell

- `Station`, `Membership`: Wachen (Name, Standort, Adresse, Ort, Kreis),
  Modulschalter, Rollen und Freigaben. Eine Person kann mehreren Wachen
  angehoeren; welche gerade aktiv ist, steht in der Session und laesst sich
  unter `Mehr` wechseln. Alle Abfragen filtern auf die aktive Wache.
- `HandoverEntry`, `HandoverRevision`: Arbeitsstand, optionaler Tagesbezug (`for_date`)
  und unveraenderte Revisionen
- `DailyTeamNote`: Team je Tag fuer das Wochenprotokoll, eine Zeile je Wache und Datum
- `HandoverAcknowledgement`: Lesebestaetigung je Person und dringendem Eintrag
- `FeedSource`, `FeedItem`: optionale externe Quellen (RSS, Verkehr-CSV,
  Abfallkalender-ICS); global oder ueber `station` einer einzelnen Wache
  zugeordnet
- `CalendarEvent`: Wachen-, kein Dienstplankalender
- `BirthdayPreference`: freiwillig, nur Tag und Monat
- `CoffeeEntry`: append-only Buchungen in Cent und Korrekturbezug
- `TotpDevice`, `RecoveryCode`: zweiter Faktor je Person; Codes nur als Hash
- `AuditEvent`: Akteur, Aktion, Objekt und Zeitpunkt ohne Freitextkopien

## Authentifizierung

Im Standardmodus authentifiziert Django lokale Benutzer. Der Befehl
`grant_station_admin` verbindet einen Superuser mit einer Wache. Optional setzt
Tailscale Serve Identitaetsheader. Das konfigurierte Tailscale-Administratorkonto
wird beim ersten Zugriff der Standardwache zugeordnet; weitere Konten warten auf
eine Freigabe unter `/team/`.

## Wiederherstellung

Der Backup-Container schreibt taeglich PostgreSQL-Custom-Dumps in `./backups`
und behaelt sieben Tage. Das Verzeichnis gehoert nicht zum Docker-Build und wird
nicht von Git erfasst. Ein Restore-Test laeuft mit:

```bash
docker compose exec -T backup /bin/sh /backup/restore-test.sh
```

Lokale Dumps sind kein Offsite-Backup. Betreiber muessen Verschluesselung,
externes Ziel, RPO, RTO und regelmaessige Restore-Tests selbst festlegen.
