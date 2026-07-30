# Betrieb

## Endpunkte

- Anwendung: `http://127.0.0.1:${HTTP_PORT:-8090}`
- Healthcheck: `/healthz/`
- Anmeldung: `/anmelden/`
- Stationsverwaltung: `/einstellungen/`
- technische Verwaltung: `/django-admin/`

Der Standard-Port ist nicht oeffentlich gebunden. `HTTP_BIND_ADDRESS=0.0.0.0`
sollte nur in einem kontrollierten Netz und nie zusammen mit ungeprueftem
Vertrauen in Proxy-Identitaetsheader verwendet werden. Fuer jeden TLS-Betrieb
muss `SECURE_COOKIES=true` gesetzt sein; `false` ist nur fuer lokalen HTTP-Zugriff
ueber Loopback vorgesehen.

## Standardbefehle

```bash
docker compose ps
docker compose logs --since 30m web migrate feed-worker backup
docker compose up -d --build
docker compose exec -T web python manage.py test --settings=config.test_settings
curl -fsS http://127.0.0.1:8090/healthz/
```

## Benutzer und Rollen

Lokaler Erstadmin:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py grant_station_admin BENUTZERNAME
```

Bei Tailscale-Anmeldung wird beim ersten Aufruf ein Konto angelegt. Nur der mit
`TAILSCALE_ADMIN_LOGIN` konfigurierte Login erhaelt automatisch die
stationsbezogene Adminrolle, aber keine globalen Django-Superuser-Rechte.
Andere Konten muessen unter `/team/` freigegeben werden. Gemeinschaftskonten
sind nicht vorgesehen.

## Tailscale Serve

Ein Beispiel fuer einen lokalen HTTP-Port 8090:

```bash
tailscale serve --bg --https=18090 http://127.0.0.1:8090
tailscale serve status
```

Hostname und HTTPS-Port muessen in `ALLOWED_HOSTS` und
`CSRF_TRUSTED_ORIGINS` abgebildet sein. Header-Vertrauen ist nur fuer diesen
geschuetzten Einstieg zu aktivieren.

## Feeds

Der Worker aktualisiert aktivierte Quellen alle 15 Minuten. Ein manueller Lauf:

```bash
docker compose exec -T feed-worker python manage.py sync_feeds
```

Neue Hosts werden zuerst in `FEED_ALLOWED_HOSTS` freigegeben. Quellen koennen
danach im Django-Admin erstellt, deaktiviert oder korrigiert werden. Fehler und
der letzte erfolgreiche Abruf stehen direkt am `FeedSource`.

Vor dem Upgrade einer 0.2-Installation muessen die Hosts aller bestehenden
Quellen aus dem Django-Admin in `FEED_ALLOWED_HOSTS` uebernommen werden. Eine
leere Allowlist deaktiviert Abrufe absichtlich.

## Backup und Restore

Der Backup-Container laeuft standardmaessig als PostgreSQL-UID/GID 70. Vor dem
Start muss `./backups` fuer dieses Konto schreibbar sein. Abweichende Images
koennen `BACKUP_UID` und `BACKUP_GID` in `.env` anpassen.

```bash
sudo chown 70:70 backups
docker compose exec -T backup /bin/sh /backup/restore-test.sh
```

Der Restore-Test erstellt kurzzeitig `rwsth_restore_test`, spielt den neuesten
Dump ein, prueft Schluesseltabellen und entfernt die Testdatenbank wieder.

## Updateablauf

1. Backup und Restore-Test ausfuehren.
2. Abhaengigkeiten und Image-Digests kontrolliert aktualisieren.
3. `docker compose build --no-cache` ausfuehren.
4. Images auf HIGH/CRITICAL-Schwachstellen scannen.
5. Tests ausfuehren und danach `docker compose up -d` starten.
6. Healthcheck, Anmeldung, Rollen und optionale Feeds pruefen.

Bei Stoerungen keine Tabellen manuell bearbeiten. Zuerst Logs und letzten Dump
sichern, dann die Ursache reproduzierbar ueber Anwendung oder Migration beheben.

## Loeschfristen ausfuehren

Die Fristen stehen je Wache unter `/wache/einstellungen/`; geloescht wird nur, wenn
der Betrieb den Befehl anstoesst. Er laeuft im `migrate`-Container, weil das
Anwendungskonto Audit-Ereignisse und Revisionen auf Datenbankebene nicht
loeschen darf:

```bash
docker compose run --rm migrate python manage.py purge_expired --dry-run
docker compose run --rm migrate python manage.py purge_expired
```

Der Lauf schreibt je Wache ein Audit-Ereignis `retention.purged` mit den
Stueckzahlen. Kassenbuchungen bleiben ausgenommen. `retention_task_days`
entfernt abgehakte Aufgabentage samt Ergebnissen - in ihnen steht, wer wann was
erledigt hat. Die Aufgabenlisten selbst und ihre Punkte bleiben erhalten, sie
enthalten keinen Personenbezug.

Im Normalbetrieb uebernimmt das der `maintenance`-Container, der den Befehl
standardmaessig einmal taeglich ausfuehrt (`MAINTENANCE_INTERVAL_SECONDS` in
`.env`). Der manuelle Aufruf oben bleibt fuer Probelaeufe sinnvoll.

## Passwort-Reset

Ohne `EMAIL_HOST` in `.env` schreibt Django Nachrichten nur in das
Containerlog. Fuer den Betrieb werden `EMAIL_HOST`, `EMAIL_PORT`,
`EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` und `DEFAULT_FROM_EMAIL` gesetzt und
der Ablauf einmal mit einem echten Postfach getestet. Konten ohne
E-Mail-Adresse koennen den Reset nicht nutzen; `/team/` markiert sie.
