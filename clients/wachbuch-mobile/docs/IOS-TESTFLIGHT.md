# iOS- und TestFlight-Build

Der Flutter-Client enthält ein Xcode-Projekt unter `ios/` und verwendet die
Bundle-ID `de.wachbuch.wachbuchMobile`. Der normale CI-Build benötigt keine
Apple-Zugangsdaten. Ein TestFlight-Upload benötigt dagegen einen aktiven
Apple-Developer-Account, ein App-Store-Provisioning-Profile und einen
App-Store-Connect-API-Schlüssel.

## Voraussetzungen

- macOS mit einer von App Store Connect unterstützten Xcode-Version
- aktuelles Flutter Stable
- Apple-Developer-Team mit registrierter Bundle-ID
  `de.wachbuch.wachbuchMobile`
- App-Eintrag in App Store Connect
- iOS-Distribution-Zertifikat und App-Store-Provisioning-Profile

## Lokaler Simulator-Build

```bash
flutter pub get
flutter build ios --simulator --debug
```

Danach kann das Projekt in Xcode geöffnet werden:

```bash
open ios/Runner.xcodeproj
```

Unter **Signing & Capabilities** muss das eigene Apple-Team ausgewählt werden,
bevor die App auf einem echten iPhone oder iPad installiert wird.

## Signierfreier Release-Check

```bash
flutter build ios --release --no-codesign
```

Dieser Build prüft, ob Flutter, Plugins und das Xcode-Projekt kompilieren. Das
erzeugte `Runner.app` ist nicht für TestFlight oder die Installation auf einem
normalen Gerät signiert.

## GitHub Actions

### `iOS CI`

Der Workflow `.github/workflows/ios.yml` läuft bei Pull Requests und Pushes auf
`main`. Er erstellt:

1. einen Debug-Build für den iOS-Simulator,
2. einen signierfreien iOS-Release-Build,
3. das Artefakt `wachbuch-ios-unsigned` zur technischen Prüfung.

### `TestFlight`

Der Workflow `.github/workflows/testflight.yml` wird ausschließlich manuell
über **Actions → TestFlight → Run workflow** gestartet. Er archiviert die App,
exportiert eine signierte IPA und lädt sie mit einem App-Store-Connect-API-Key
hoch.

Das GitHub-Environment `testflight` sollte mit erforderlichen Reviewern und den
folgenden Secrets angelegt werden:

| Secret | Inhalt |
| --- | --- |
| `APPLE_TEAM_ID` | Apple Developer Team ID |
| `APP_STORE_CONNECT_KEY_ID` | Key ID des App-Store-Connect-API-Schlüssels |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer ID des API-Schlüssels |
| `APP_STORE_CONNECT_PRIVATE_KEY_BASE64` | Base64-kodierte `.p8`-Datei |
| `IOS_DISTRIBUTION_CERTIFICATE_BASE64` | Base64-kodierte `.p12`-Datei |
| `IOS_DISTRIBUTION_CERTIFICATE_PASSWORD` | Passwort der `.p12`-Datei |
| `IOS_PROVISIONING_PROFILE_BASE64` | Base64-kodiertes App-Store-Profile |
| `IOS_KEYCHAIN_PASSWORD` | starkes temporäres CI-Keychain-Passwort |

Beispiel zum Kodieren unter macOS:

```bash
base64 -i AuthKey_ABC123XYZ.p8 | pbcopy
base64 -i Wachbuch_Distribution.p12 | pbcopy
base64 -i Wachbuch_AppStore.mobileprovision | pbcopy
```

Die geheimen Dateien dürfen nicht ins Repository eingecheckt werden.

## Erster TestFlight-Upload

1. In Apple Developer die Bundle-ID `de.wachbuch.wachbuchMobile` registrieren.
2. In App Store Connect einen iOS-App-Eintrag mit derselben Bundle-ID anlegen.
3. Zertifikat, Provisioning Profile und API-Key erstellen.
4. Das GitHub-Environment und die Secrets konfigurieren.
5. PR mit erfolgreichem `iOS CI` mergen.
6. `TestFlight` manuell mit einer eindeutigen Build-Nummer starten.
7. In App Store Connect unter **TestFlight** die Verarbeitung und mögliche
   Warnungen kontrollieren.

## Datenschutz und Berechtigungen

Die App enthält Nutzungstexte für Kamera und Standort. Vor dem öffentlichen
App-Store-Release müssen zusätzlich die App-Privacy-Angaben in App Store
Connect mit dem tatsächlichen Serverbetrieb und den verwendeten Flutter-Plugins
abgeglichen werden. Standortdaten werden laut App-Konzept nur lokal für das
Tag-/Nacht-Design verwendet.

Apple verlangt für verwendete Required-Reason-APIs passende Privacy-Manifeste.
Bei jedem Plugin-Upgrade ist daher zu prüfen, ob die eingebetteten
`PrivacyInfo.xcprivacy`-Dateien vollständig sind.
