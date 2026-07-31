# AGENTS.md

## Cursor Cloud specific instructions

This repository (`Rettungswache-Wachbuch`) is the **Docker backend server**: a
Django 5.2 server-rendered "Wachbuch" (station logbook) for a Rettungswache,
deployed via Docker Compose (Postgres + gunicorn web + one-shot migrate job +
optional feed-worker + backup). The sibling repo `Wachbuch-Client` is intended to
become the **mobile client app (Android/iOS)** that talks to this server, but it is
currently an empty placeholder (only a `README.md`) with no app source code or
chosen framework yet — nothing to install, build, or run there. iOS builds are not
possible on this Linux VM (they require macOS/Xcode).

For pure application development and the test suite you can run Django locally on
SQLite (see below) without Docker. To run the actual server as it is deployed, use
the Docker stack (see "Docker server" below).

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

### Docker server (production-like backend stack)

The canonical way to run the server is Docker Compose. Non-obvious caveats in this
cloud VM:

- **dockerd must be started manually each session** (no systemd here):
  `sudo dockerd` (run it in a background tmux session; wait a few seconds).
- Docker Engine, `fuse-overlayfs`, `iptables-legacy`, and `/etc/docker/daemon.json`
  are already configured. Because Docker 29 defaults to the containerd snapshotter
  (which breaks fuse-overlayfs in this VM), `daemon.json` sets
  `"storage-driver": "fuse-overlayfs"` and `"features": {"containerd-snapshotter": false}`.
  If dockerd was reinstalled/reset, re-apply that config before starting it.
- `.env` is required: `cp .env.example .env` and replace every placeholder secret
  with a random value (e.g. `openssl rand -hex 32`). `.env` is gitignored.
- The `backup/` dir must be owned by the container postgres user: `sudo chown 70:70 backups`.
- Bring up the stack: `sudo docker compose up --build -d web` (this also starts
  `db` and runs the one-shot `migrate` job, which migrates + bootstraps the default
  station + grants restricted DB roles). App is served on `http://127.0.0.1:8090`
  (loopback only by design), health at `/healthz/`.
- Create the first admin inside the running web container (writes go to Postgres,
  so the read-only container filesystem is fine):
  - `sudo docker compose exec -e DJANGO_SUPERUSER_PASSWORD='...' web python manage.py createsuperuser --noinput --username admin --email admin@example.org`
  - `sudo docker compose exec web python manage.py grant_station_admin admin`
- The `web` container runs as the restricted `rwsth_app` DB role by design (e.g. it
  cannot UPDATE `core_auditevent`); verify with
  `sudo docker compose exec -T db psql -U rwsth_owner -d rwsth -tAc "SELECT has_table_privilege('rwsth_app','core_auditevent','UPDATE')"` → `f`.
- Port `8090` is shared with the local `runserver` dev flow; only run one at a time.
