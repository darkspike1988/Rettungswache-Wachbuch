# Google Play Store – Freigabehandbuch

Stand: 3. August 2026

Der verbindliche Fortschritt wird in [`ROADMAP.md`](../ROADMAP.md) geführt. Nur
tatsächlich umgesetzte und geprüfte Schritte werden dort gestrichen.

## Offizielle Grundlagen

- [Target-API-Anforderungen](https://developer.android.com/google/play/requirements/target-sdk)
- [App-Signierung und Play App Signing](https://developer.android.com/studio/publish/app-signing)
- [Android App Bundles](https://developer.android.com/guide/app-bundle)
- [Automatische Sicherung](https://developer.android.com/identity/data/autobackup)
- [Network Security Configuration](https://developer.android.com/privacy-and-security/security-config)
- [Data Safety](https://support.google.com/googleplay/android-developer/answer/10787469)

Ab dem 31. August 2026 müssen neue Apps und Updates Android 16 beziehungsweise
API 36 oder höher als Ziel verwenden. Das Projekt übernimmt `targetSdk` aus dem
aktuellen Flutter-Stable-SDK und prüft den Produktionsbuild in CI.

## Varianten

| Variante | Paket-ID | Name | Signierung | Zweck |
| --- | --- | --- | --- | --- |
| `internal` | `de.wachbuch.mobile.internal` | Wachbuch Internal | Android-Debug-Key | CI, Entwicklung und kontrolliertes Sideloading |
| `production` | `de.wachbuch.mobile` | Wachbuch | eigener Upload-Key | Google Play und produktive APK-Verteilung |

Die interne Variante ist bewusst als eigene App installierbar. Sie kann die
Produktions-App nicht überschreiben und verwendet das separate URI-Schema
`wachbuch-internal://`.

## Upload-Key erzeugen

Der Upload-Key darf nicht ins Repository gelangen. Ein Beispiel:

```bash
keytool -genkeypair -v \
  -keystore wachbuch-upload.jks \
  -alias wachbuch-upload \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000
```

Den Keystore verschlüsselt offline sichern. Für Google Play sollte Play App
Signing aktiviert werden, damit der App-Signaturschlüssel getrennt vom
Upload-Key verwaltet wird.

## Lokale Signing-Konfiguration

```bash
cp android/key.properties.example android/key.properties
```

Danach die realen Werte in `android/key.properties` eintragen. Die Datei und
alle üblichen Keystore-Endungen sind durch `.gitignore` ausgeschlossen.

Alternativ akzeptiert Gradle folgende Umgebungsvariablen:

- `ANDROID_KEYSTORE_PATH`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

Mit `REQUIRE_RELEASE_SIGNING=true` bricht der Build ab, falls auch nur ein Wert
fehlt. Einen Debug-Key-Fallback für `production` gibt es nicht.

## Lokaler Produktionsbuild

```bash
BUILD_NAME=0.5.2 BUILD_NUMBER=11 ./scripts/build-aab.sh
```

Das Skript führt Analyse und Tests aus, baut ein obfuskiertes und signiertes
Produktions-AAB, prüft die JAR-Signatur und speichert AAB, SHA-256-Hash und
Symbole getrennt unter `dist/`.

Direkter Flutter-Aufruf:

```bash
REQUIRE_RELEASE_SIGNING=true flutter build appbundle \
  --release \
  --flavor production \
  --build-name 0.5.2 \
  --build-number 11 \
  --obfuscate \
  --split-debug-info=build/symbols/production
```

## Geschützter GitHub-Release

In GitHub ein Environment namens `google-play` anlegen und mindestens einen
erforderlichen Reviewer konfigurieren. Folgende Secrets werden benötigt:

| Secret | Inhalt |
| --- | --- |
| `ANDROID_UPLOAD_KEYSTORE_BASE64` | Base64-kodierter Upload-Keystore |
| `ANDROID_UPLOAD_KEYSTORE_PASSWORD` | Keystore-Passwort |
| `ANDROID_UPLOAD_KEY_ALIAS` | Alias des Upload-Schlüssels |
| `ANDROID_UPLOAD_KEY_PASSWORD` | Schlüsselpasswort |

Keystore unter Linux oder macOS kodieren:

```bash
base64 -w 0 wachbuch-upload.jks
# macOS alternativ: base64 -i wachbuch-upload.jks
```

Danach **Actions → Android Signed Release → Run workflow** öffnen und eine neue,
streng steigende Build-Nummer angeben. Der Workflow:

1. validiert alle Secrets,
2. installiert den Keystore nur temporär,
3. führt Analyse und Tests aus,
4. baut signiertes AAB und signierte ABI-APKs,
5. führt Android-Lint aus,
6. prüft Paket-ID, `debuggable=false` und Signaturen,
7. erzeugt Hashes, Zertifikatsbericht, Abhängigkeitsberichte und Symbole,
8. löscht den temporären Keystore auch bei Fehlern.

## Normaler Pull-Request-CI

Der normale CI benötigt keine privaten Schlüssel. Er baut:

- obfuskierte, R8-optimierte interne Split-APKs,
- ein absichtlich nicht signiertes Production-AAB als Kompilier- und
  Größenprüfung,
- Android-Lint,
- Signatur-, Paket-ID- und Größenprüfungen,
- Abhängigkeits- und Symbolartefakte.

Das unsigned Production-AAB wird nicht als Download veröffentlicht und darf
nicht in die Play Console hochgeladen werden.

## Datenschutz und Berechtigungen

| Permission | Zweck | Verhalten ohne Freigabe |
| --- | --- | --- |
| `INTERNET` | Verbindung zum selbst gehosteten Wachbuch-Server | App nicht nutzbar |
| `CAMERA` | optionaler QR-Scan der Server-Adresse | manuelle Eingabe funktioniert |
| `ACCESS_COARSE_LOCATION` | lokale Sonnenaufgang-/Sonnenuntergangsberechnung | Systemtheme als Fallback |

Nicht vorhanden sind Medien-, Kontakt-, Mikrofon- oder
Hintergrundstandortberechtigungen. Standortdaten verlassen nach App-Konzept das
Gerät nicht. Kamera-Bilder werden nicht gespeichert.

App-Daten sind sowohl von Cloud-Backups als auch von Geräteübertragungen
explizit ausgeschlossen. Das betrifft insbesondere Token, Serveradresse und
lokale Einstellungen.

## Data-Safety-Angaben

Vor Einreichung mit dem realen Serverbetrieb abgleichen:

- Login- und Wachbuchdaten werden an den vom Nutzer gewählten Wachbuch-Server
  übertragen.
- Der App-Token wird lokal über Secure Storage beziehungsweise Android Keystore
  geschützt.
- Kamera wird nur für QR-Erkennung verarbeitet und nicht gespeichert.
- Ungefährer Standort wird nur lokal verwendet und nicht übertragen.
- Keine Werbung und kein Tracking-SDK.
- Datenschutzerklärung muss öffentlich und ohne Login erreichbar sein.

## Upload-Reihenfolge

1. App `de.wachbuch.mobile` in der Play Console anlegen.
2. Play App Signing aktivieren.
3. Signiertes AAB zunächst in den internen Test-Track laden.
4. Data Safety, Datenschutzerklärung, Altersfreigabe und Store-Eintrag ausfüllen.
5. Interne Tester auf Login, QR, Deep Link, Standortverweigerung, Tablet,
   Rotation und Sitzungsablauf testen lassen.
6. Pre-Launch-Report prüfen und kritische Abstürze, ANRs oder Sicherheitsfehler
   vor Produktion beheben.
7. Erst danach stufenweise in Produktion ausrollen.
