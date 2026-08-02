# Google Play Store – Freigabe-Checkliste (Wachbuch Client)

Stand: 31. Juli 2026.

Offizielle Quellen (verbindlich vor dem Upload prüfen):

| Thema | Google-Dokumentation |
| --- | --- |
| Target API | [Target API level](https://developer.android.com/google/play/requirements/target-sdk) / [Play Console](https://support.google.com/googleplay/android-developer/answer/11926878) |
| App-Signierung | [App signing](https://developer.android.com/studio/publish/app-signing) / Play App Signing |
| Berechtigungen | [Sensitive permissions](https://support.google.com/googleplay/android-developer/answer/9888170) |
| Netzwerk-Sicherheit | [Network security config](https://developer.android.com/privacy-and-security/security-config) |
| Design | [Material Design 3](https://m3.material.io/) / [Android Design](https://developer.android.com/design) |
| Datenschutzerklärung | [User Data](https://support.google.com/googleplay/android-developer/answer/10144311) |
| Data safety form | [Provide information](https://support.google.com/googleplay/android-developer/answer/10787469) |

## Was die App tut

1. **Server-Adresse** eingeben oder per **QR/Kamera** scannen → Bestätigen  
2. **Login** mit Benutzername und Passwort (optional App-Token bei MFA)  
3. Daten nur vom selbst gehosteten Wachbuch-Server (`/api/v1/`)

## Berechtigungen (Minimalprinzip)

| Permission | Pflicht? | Zweck |
| --- | --- | --- |
| `INTERNET` | ja | API zum eigenen Server |
| `CAMERA` | optional | nur QR der Server-Adresse; `uses-feature required=false` |

Keine Foto-/Medien-/Kontakte-/Standort-Permissions. Kamera-Rationale erscheint **vor** der Systemabfrage.

## Netzwerk

- Release: **kein Cleartext-HTTP** (`usesCleartextTraffic=false`)
- HTTPS mit System-CAs
- Debug-Builds: LAN-HTTP nur über `debug-overrides` (nicht für Play-Upload)

## Target SDK

Flutter Stable setzt `targetSdk` aktuell auf **API 36** (Android 16) – erfüllt die Play-Anforderung ab 31.08.2026 für neue Apps/Updates.

## Signierung für Play

1. Eigenen **Upload-Keystore** erzeugen (nicht den Debug-Key)
2. In `android/app/build.gradle.kts` `signingConfigs.release` setzen
3. Play App Signing in der Console aktivieren
4. AAB bauen: `flutter build appbundle --release`

FOSS-Sideload darf weiterhin Debug-Signatur nutzen; **Play-Uploads nicht**.

## Data safety / Datenschutz

Anzugeben (typisch):

- Konto-Login-Daten: an **euren Server** (nicht an Google/Entwickler-Backend)
- App-Token lokal im Android Keystore / Secure Storage
- Kamera: nicht gespeichert, nur QR-Scan
- Keine Werbung, kein Tracking-SDK

URL zur Datenschutzerklärung der jeweiligen Wache (Server `/datenschutz/`) in der Play Console hinterlegen.

## UX (Material 3)

- System Light/Dark
- Formulare mit Outline-Feldern, 48 dp Touchziele
- Phone: NavigationBar · Tablet: NavigationRail
- Autofill für Benutzername/Passwort

## Build

```bash
flutter build apk --release          # Sideload/Test
flutter build appbundle --release    # Play Console
```
