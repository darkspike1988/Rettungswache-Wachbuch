# Mitwirken

## Entwicklung

1. Einen Fork oder Branch anlegen.
2. Keine echten Wach-, Mitarbeiter-, Einsatz- oder Zugangsdaten verwenden.
3. Aenderungen klein halten und durch Tests absichern.
4. Vor dem Pull Request Lint, Tests und Docker-Build ausfuehren.

```bash
uvx --from ruff==0.16.1 ruff check .
docker compose build web
docker compose run --rm --no-deps \
  -e DJANGO_SECRET_KEY=test-only \
  -e DJANGO_DEBUG=false \
  -e DATABASE_URL=sqlite:////tmp/test.sqlite3 \
  web python manage.py test --settings=config.test_settings
```

### Mobile-Client (AGPL)

```bash
cd clients/wachbuch-mobile
flutter pub get
flutter test
flutter analyze
```

Der Client spricht nur `/api/v1/` an; siehe [`docs/CLIENT.md`](docs/CLIENT.md).

Pull Requests sollen Zweck, Verhaltensaenderung, Tests und moegliche
Datenschutz- oder Migrationsfolgen beschreiben. Neue Abhaengigkeiten brauchen
eine Begruendung und kompatible Lizenz (Server und Client: AGPL-kompatibel).

## Abhaengigkeiten und Hashes

`requirements.txt` fuehrt die Produktionsabhaengigkeiten. Fuer
Supply-Chain-Sicherheit ist die vollstaendige Lock-Datei mit SHA256-Hashes
verbindlich:

```bash
./scripts/update-hashes.sh   # erzeugt requirements.lock via pip-compile --generate-hashes
pip install --require-hashes -r requirements.lock   # Installation mit Hash-Verifikation
```

Die CI installiert ausschliesslich mit `--require-hashes`. Eine fehlende oder
unvollstaendige Lock-Datei bricht den Build ab. Bei jeder Aenderung an
`requirements.txt` die Lock-Datei neu erzeugen und committen.

## Datenschutz

Issues, Tests, Screenshots und Commits duerfen keine personenbezogenen Daten,
Session-Cookies, `.env`-Inhalte, Datenbank-Dumps oder Tailnet-Details enthalten.
