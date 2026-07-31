# AGPL-Client (iOS / Android)

Stand: 31. Juli 2026.

## Zweites Repository

| | |
| --- | --- |
| **Server** | https://github.com/darkspike1988/Rettungswache-Wachbuch |
| **Client (Ziel)** | https://github.com/darkspike1988/Wachbuch-Mobile |
| **Quellpfad bis zum Split** | `clients/wachbuch-mobile/` im Server-Repo |
| **Publish** | `./scripts/publish-mobile-client-repo.sh` |

Cloud-Agents dürfen auf GitHub **keine** Repos anlegen. Einmalig manuell:

1. https://github.com/new → Name `Wachbuch-Mobile`, Owner `darkspike1988`, Public
2. `./scripts/publish-mobile-client-repo.sh` im Server-Repo ausführen
3. Issues/PRs für die App danach im Client-Repo

Der Client-Quellcode ist bereits **standalone** (eigene `LICENSE`, CI, CONTRIBUTING).

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

Header: `Authorization: Token <wb_…>`

## Wachenspezifisch

- Mitgliedschaft nur auf dem Server
- App liest `membership.station` aus `/me/`
- Kein Multi-Wachen-Switcher in v0.1

## MFA

Bei MFA: App-Token im Web unter `/konto/api/` erzeugen und in der App einfügen.

## Vorbilder auf GitHub (Ideen)

| Projekt | Übernehmen | Nicht übernehmen |
| --- | --- | --- |
| paperless-go (AGPL, Flutter) | Self-host URL, Token, Secure Storage | Dokument-Scan |
| Paperless_ngx_uploader (GPL) | schlanker Zweck-Client | Upload-only |
| Nextcloud App-Passwords | Server zuerst, Token statt Cookie | Files-App-SSO |

Kein Fremdcode 1:1 kopiert.

## Android-APK

- Bau: `clients/wachbuch-mobile/scripts/build-apk.sh` → `dist/wachbuch-mobile.apk`
- Install: [clients/wachbuch-mobile/docs/INSTALL-ANDROID.md](../clients/wachbuch-mobile/docs/INSTALL-ANDROID.md)
- Play-Vorbereitung: [PLAY-STORE.md](../clients/wachbuch-mobile/docs/PLAY-STORE.md) (Target API 36, Kamera nur QR, kein Cleartext in Release)
- Startflow: Server-Adresse/QR → Bestätigen → Login (Benutzername/Passwort)
- Package-ID: `de.wachbuch.mobile` (minSdk 24)
- Layout: Phone Bottom-Nav, Tablet NavigationRail / Grid
- Web: QR unter `/konto/api/` für den Scan

## Lizenz

AGPL-3.0-or-later in Client-`LICENSE` und Server-Root-`LICENSE`.
