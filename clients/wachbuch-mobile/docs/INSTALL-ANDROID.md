# Android installieren und intern testen

Stand: 3. August 2026

Für die öffentliche Google-Play-Freigabe gilt zusätzlich
[`PLAY-STORE.md`](PLAY-STORE.md). Der Fortschritt steht in
[`ROADMAP.md`](../ROADMAP.md).

## Varianten

| Variante | Paket-ID | Anzeige | Verwendung |
| --- | --- | --- | --- |
| Internal | `de.wachbuch.mobile.internal` | Wachbuch Internal | Entwicklung, CI und kontrolliertes Sideloading |
| Production | `de.wachbuch.mobile` | Wachbuch | signierte Freigaben und Google Play |

Die interne APK ist zwar mit dem Android-Debug-Key signiert, trägt aber eine
eigene Paket-ID, einen eindeutigen Namen und das Deep-Link-Schema
`wachbuch-internal://`. Sie wird niemals als produktive oder Play-fähige APK
bezeichnet.

## Voraussetzungen

1. Android 7.0 oder neuer
2. laufender Wachbuch-Server mit `/api/v1/`
3. für nicht debuggbare Builds eine gültige HTTPS-Adresse
4. für Sideloading die Installation aus der verwendeten Datei-App erlauben

## CI-Artefakt installieren

1. In GitHub Actions den erfolgreichen Workflow **Flutter CI** öffnen.
2. Artefakt `wachbuch-internal-apks` laden.
3. Die zu deinem Gerät passende APK auswählen:
   - `arm64-v8a`: praktisch alle aktuellen Android-Geräte
   - `armeabi-v7a`: ältere 32-Bit-Geräte
   - `x86_64`: Emulatoren und wenige Spezialgeräte
4. Den Hash aus `SHA256SUMS` prüfen.
5. APK übertragen und installieren.
6. Die App **Wachbuch Internal** starten.

Beispiel für die Hashprüfung:

```bash
sha256sum -c SHA256SUMS
```

## Interne APKs selbst bauen

```bash
./scripts/build-apk.sh
```

Das Skript führt Tests aus und erstellt obfuskierte, R8-optimierte Split-APKs:

```text
dist/internal-apk/
├── app-...-armeabi-v7a-...apk
├── app-...-arm64-v8a-...apk
├── app-...-x86_64-...apk
└── SHA256SUMS
```

## Produktions-AAB bauen

Produktionsartefakte benötigen einen eigenen Upload-Key. Es gibt keinen
Debug-Key-Fallback.

```bash
cp android/key.properties.example android/key.properties
# private Werte eintragen
BUILD_NAME=0.5.2 BUILD_NUMBER=11 ./scripts/build-aab.sh
```

Alternativ den geschützten GitHub-Workflow **Android Signed Release** verwenden.
Details und Secret-Namen stehen in [`PLAY-STORE.md`](PLAY-STORE.md).

## Erster Start

1. Serveradresse eingeben oder QR-Code scannen.
2. Die erkannte HTTPS-Adresse kontrollieren und bestätigen.
3. Benutzername und Passwort verwenden; bei MFA einen App-Token einsetzen.
4. Kamera nur beim QR-Scan freigeben.
5. Ungefähren Standort nur für das automatische Tag-/Nacht-Design freigeben;
   bei Ablehnung bleibt die App vollständig nutzbar.

QR im Server-Web: **Mein Konto → App-Tokens**.

## Deep Links

| Variante | Schema |
| --- | --- |
| Production | `wachbuch://connect?url=…` |
| Internal | `wachbuch-internal://connect?url=…` |

Die App akzeptiert nur den Host `connect`, keinen zusätzlichen Pfad, genau einen
`url`-Parameter und keine eingebetteten Zugangsdaten. Eine neue Serveradresse
muss in der App bestätigt werden.

## Sicherheitseigenschaften

- kein Klartext-HTTP in nicht debuggbaren Builds
- Token über Secure Storage beziehungsweise Android Keystore
- keine Cloud-Sicherung und keine Geräteübertragung der App-Daten
- kein Zugriff auf Kontakte, Medien, Mikrofon oder Hintergrundstandort
- interne und produktive Installationen überschreiben einander nicht
- Produktionsbuilds werden ohne privaten Schlüssel nicht signiert

## Troubleshooting

| Problem | Lösung |
| --- | --- |
| APK lässt sich nicht installieren | passende ABI wählen und Installation aus dieser Quelle erlauben |
| „App nicht installiert“ bei Update | Signatur muss zur bereits installierten Variante passen; gegebenenfalls Internal deinstallieren |
| HTTP wird blockiert | für Internal/Release HTTPS verwenden; nur echter Debug-Build erlaubt LAN-HTTP |
| Kamera verweigert | Serveradresse manuell eingeben |
| Standort verweigert | Systemtheme wird verwendet |
| 403 bei MFA | App-Token statt Passwort verwenden |
| 401 nach Tokenablauf | erneut anmelden beziehungsweise Token erneuern |
