# Wachbuch Client (AGPL)

Open-Source-Begleit-App für selbst gehostetes
**[Wachbuch](https://github.com/darkspike1988/Rettungswache-Wachbuch)** (iOS & Android).

| | |
| --- | --- |
| **Dieses Repo** | https://github.com/darkspike1988/Wachbuch-Client |
| **Server** | https://github.com/darkspike1988/Rettungswache-Wachbuch |
| **Lizenz** | AGPL-3.0-or-later |
| **API** | `/api/v1/` (Token-Auth, Paperless/Nextcloud-Stil) |
| **App-Version** | 0.5.1 (passend zu Server ≥ 0.14.1) |
| **Roadmap** | [ROADMAP.md](ROADMAP.md) |

## Startflow

1. **Adresse** der Wache eingeben **oder** QR scannen → **Bestätigen**
2. **Benutzername** und **Passwort** (bei MFA: App-Token aus dem Web)

QR im Server-Web: Mein Konto → App-Tokens.

## Was die App macht

- Token lokal im Keystore / Keychain
- `GET /api/v1/me/` → eine Wache (keine Wachenauswahl in der App)
- `GET /api/v1/handovers/` → aktive Übergaben
- Volltextsuche, kombinierbare Status-/Prioritätsfilter und lokalisierte Chips
- antippbare Übergabekarten mit Detailansicht über `GET /api/v1/handovers/{id}/`
- kompakte Status- und Dringlichkeitsübersicht auf dem Dashboard
- Phone: Bottom-Navigation · Tablet: NavigationRail + Grid
- Material Design 3 mit responsivem Smartphone-/Tablet-Layout
- automatisches Tag-/Nacht-Design nach lokal berechnetem Sonnenaufgang und Sonnenuntergang
- dafür wird nur der ungefähre Gerätestandort während der App-Nutzung abgefragt; keine Standortdaten verlassen das Gerät
- `wachbuch://connect?url=…` öffnet die Produktions-App und übernimmt nach Bestätigung eine neue Serveradresse

## Start

```bash
git clone https://github.com/darkspike1988/Wachbuch-Client.git
cd Wachbuch-Client
flutter pub get
flutter test
```

Android lokal als eindeutig markierte interne Variante starten:

```bash
flutter run --flavor internal
```

Auf iOS bleibt der normale Start ohne Android-Flavor bestehen:

```bash
flutter run -d ios
```

### Android Internal

Die installierbare Testversion besitzt die separate Paket-ID
`de.wachbuch.mobile.internal` und kann parallel zur Produktions-App installiert
werden:

```bash
./scripts/build-apk.sh
# → dist/internal-apk/*.apk + SHA256SUMS
```

### Android Production

Ein Produktionsbuild benötigt einen eigenen Upload-Key und fällt niemals auf
den Debug-Key zurück:

```bash
cp android/key.properties.example android/key.properties
BUILD_NAME=0.5.2 BUILD_NUMBER=11 bash scripts/build-aab.sh
```

Alternativ erstellt der geschützte Workflow **Android Signed Release** ein
signiertes AAB, signierte ABI-APKs, Hashes, Zertifikatsberichte und
Obfuskationssymbole.

### iOS

Ein lokaler Simulator-Build benötigt macOS, Xcode und Flutter Stable:

```bash
flutter pub get
flutter build ios --simulator --debug
```

Für jeden Pull Request prüft GitHub Actions zusätzlich einen iOS-Simulator-Build
und einen signierfreien Release-Build. Der manuelle TestFlight-Workflow wird erst
nach Einrichtung der geschützten Apple-Secrets verwendet.

Siehe [docs/INSTALL-ANDROID.md](docs/INSTALL-ANDROID.md),
[docs/PLAY-STORE.md](docs/PLAY-STORE.md),
[docs/IOS-TESTFLIGHT.md](docs/IOS-TESTFLIGHT.md) und
[docs/MARKET-RESEARCH.md](docs/MARKET-RESEARCH.md).

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
