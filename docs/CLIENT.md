# AGPL-Client (iOS / Android)

Stand: 31. Juli 2026.

Der offizielle Begleit-Client liegt unter [`clients/wachbuch-mobile/`](../clients/wachbuch-mobile/)
(Flutter, **AGPL-3.0-or-later**).

## Vorbilder auf GitHub (Ideen)

| Projekt | Was wir übernehmen | Was wir nicht übernehmen |
| --- | --- | --- |
| [paperless-go](https://github.com/bearyjd/paperless-go) (AGPL, Flutter) | Self-host URL, Token, Secure Storage, FOSS-Stores | Dokument-Scan/OCR (fachlich anders) |
| [Paperless_ngx_uploader](https://github.com/gmag11/Paperless_ngx_uploader) (GPL) | schlanker Zweck-Client, Share-Intent-Idee spaeter | Upload-only Fokus |
| Nextcloud Login Flow / App-Passwords | Server zuerst, Token statt Session-Cookie | SSO ueber Files-App (optional spaeter) |
| Verwaiste Paperless-Mobile-Apps | Warnung: Community-Apps brauchen Pflege | proprietäre Clients ohne Quellcode |

Kein Fremdcode wurde 1:1 kopiert; nur Architektur- und UX-Muster.

## Kopplung an den Server

```text
App                      Wachbuch-Server
─────────────────────    ────────────────────────────
Server-URL
   │
   ├─ GET  /api/v1/              Discovery
   ├─ POST /api/v1/token/        Login → Token  (oder Token aus /konto/api/)
   ├─ GET  /api/v1/me/           User + **eine Station** + Module
   └─ GET  /api/v1/handovers/    Fachdaten der Wache
```

Header nach Login:

```http
Authorization: Token <wb_…>
```

## Wachenspezifisch

- Mitgliedschaft liegt **nur** auf dem Server (`unique_active_membership`).
- Die App liest `membership.station` aus `/me/` und blendet Module ein/aus.
- Kein Multi-Wachen-Switcher in v0.1; Wechsel = anderes Konto / neue Freigabe.

## MFA

Wenn das Konto MFA hat, lehnt `/api/v1/token/` ab (`mfa_required`). Die App
bietet dann **App-Token einfuegen** an (aus dem Web unter `/konto/api/`) – analog
Nextcloud-App-Passwort.

## Ausbau-Fahrplan Client

1. Lesen: Kalender, Aufgaben, Kasse (sobald API-Endpunkte wachsen)
2. Schreiben: Uebergaben anlegen/Status
3. E2EE: Chat/Privat/Post mit lokalem Schluesselmaterial
4. Optional: biometrische Entsperrung, F-Droid-Builds

## Lizenz

AGPL-3.0-or-later. Verteilung der App verpflichtet zur Quellcode-Offenlegung
unter AGPL. Details: Root-`LICENSE`, Client-`LICENSE`.
