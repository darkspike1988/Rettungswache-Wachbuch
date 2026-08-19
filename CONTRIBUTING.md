# Mitwirken

## Entwicklung

1. Einen Fork oder Branch anlegen.
2. Keine echten Wach-, Mitarbeiter-, Einsatz- oder Zugangsdaten verwenden.
3. Aenderungen klein halten und durch Tests absichern.
4. Vor dem Pull Request Tests und Docker-Build ausfuehren.

```bash
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

`requirements.txt` fuehrt die direkten Produktionsabhaengigkeiten.
`requirements.lock` enthaelt die aufgeloesten direkten und transitiven
Abhaengigkeiten mit SHA256-Hashes und ist der Installationsweg in CI:

```bash
./scripts/update-hashes.sh   # erzeugt requirements.lock via pip-compile --generate-hashes
pip install --require-hashes -r requirements.lock   # Installation mit Hash-Verifikation
```

Die CI verweigert die Installation, wenn ein Paket oder Hash in der Lock-Datei
fehlt oder nicht zum heruntergeladenen Artefakt passt. Bei jeder Aenderung an
`requirements.txt` die Lock-Datei neu erzeugen, die Hash-Verifikation lokal
pruefen und beide Dateien committen.

## Datenschutz

Issues, Tests, Screenshots und Commits duerfen keine personenbezogenen Daten,
Session-Cookies, `.env`-Inhalte, Datenbank-Dumps oder Tailnet-Details enthalten.
