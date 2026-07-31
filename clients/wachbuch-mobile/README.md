# Wachbuch Client (AGPL)

Open-Source-Begleit-App für selbst gehostetes
**[Wachbuch](https://github.com/darkspike1988/Rettungswache-Wachbuch)** (iOS & Android).

| | |
| --- | --- |
| **Dieses Repo** | https://github.com/darkspike1988/Wachbuch-Client |
| **Server** | https://github.com/darkspike1988/Rettungswache-Wachbuch |
| **Lizenz** | AGPL-3.0-or-later |
| **API** | `/api/v1/` (Token-Auth, Paperless/Nextcloud-Stil) |
| **App-Version** | 0.2.0 (passend zu Server ≥ 0.12.0) |

## Startflow

1. **Adresse** der Wache eingeben **oder** QR scannen → **Bestätigen**
2. **Benutzername** und **Passwort** (bei MFA: App-Token aus dem Web)

QR im Server-Web: Mein Konto → App-Tokens.

## Was die App macht

- Token lokal im Keystore / Keychain
- `GET /api/v1/me/` → eine Wache (keine Wachenauswahl in der App)
- `GET /api/v1/handovers/` → aktive Übergaben
- Phone: Bottom-Navigation · Tablet: NavigationRail + Grid

## Start

```bash
git clone https://github.com/darkspike1988/Wachbuch-Client.git
cd Wachbuch-Client
flutter pub get
flutter test
flutter run
```

### Android-APK

```bash
./scripts/build-apk.sh
# → dist/wachbuch-mobile.apk
```

Siehe [docs/INSTALL-ANDROID.md](docs/INSTALL-ANDROID.md) und [docs/PLAY-STORE.md](docs/PLAY-STORE.md).

## Kopplung zum Server

Vertrag und OpenAPI liegen im Server-Repo:

- https://github.com/darkspike1988/Rettungswache-Wachbuch/blob/main/docs/API.md
- https://github.com/darkspike1988/Rettungswache-Wachbuch/blob/main/docs/CLIENT.md

Spiegel im Server-Monorepo (Entwicklung/CI): `clients/wachbuch-mobile/`  
Synchronisation: `./scripts/publish-mobile-client-repo.sh` im Server-Repo.

## Vorbilder (Ideen, kein Code-Copy)

- [Paperless-go](https://github.com/bearyjd/paperless-go) – Flutter + Token + Secure Storage
- Nextcloud – Server-URL zuerst, dann Login

## Rechtliches

AGPL-3.0-or-later – siehe `LICENSE`.
