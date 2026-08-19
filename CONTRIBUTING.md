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

Fuer reproduzierbare CI-Qualitaetswerkzeuge gilt derselbe Fail-Closed-Grundsatz:
`requirements-ci.in` beschreibt die direkten Werkzeuge, `requirements-ci.lock`
enthaelt deren aufgeloeste Versionen und SHA256-Hashes. Der erste Ruff-Gate-
Schritt prueft die fehlerkritischen Regeln E4/E7/E9; die vollstaendige
Formatpruefung und eine breitere Regelmenge bleiben wegen des bestehenden
Altbestands bewusst ein separater Folge-Schritt.

```bash
uv pip compile --generate-hashes --python-version 3.13 \
  requirements-ci.in --output-file requirements-ci.lock
pip install --require-hashes -r requirements.lock -r requirements-ci.lock
ruff check config core --select E4,E7,E9 --output-format=concise
```

Die CI verweigert die Installation, wenn ein Paket oder Hash in der Lock-Datei
fehlt oder nicht zum heruntergeladenen Artefakt passt. Bei jeder Aenderung an
`requirements.txt` die Lock-Datei neu erzeugen, die Hash-Verifikation lokal
pruefen und beide Dateien committen.

## Datenschutz

Issues, Tests, Screenshots und Commits duerfen keine personenbezogenen Daten,
Session-Cookies, `.env`-Inhalte, Datenbank-Dumps oder Tailnet-Details enthalten.
