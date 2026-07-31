# API für Mobile- und Drittclients

Stand: 31. Juli 2026. Fundament für spätere **Open-Source-Apps** (iOS/Android),
angelehnt an Paperless-ngx und Nextcloud (Token-Auth, versionierte REST-Pfade,
OpenAPI).

## Ziele

- selbst gehostete Clients können sich ohne Browser-Session anbinden
- stabile, versionierte Verträge unter `/api/v1/`
- widerrufbare App-Tokens (Klartext nur einmal)
- stationsbezogene Rechte über die bestehende Mitgliedschaft
- kein CSRF für Token-Auth (Header `Authorization`)

## Authentifizierung

Wie bei Paperless:

```http
Authorization: Token <geheim>
```

Alternativ akzeptiert:

```http
Authorization: Bearer <geheim>
```

### Token erzeugen

1. Im Web unter **Mein Konto → App-Tokens** (`/konto/api/`) erzeugen und kopieren
2. Oder (ohne MFA am Konto) `POST /api/v1/token/` mit JSON:

```json
{ "username": "user@example.org", "password": "…", "label": "Android App" }
```

Antwort enthält `token` **einmal**. Bei aktivem MFA muss der Weg über `/konto/api/`
genutzt werden.

### Widerruf

Unter `/konto/api/` oder durch Deaktivieren des Tokens in der Datenbank.
Passwortwechsel widerruft Tokens derzeit **nicht** automatisch (kann später
nachgezogen werden).

## Endpunkte (v1)

| Methode | Pfad | Auth | Beschreibung |
| --- | --- | --- | --- |
| GET | `/api/v1/` | nein | Discovery |
| GET | `/api/v1/openapi.yaml` | nein | OpenAPI 3 Schema |
| POST | `/api/v1/token/` | nein | Token gegen Benutzer/Passwort |
| GET | `/api/v1/me/` | Token | Nutzer, Rolle, Station, Module |
| GET | `/api/v1/handovers/` | Token + Scope | Aktive Übergaben der Wache |

Scopes der Standard-Tokens: `read:me`, `read:handovers`.

## Mobile-Client-Fahrplan

Analog Nextcloud/Paperless:

1. **Foundation (jetzt):** Token, Discovery, `me`, lesende Übergaben, OpenAPI
2. **AGPL-Client:** https://github.com/darkspike1988/Wachbuch-Client  
   (Spiegel: `clients/wachbuch-mobile/` – siehe [`CLIENT.md`](CLIENT.md))
3. **Lesen:** Kalender, Tagesaufgaben, Kassenstand (ohne Zahlungsabwicklung)
4. **Schreiben:** Übergaben anlegen/Status – mit denselben Rollenregeln wie die Web-UI
5. **E2EE:** Chat/Privat/Post nur mit Client-seitiger Krypto (Keys bleiben lokal)
6. **Stores/F-Droid:** Release-Pipelines, sobald die API stabil genug ist

Offizielle AGPL-Apps leben im Monorepo unter `clients/`; der Server bleibt Quelle der Wahrheit.

## Nicht im API-Scope

- Patienten-/Einsatz-/Alarmdaten
- Klartext von E2EE-Chats oder Post
- Django-Admin oder Master-Admin-Sonderrechte über die API umgehen

## Betrieb

- TLS vor dem Loopback-Port (wie Web)
- Authorization-Header nicht loggen
- Rate-Limits für `/api/v1/token/` folgen dem Login-Schutz (Axes); weitere
  API-Limits können ergänzt werden
- `/healthz/` bleibt ausserhalb der Produkt-API

Siehe auch [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md),
[`ASVS-L2.md`](ASVS-L2.md).
