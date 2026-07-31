# Wachbuch Mobile (AGPL)

Open-Source-Begleit-App für selbst gehostetes **[Wachbuch](https://github.com/darkspike1988/Rettungswache-Wachbuch)** (iOS & Android).

**Lizenz:** AGPL-3.0-or-later  
**Geplantes GitHub-Repo:** https://github.com/darkspike1988/wachbuch-Client  
**Server-API:** `/api/v1/` (Token-Auth wie Paperless/Nextcloud)

## Status

Der Quellcode wird derzeit im Server-Monorepo unter `clients/wachbuch-mobile/`
entwickelt und mit `scripts/publish-mobile-client-repo.sh` in dieses Repo
gespiegelt, sobald das leere GitHub-Repository angelegt ist.

## Was die App macht

1. **Server-URL** eingeben (`https://wache.example.org`)
2. **Login** (Benutzer/Passwort → `POST /api/v1/token/`) **oder** App-Token aus `/konto/api/` einfügen (nötig bei MFA)
3. Token in der **Keychain / Keystore** speichern
4. `GET /api/v1/me/` → **eine Wache**, Rolle, Module
5. `GET /api/v1/handovers/` → aktive Übergaben dieser Wache

Es gibt **keine** Wachenauswahl in der App – die Station kommt aus der Server-Mitgliedschaft.

## Vorbilder (Ideen, kein Code-Copy)

- [Paperless-go](https://github.com/bearyjd/paperless-go) – Flutter + Token + Secure Storage (AGPL)
- [Paperless-ngx Uploader](https://github.com/gmag11/Paperless_ngx_uploader) – schlanker Self-Host-Client
- Nextcloud App-Passwords / Login-Flow – Server-URL zuerst

# Android-APK (Smartphone & Tablet)

Installierbare FOSS-APK (Package `de.wachbuch.mobile`, Android 7+):

```bash
./scripts/build-apk.sh
# → dist/wachbuch-mobile.apk
```

Sideload: APK aufs Gerät kopieren, unbekannte Quellen erlauben, installieren.
Details: [docs/INSTALL-ANDROID.md](docs/INSTALL-ANDROID.md) · Play-Checkliste: [docs/PLAY-STORE.md](docs/PLAY-STORE.md).

### Startflow (Play-/Material-konform)

1. Nur **Adresse** eingeben **oder** Kamera-QR scannen → **Bestätigen**
2. Danach **Benutzername** und **Passwort**

- **Smartphone:** untere Navigation
- **Tablet (≥ 720 dp):** NavigationRail + Übergaben-Grid
- CI baut die APK als Artifact `wachbuch-mobile-apk`

## Start

```bash
git clone https://github.com/darkspike1988/wachbuch-Client.git
cd wachbuch-Client
flutter pub get
flutter test
flutter run
```

Solange das zweite Repo noch leer/nicht angelegt ist, aus dem Server-Repo:

```bash
cd Rettungswache-Wachbuch/clients/wachbuch-mobile
flutter pub get && flutter test && flutter run
# oder: ./scripts/build-apk.sh
```

## Zweites Repo anlegen (Maintainer)

1. Auf GitHub **wachbuch-Client** öffentlich anlegen (ohne initiales README, wenn möglich)
2. Im Server-Repo: `./scripts/publish-mobile-client-repo.sh`
3. Danach Entwicklung primär in **wachbuch-Client**; Server verweist auf den Client

## Rechtliches

AGPL-3.0-or-later – siehe `LICENSE`. Wer die App verteilt oder als Netzdienst
anbietet, muss den entsprechenden Quellcode unter AGPL anbieten.
