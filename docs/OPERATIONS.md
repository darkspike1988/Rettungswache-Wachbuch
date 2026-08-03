# Betrieb

## Endpunkte

- Anwendung: `http://127.0.0.1:${HTTP_PORT:-8090}/` (oeffentliche Projektseite)
- Uebersicht (nach Login): `/uebersicht/`
- Healthcheck: `/healthz/` (JSON mit `status` und `version`)
- Datenschutz/Cookies: `/datenschutz/`
- Anmeldung: `/anmelden/` (optional TOTP unter `/anmelden/mfa/` und `/konto/mfa/`)
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
docker compose exec -T web python manage.py apply_retention
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
die Rolle. Gemeinschaftskonten sind nicht vorgesehen. Unter **Mehr → Zwei-Faktor
/ Passkeys** koennen TOTP und Passkeys eingerichtet werden. Mit
`MFA_REQUIRED=true` wird die Einrichtung nach dem Passwort-Login erzwungen.

Passkeys brauchen `WEBAUTHN_RP_ID` (Hostname) und `WEBAUTHN_ORIGIN` (z. B.
`https://wache.example`). Web-Push braucht `WEB_PUSH_ENABLED=true` sowie
VAPID-Schluessel (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`).

## Reverse-Proxy

TLS nach **BSI TR-02102-2**: bevorzugt TLS 1.3 mit AEAD (z. B. AES-256-GCM).
Details: [`CRYPTO-BSI.md`](CRYPTO-BSI.md).

Beispiel fuer Caddy vor dem Loopback-Port:

```caddy
wache.example.org {
        reverse_proxy 127.0.0.1:8090
}
```

Hostname und HTTPS-Origin muessen in `ALLOWED_HOSTS` und
`CSRF_TRUSTED_ORIGINS` stehen. Der Proxy sollte `X-Forwarded-Proto` setzen.
Fuer jeden TLS-Betrieb muss `SECURE_COOKIES=true` gesetzt sein.
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

### Rollenmodell (R-010, Least-Privilege)

Die Datenbank unterscheidet vier Rollen mit klar getrennten Aufgaben:

- `rwsth_owner` (entspricht `POSTGRES_USER`): ausschliesslich fuer Init,
  Migration, manuelle Restore-Skripte und die Passwortrotation. Wird im
  laufenden Betrieb von keinem dauerhaften Container benutzt.
- `rwsth_app` (entspricht `APP_DB_USER`): Web- und Migrationscontainer. Volle
  CRUD-Rechte auf das Schema, aber kein `UPDATE`/`DELETE` auf den
  append-only-Tabellen `core_coffeeentry`, `core_auditevent`,
  `core_handoverrevision` und `core_checklistcompletion`.
- `rwsth_feed` (entspricht `FEED_DB_USER`): ausschliesslich `FeedSource`-
  Status- und `FeedItem`-CRUD.
- `rwsth_backup` (entspricht `BACKUP_DB_USER`): ausschliesslich `SELECT` plus
  `pg_read_all_data`. Wird vom dauerhaften `backup`-Container fuer
  `pg_dump` benutzt. Kann weder `INSERT`, `UPDATE` noch `DELETE` auf
  Fach-Tabellen ausfuehren.

### Tagesbackup

Der `backup`-Container laeuft standardmaessig als PostgreSQL-UID/GID 70 und
nutzt die `rwsth_backup`-Rolle. Vor dem Start muss `./backups` fuer dieses
Konto schreibbar sein. Abweichende Images koennen `BACKUP_UID` und
`BACKUP_GID` in `.env` anpassen.

```bash
sudo chown 70:70 backups
```

`pg_dump` laeuft mit `--no-owner --no-acl --format custom`. Der lokale
Sieben-Tage-Ring bleibt im Container-Volume `backups/`.

### Offsite-Verschluesselung

Wenn `BACKUP_ENCRYPT_REMOTE=true` gesetzt ist, wird jeder Dump vor dem
Offsite-Upload symmetrisch mit GnuPG gegen `BACKUP_GPG_RECIPIENT`
(AES-256, Empfaenger-Fingerprint oder E-Mail) verschluesselt. Der Klartext
verlaesst den Container nie. `BACKUP_OFF_TARGET` akzeptiert `file://`-Ziele
und ist die einzige Stelle, an der das verschluesselte Artefakt abgelegt
wird. Eine leerer Wert fuehrt das lokale Backup weiter aus, unterdrueckt
aber den Offsite-Schritt.

```bash
# in .env
BACKUP_ENCRYPT_REMOTE=true
BACKUP_GPG_RECIPIENT=ops-backup@example.org
BACKUP_OFF_TARGET=file:///srv/wachbuch-offsite
```

### Restore-Test

Der Restore-Test benoetigt Owner-Rechte (`createdb`/`dropdb`) und wird daher
explizit mit `RESTORE_OWNER=1` und den Owner-Credentials gestartet. Der
dauerhafte `backup`-Container fuehrt ihn **nicht** automatisch aus.

```bash
sudo chown 70:70 backups
docker compose exec -T -e RESTORE_OWNER=1 \
    -e PGUSER=rwsth_owner -e PGPASSWORD="$POSTGRES_PASSWORD" \
    backup /bin/sh /backup/restore-test.sh
```

Der Restore-Test erstellt kurzzeitig `rwsth_restore_test`, spielt den
neuesten Dump ein, prueft Schluesseltabellen und entfernt die Testdatenbank
wieder. Mit der Backup-Rolle laesst sich stattdessen nur die Dump-Struktur
verifizieren (`pg_restore --list`) und ein Read-only-SELECT auf
`django_migrations`/`core_station` ausfuehren.

## Aufbewahrung (Retention)

- `RETENTION_FEED_DAYS` (Standard `90`): entfernt Feed-Eintraege, deren
  `last_seen_at` aelter ist. `0` deaktiviert die Feed-Loeschung.
- `RETENTION_AUDIT_DAYS` (Standard `0`): Audit-Purge bleibt absichtlich aus, bis
  organisatorische Fristen freigegeben sind. Nur mit Owner-Rechten und klarer
  Freigabe setzen.
- Kommando: `docker compose exec -T web python manage.py apply_retention`
  (z. B. taeglich per Host-Cron).

## Datenbank-Passwortrotation

App- und Feed-Rollenpasswoerter rotieren (Owner-Passwort bleibt unangetastet):

```bash
./scripts/rotate-db-passwords.sh
```

Das Skript setzt neue Zufallswerte in PostgreSQL und `.env`, startet `web` und
`feed-worker` neu. Anschliessend Healthcheck und Feed-Worker-Logs pruefen. Das
Owner-Passwort (`POSTGRES_PASSWORD`) nur mit Dump/Restore und Neuinitialisierung
rotieren.

## Krypto-Schluesselrotation (TOTP-Secrets)

Die TOTP-Geheimnisse liegen AES-256-GCM-verschluesselt in der Datenbank. Der
Master-Key stammt Vorgabe aus `HKDF(SECRET_KEY)`. Da eine `SECRET_KEY`-Rotation
damit alle Umschlaege unlesbar machen wuerde, kann der Master-Key unabhaengig
von `SECRET_KEY` konfiguriert und rotiert werden:

- `CRYPTO_MASTER_KEY` – 32 Byte hex-codiert (z. B. `openssl rand -hex 32`).
  Wenn gesetzt, ersetzt er die `HKDF(SECRET_KEY)`-Ableitung. Wenn nicht gesetzt,
  gilt das alte Verfahren (Rueckwaertskompatibilitaet).
- `CRYPTO_PREVIOUS_MASTER_KEY` – optionaler Fallback-Schluessel, der waehrend
  eines Rotationsfensters **zusätzlich** zum Entschluesseln akzeptiert wird.
  Er erlaubt das Betreiben der App mit dem neuen Key, waehrend noch alte
  Umschlaege in der Datenbank stehen.

### Rotationsablauf

```bash
# 0. Backup erstellen und App weiterhin mit dem ALTEN Key betreiben.

# 1. Den aktuell aktiven Master-Key als Hex anzeigen (fuer den Fallback):
docker compose exec -T web python manage.py rotate_crypto_key --show-current-key
#   -> <alter-key-hex>

# 2. Neuen Key erzeugen:
NEW_KEY=$(openssl rand -hex 32)

# 3. In .env eintragen (app danach neu starten):
#    CRYPTO_MASTER_KEY=$NEW_KEY
#    CRYPTO_PREVIOUS_MASTER_KEY=<alter-key-hex aus Schritt 1>

# 4. App neu starten, dann Re-Verschluesselung testen und ausfuehren:
docker compose up -d web
docker compose exec -T web python manage.py rotate_crypto_key --dry-run
docker compose exec -T web python manage.py rotate_crypto_key

# 5. Nach erfolgreicher Rotation CRYPTO_PREVIOUS_MASTER_KEY aus .env entfernen
#    und erneut neu starten. Healthcheck und TOTP-Anmeldung verifizieren.
```

`--dry-run` aendert nichts, zaehlt aber wie viele Datensaetze neu
verschluesselt wuerden. Waehrend des Rotationsfensters (Schritt 3–4) kann die
App sowohl alte als auch neue Umschlaege lesen, sodass TOTP-Anmeldungen nicht
ausfallen. Erst nach Entfernen von `CRYPTO_PREVIOUS_MASTER_KEY` (Schritt 5)
akzeptiert das System ausschliesslich den neuen Key.

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
