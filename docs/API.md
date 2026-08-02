# API für Mobile- und Drittclients

Stand: 2. August 2026 (Server ≥ **0.14.1**). Versionierte REST-API unter `/api/v1/` für den
AGPL-Client ([Wachbuch-Client](https://github.com/darkspike1988/Wachbuch-Client)),
angelehnt an Paperless-ngx und Nextcloud.

## Ziele

- selbst gehostete Clients ohne Browser-Session
- stabile Verträge unter `/api/v1/`
- **widerrufbare** App-Tokens (`wb_…`, Klartext nur einmal)
- stationsbezogene Rechte über die bestehende Mitgliedschaft
- deutsche Alias-Pfade neben englischen Ressourcen
- kein CSRF für Token-Auth (`Authorization`-Header)

## Authentifizierung

```http
Authorization: Token <geheim>
```

oder:

```http
Authorization: Bearer <geheim>
```

### Token erzeugen

1. Im Web unter **Mein Konto → App-Tokens** (`/konto/api/`) erzeugen und kopieren
2. Oder (ohne MFA am Konto) `POST /api/v1/token/` bzw. Alias `POST /api/v1/anmeldung/`:

```json
{ "username": "user@example.org", "password": "…", "label": "Android App" }
```

Antwort enthält `token` **einmal** sowie `expires_at` / `expires_in` (Standard: **90 Tage**).
Bei aktivem MFA muss der Weg über `/konto/api/` genutzt werden. Standard-Scopes
umfassen Lesen und Schreiben der Mobile-Ressourcen (Rollenregeln bleiben zusätzlich
serverseitig erzwungen). `/me/` und `/uebersicht/` brauchen `read:me`.

### Widerruf

Unter `/konto/api/` oder durch Deaktivieren des Tokens. **Passwortwechsel widerruft
alle aktiven App-Tokens** des Kontos automatisch.

## Endpunkte (v1)

| Methode | Pfad | Auth | Beschreibung |
| --- | --- | --- | --- |
| GET | `/api/v1/` | nein | Discovery |
| GET | `/api/v1/openapi.yaml` | nein | OpenAPI 3 Schema |
| POST | `/api/v1/token/` | nein | Token gegen Benutzer/Passwort |
| POST | `/api/v1/anmeldung/` | nein | Alias von `token/` |
| GET | `/api/v1/status/` | optional | Auth-/Mitgliedschaftsstatus |
| GET | `/api/v1/me/` | Token | Nutzer, Rolle, Station, Module |
| GET | `/api/v1/uebersicht/` | Token | Dashboard-Kurzfassung |
| GET/POST | `/api/v1/handovers/` | Token + Scope | Liste / Übergabe anlegen |
| GET | `/api/v1/handovers/<id>/` | Token + Scope | Detail |
| POST | `/api/v1/handovers/<id>/status/` | Token + Scope | Status (Schichtleitung/Admin) |
| GET/POST | `/api/v1/uebergaben/` … | Token + Scope | Deutsche Aliase zu `handovers/` |
| GET/POST | `/api/v1/kalender/` | Token + Scope | Termine (Modul) |
| GET/POST | `/api/v1/kaffeekasse/` | Token + Scope | Kasse lesen / buchen (Modul) |
| GET | `/api/v1/checklisten/` | Token + Scope | Checklisten (Modul) |
| POST | `/api/v1/checklisten/<id>/erledigt/` | Token + Scope | Abschluss (append-only) |

### Scopes

Standard-Tokens (Passwort-Austausch und `/konto/api/`):

`read:me`, `read:handovers`, `write:handovers`, `read:calendar`, `write:calendar`,
`read:coffee`, `write:coffee`, `read:checklists`, `write:checklists`

Zusätzlich gelten dieselben Rollen- und Modulschalter wie in der Web-UI
(z. B. Kasse nur Kassierer/Admin; deaktiviertes Modul → `404`).

## Mobile-Client

1. Discovery `GET /api/v1/`
2. Login `POST /api/v1/token/` oder vorgefertigtes App-Token
3. Profil `GET /api/v1/me/` bzw. Übersicht `GET /api/v1/uebersicht/`
4. Fachdaten über englische oder deutsche Pfade

Offizielle App: https://github.com/darkspike1988/Wachbuch-Client  
Spiegel: `clients/wachbuch-mobile/` – siehe [`CLIENT.md`](CLIENT.md)

## Nicht im API-Scope

- Patienten-/Einsatz-/Alarmdaten
- Klartext von E2EE-Chats oder Post
- Django-Admin oder Master-Admin-Sonderrechte über die API umgehen

## Betrieb

- TLS vor dem Loopback-Port (wie Web)
- Authorization-Header nicht loggen
- Rate-Limits für `/api/v1/token/` folgen dem Login-Schutz (Axes)
- `/healthz/` bleibt ausserhalb der Produkt-API

Siehe auch [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md),
[`ASVS-L2.md`](ASVS-L2.md).
