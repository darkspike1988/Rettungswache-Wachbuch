# AGPL-Client (iOS / Android)

Stand: 31. Juli 2026.

## Zwei Repositories (aufeinander abgestimmt)

| | |
| --- | --- |
| **Server** | https://github.com/darkspike1988/Rettungswache-Wachbuch (≥ **0.14.0**) |
| **Client** | https://github.com/darkspike1988/Wachbuch-Client (App **0.2.x**) |
| **Spiegel im Server** | `clients/wachbuch-mobile/` |
| **Push Server → Client** | `./scripts/publish-mobile-client-repo.sh` |
| **Pull Client → Server** | `./scripts/pull-mobile-client-repo.sh` |

Canonical für die App-Entwicklung ist **Wachbuch-Client**. Der Ordner
`clients/wachbuch-mobile/` bleibt als Spiegel für Docs/CI im Server-Repo.

### Cursor / GitHub-App

Schreibzugriff auf `Wachbuch-Client` freigeben:

https://github.com/settings/installations → Cursor → Configure → Repo hinzufügen

## Kopplung

```text
App                      Wachbuch-Server
─────────────────────    ────────────────────────────
1. Adresse oder QR
   └─ Bestätigen         GET  /api/v1/          Discovery
2. Login User/Passwort   POST /api/v1/token/    (Alias: /anmeldung/)
                         oder App-Token unter /konto/api/
3. Sitzung               GET  /api/v1/me/       User + eine Station
                         GET  /api/v1/uebersicht/
4. Fachdaten             /handovers/ oder /uebergaben/,
                         /kalender/, /kaffeekasse/, /checklisten/
```

Header: `Authorization: Token <wb_…>` (widerrufbar)

## Wachenspezifisch

- Mitgliedschaft nur auf dem Server
- App liest `membership.station` aus `/me/`
- Kein Multi-Wachen-Switcher

## MFA

App-Token im Web unter `/konto/api/` (QR der Server-Adresse dort ebenfalls).

## Android / Play

- Package `de.wachbuch.mobile`, minSdk 24, targetSdk 36
- Start: Adresse/QR → Login
- [INSTALL-ANDROID.md](../clients/wachbuch-mobile/docs/INSTALL-ANDROID.md)
- [PLAY-STORE.md](../clients/wachbuch-mobile/docs/PLAY-STORE.md)
- Client: [SERVER.md](../clients/wachbuch-mobile/docs/SERVER.md)

## Vorbilder (Ideen)

| Projekt | Übernehmen |
| --- | --- |
| paperless-go | Self-host URL, Token, Secure Storage |
| Nextcloud | Server zuerst, dann Login |

## Lizenz

AGPL-3.0-or-later in beiden Repos.
