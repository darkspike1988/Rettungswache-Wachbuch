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

`requirements.txt` enthaelt die gepinnten Top-Level-Pakete. Zusaetzlich gibt es
`requirements.lock`, einen mit Integritaets-Hashes (SHA256) angereicherten
Lockfile fuer alle Pakete inklusive transitiver Abhaengigkeiten.

### Hashes aktualisieren

Nach jeder Aenderung an `requirements.txt` (oder regelmaessig fuer Updates) den
Lockfile neu erzeugen und committen:

```bash
pip install pip-tools
./scripts/update-hashes.sh
git diff requirements.lock    # Review der neuen/entfernten Pakete und Hashes
git add requirements.lock
```

`scripts/update-hashes.sh` ruft `pip-compile --generate-hashes` auf und
ueberschreibt `requirements.lock`. Solange der Lockfile nur den Header-Kommentar
und keine `--hash`-Zeilen enthaelt, ist der Hash-Check in CI deaktiviert. Sobald
echte Eintraege vorhanden sind, prueft CI
`pip install --require-hashes -r requirements.lock` und schlaegt fehl, wenn die
hinterlegten Versionen/Hashes nicht zum Wheel auf PyPI passen. Damit werden
unkontrollierte Aenderungen an transitiven Abhaengigkeiten sichtbar.

`.gitignore` nicht anpassen – `requirements.lock` wird versioniert.

## Datenschutz

Issues, Tests, Screenshots und Commits duerfen keine personenbezogenen Daten,
Session-Cookies, `.env`-Inhalte, Datenbank-Dumps oder Tailnet-Details enthalten.
