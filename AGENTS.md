# AGENTS.md

## Cursor Cloud specific instructions

This repository (`Rettungswache-Wachbuch`) is the complete product: a Django 5.2
server-rendered "Wachbuch" (station logbook) for a Rettungswache. The sibling
repo `Wachbuch-Client` is currently an empty placeholder (only a `README.md`) and
has nothing to install, build, or run.

### Environment / dependencies

- Dependencies are managed with `pip` and pinned in `requirements.txt` (no lockfile).
- The startup update script creates a virtualenv at `.venv/` and installs
  `requirements.txt`. It relies on the `python3-venv` system package (installed
  during environment setup); if `python3 -m venv` ever fails with an `ensurepip`
  error, run `sudo apt-get install -y python3.12-venv`.
- Always use the venv interpreter: `.venv/bin/python`.

### Database configuration (non-obvious)

`config/settings.py` selects the database by env var precedence: `DATABASE_URL` >
discrete `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD` > **SQLite fallback** (`db.sqlite3`).
So for local development you can run everything on SQLite by simply not setting
those DB vars. The Docker Compose stack uses PostgreSQL, but Docker is not required
(and is not installed) for local dev or tests.

### Secret key / DEBUG (non-obvious)

`DJANGO_SECRET_KEY` is **required only when `DJANGO_DEBUG` is false**. For local dev
run with `DJANGO_DEBUG=true`, which also flips `SECURE_COOKIES` off so cookies work
over plain HTTP. The test settings module supplies its own behavior; CI passes
`DJANGO_SECRET_KEY=ci-only-secret` with `DJANGO_DEBUG=false`.

### Lint / test / run (local dev, SQLite)

- Migration check (used as lint in CI):
  `DJANGO_SECRET_KEY=ci-only-secret DJANGO_DEBUG=false .venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings`
- Tests (SQLite, WhiteNoise disabled via test settings):
  `DJANGO_SECRET_KEY=ci-only-secret DJANGO_DEBUG=false .venv/bin/python manage.py test --settings=config.test_settings`
- First-time run setup (creates SQLite DB + default station + admin):
  - `DJANGO_DEBUG=true .venv/bin/python manage.py migrate`
  - `DJANGO_DEBUG=true .venv/bin/python manage.py bootstrap_project`
  - `DJANGO_DEBUG=true DJANGO_SUPERUSER_PASSWORD='...' .venv/bin/python manage.py createsuperuser --noinput --username admin --email admin@example.org`
  - `DJANGO_DEBUG=true .venv/bin/python manage.py grant_station_admin admin`
    (a global superuser still needs a station Membership to see the app UI)
- Dev server: `DJANGO_DEBUG=true .venv/bin/python manage.py runserver 127.0.0.1:8090`
  - Login page: `/anmelden/`, health: `/healthz/`, Django admin: `/django-admin/`.
  - Core UI routes are German, e.g. `/uebergaben/` (handovers), `/kaffeekasse/`,
    `/kalender/`, `/team/`, `/einstellungen/`.

### Full Docker stack (optional, not used in this environment)

`docker compose up --build -d` runs the production-like stack (Postgres + gunicorn
web + migrate job + optional feed-worker + backup). It requires a filled `.env`
(copy from `.env.example`) and `sudo chown 70:70 backups`. Docker is not installed
here; prefer the local SQLite dev flow above for development and testing.
