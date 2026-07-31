# Betrieb

## Endpunkte

- Anwendung: `http://127.0.0.1:${HTTP_PORT:-8090}`
- Healthcheck: `/healthz/` (JSON mit `status` und `version`)
- Datenschutz/Cookies: `/datenschutz/`
- Anmeldung: `/anmelden/`
- Stationsverwaltung: `/einstellungen/`
- Teamfreigaben: `/team/`
- technische Verwaltung: `/django-admin/`

Der Standard-Port ist nicht oeffentlich gebunden. `HTTP_BIND_ADDRESS=0.0.0.0`
sollte nur in einem kontrollierten Netz hinter einem Reverse-Proxy verwendet
werden. Fuer jeden TLS-Betrieb muss `SECURE_COOKIES=true` gesetzt sein; `false`
ist nur fuer lokalen HTTP-Zugriff ueber Loopback vorgesehen.

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

Weitere persoenliche Konten werden unter `/django-admin/auth/user/` angelegt.
Stationsadministratoren geben sie anschliessend unter `/team/` frei und setzen
die Rolle. Gemeinschaftskonten sind nicht vorgesehen.

## Reverse-Proxy

Beispiel fuer Caddy vor dem Loopback-Port:

```caddy
wache.example.org {
        reverse_proxy 127.0.0.1:8090
}
```

Hostname und HTTPS-Origin muessen in `ALLOWED_HOSTS` und
`CSRF_TRUSTED_ORIGINS` stehen. Der Proxy sollte `X-Forwarded-Proto` setzen.
Django wertet `SECURE_PROXY_SSL_HEADER` aus und erzwingt sichere Cookies, wenn
`SECURE_COOKIES=true` gesetzt ist.

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

## Versionierung und Updates

Canonical Version steht in `core/version.py` und kann mit `APP_VERSION` in `.env`
ueberschrieben werden. Die Version erscheint im Footer und unter `/healthz/`.

### Release vorbereiten

1. SemVer in `core/version.py` setzen und `CHANGELOG.md` aktualisieren.
2. Migrationshinweise und Breaking Changes dokumentieren.
3. Backup und Restore-Test ausfuehren.
4. Abhaengigkeiten und Image-Digests kontrolliert aktualisieren.
5. `docker compose build --no-cache` ausfuehren.
6. Images auf HIGH/CRITICAL-Schwachstellen scannen.
7. Tests ausfuehren und danach `docker compose up -d` starten.
8. Healthcheck inkl. Versionsfeld, Anmeldung, Rollen, Tagesaufgaben und optionale
   Feeds pruefen.
9. Service-Worker-Caches leeren bzw. einmal ab-/anmelden, falls Shell-Assets
   geaendert wurden.

### Rollback

1. Vorheriges Image-Tag bzw. Compose-Revision wieder aktivieren.
2. Bei scheiternder Migration nur dokumentierte Reverse-Migrationen oder
   Dump-Restore nutzen.
3. Keine Tabellen manuell „reparieren“.
4. Incident, Root Cause und erneuten Release-Versuch dokumentieren.

Bei Stoerungen zuerst Logs und letzten Dump sichern, dann die Ursache
reproduzierbar ueber Anwendung oder Migration beheben.

Siehe auch [`COMPLIANCE.md`](COMPLIANCE.md).
