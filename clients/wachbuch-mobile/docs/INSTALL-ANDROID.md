# Android-APK installieren (FOSS Sideload)

Stand: 31. Juli 2026.

Die wachbuch-Client-App ist **AGPL** und wird als selbst gebaute bzw. CI-APK
auf Smartphone und Tablet installiert. Für einen späteren Play-Store-Release siehe
[PLAY-STORE.md](PLAY-STORE.md).

## Voraussetzungen auf dem Gerät

1. Android 7.0+ (API 24), Smartphone oder Tablet
2. Installation aus unbekannten Quellen / „App installieren“ für den Datei-Manager erlauben
3. Laufender Wachbuch-Server mit `/api/v1/` und **HTTPS**-URL (Release-APK erlaubt kein Cleartext-HTTP)

## Fertige APK nutzen

Wenn eine Release-APK vorliegt (z. B. GitHub Actions Artifact `wachbuch-mobile.apk`
oder `dist/wachbuch-mobile.apk` nach lokalem Build):

1. APK aufs Gerät kopieren (USB, Download, Nextcloud, …)
2. Datei antippen → installieren
3. App **Wachbuch** starten:
   - nur **Adresse** eingeben **oder** Kamera-Symbol / „QR-Code scannen“ → **Bestätigen**
   - danach **Benutzername** und **Passwort**
4. QR im Web: Mein Konto → App-Tokens

Package-ID: `de.wachbuch.mobile`

## Selbst bauen

```bash
cd clients/wachbuch-mobile   # bzw. Clone von wachbuch-Client
flutter pub get
flutter test
flutter build apk --release
```

Ausgabe:

`build/app/outputs/flutter-apk/app-release.apk`

Optional kopieren:

```bash
mkdir -p dist
cp build/app/outputs/flutter-apk/app-release.apk dist/wachbuch-mobile.apk
```

Für LAN-HTTP-Tests (nur Entwicklung): `flutter build apk --debug` – Cleartext ist
ausschließlich in debuggbaren Builds erlaubt.

### Signatur (FOSS-Sideload)

Der Release-Build ist vorerst mit dem **Debug-Keystore** signiert, damit jede
Person die APK ohne eigenen Release-Key bauen und sideloaden kann. Für den
**Play Store** eigenen Upload-Key setzen (siehe PLAY-STORE.md).

## Tablet & Smartphone

- **Smartphone:** untere `NavigationBar`
- **Tablet (≥ 720 dp Breite):** seitliche `NavigationRail`, Übergaben als Grid
- Portrait und Landscape; `supports-screens` für small–xlarge

## Anmeldung

| Situation | Vorgehen |
| --- | --- |
| Ohne MFA | Benutzername + Passwort → `POST /api/v1/token/` |
| Mit MFA | Im Web unter `/konto/api/` App-Token erzeugen und auf dem Login-Screen „App-Token“ wählen |

## Troubleshooting

| Problem | Hilfe |
| --- | --- |
| Cleartext / HTTP blockiert | Release braucht HTTPS; Debug-APK für LAN |
| Kamera verweigert | Adresse manuell eingeben; Rationale erklärt den Zweck |
| 403 MFA | App-Token statt Passwort |
| 401 nach Update | Abmelden, Token neu erzeugen |
| Installation blockiert | Unbekannte Apps für den Datei-Manager erlauben |

## Quellcode

- Client: `clients/wachbuch-mobile/` bzw. https://github.com/darkspike1988/wachbuch-Client
- Server: https://github.com/darkspike1988/Rettungswache-Wachbuch
