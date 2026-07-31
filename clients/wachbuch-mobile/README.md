# Wachbuch Mobile (AGPL)

Open-Source-Begleit-App für selbst gehostetes **Wachbuch** (iOS & Android).
Lizenz: **AGPL-3.0-or-later** – gleiche Familie wie der Server.

Vorbilder (Ideen, kein Code-Copy):

- [Paperless-go](https://github.com/bearyjd/paperless-go) – Flutter + Token + Secure Storage
- [Paperless-ngx Uploader](https://github.com/gmag11/Paperless_ngx_uploader) – schlanker Self-Host-Client
- Nextcloud Login-Flow – Server-URL zuerst, App-Passwort/Token, keine zentrale Cloud

## Was die App macht

1. **Server-URL** eingeben (`https://wache.example.org`)
2. **Login** (Benutzer/Passwort → `POST /api/v1/token/`) **oder** App-Token aus `/konto/api/` einfügen (nötig bei MFA)
3. Token in der **Keychain / Keystore** speichern
4. `GET /api/v1/me/` → **eine Wache**, Rolle, Module
5. `GET /api/v1/handovers/` → aktive Übergaben dieser Wache

Es gibt **keine** Wachenauswahl in der App – die Station kommt aus der Server-Mitgliedschaft.

## Voraussetzungen

- Flutter stable (3.8+)
- Erreichbarer Wachbuch-Server mit `/api/v1/` (ab Server 0.9.0)
- Für iOS: Xcode; für Android: Android SDK

## Start

```bash
cd clients/wachbuch-mobile
flutter pub get
flutter test
flutter run
```

Release-Builds:

```bash
flutter build apk
flutter build ios --no-codesign
```

## Projektstruktur

```text
lib/
  api/client.dart          # /api/v1/ HTTP-Client
  auth/session_store.dart  # URL + sicheres Token
  screens/login_screen.dart
  screens/home_shell.dart  # Übersicht / Übergaben / Konto
  main.dart
```

## Rechtliches

Quellcode dieser App steht unter AGPL-3.0-or-later. Wer die App verteilt oder
als Netzdienst anbietet, muss den entsprechenden Quellcode unter AGPL anbieten.
Der Server im übergeordneten Repository bleibt die fachliche Quelle der Wahrheit.

Siehe [`docs/CLIENT.md`](../../docs/CLIENT.md) und [`docs/API.md`](../../docs/API.md).
