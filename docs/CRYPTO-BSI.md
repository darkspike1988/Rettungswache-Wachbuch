# Kryptografie nach BSI-Empfehlungen (öffentliche Verwaltung)

Stand: 31. Juli 2026.

Referenz: [BSI TR-02102](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Technische-Richtlinien/TR-nach-Thema-sortiert/tr02102/tr02102_node.html)
(aktuelle Jahresfassung, z. B. 2026-01) sowie TR-02102-2 (TLS).

Dieses Dokument ist **keine Zertifizierung**, sondern die produktseitige
Zuordnung gängiger Verfahren für selbst gehostete Wachbuch-Instanzen
(kommunal / öffentlicher Rettungsdienst).

## Kurzprofil

| Einsatz | Verfahren | Schlüssellänge / Parameter | BSI-Status |
| --- | --- | --- | --- |
| Transport (Proxy) | TLS **1.3** bevorzugt, mind. 1.2 | AEAD, Forward Secrecy | TR-02102-2 |
| E2EE Nachrichten | **AES-256-GCM** | 256 Bit | empfohlen |
| E2EE Schlüsselvereinbarung | **ECDH P-256** (secp256r1) | 256 Bit Kurve | empfohlen (≥ 250 Bit) |
| E2EE Schlüsselableitung | **HKDF-SHA-256** | – | empfohlen |
| Private-Key-Umschlag | **PBKDF2-SHA-256** → AES-256-GCM | ≥ 600 000 Iterationen | PBKDF2 zulässig; Argon2 im Browser nicht verfügbar |
| Login-Passwörter | **Argon2id** (Django), PBKDF2-Fallback | Django-Defaults | moderne Verwaltungspraxis |
| TOTP-Geheimnisse at rest | **AES-256-GCM** (Schlüssel aus `SECRET_KEY` via HKDF) | 256 Bit | empfohlen |
| App-Tokens | SHA-256-Hash in DB | – | Integrität / Vergleich |
| Zufall | OS-CSPRNG (`secrets` / Web Crypto) | – | empfohlen |

## Ende-zu-Ende (Chat / Privat / Post)

- Server speichert nur Ciphertext und Key-Wraps (`A256GCM+ECDH-ES`).
- Private Keys nur passphrase-umschlossen auf dem Server; Klartext-Private-Key
  nur kurz im Browser (`sessionStorage`) nach Entsperren.
- Master-Admin ohne Teilnahme liest keine Klartexte.

## Transport (Betreiberpflicht)

TLS terminiert am Reverse-Proxy. Empfohlen (TR-02102-2):

- TLS 1.3 mit z. B. `TLS_AES_256_GCM_SHA384`
- Kein TLS 1.0/1.1, kein RC4/3DES/CBC ohne AEAD
- `SECURE_COOKIES=true`, HSTS aktiv

Beispiel Caddy (TLS 1.3 default):

```caddy
wache.example.org {
        reverse_proxy 127.0.0.1:8090
}
```

Beispiel nginx (Ausschnitt):

```nginx
ssl_protocols TLSv1.3 TLSv1.2;
ssl_prefer_server_ciphers off;
# TLS 1.3 AEAD-Suiten nutzt OpenSSL automatisch bei TLSv1.3
```

## Was bewusst nicht Produkt-Scope ist

- VS-NfD / Geheimschutz-Freigaben
- Post-Quanten-Hybrid (BSI-Migration geplant; Roadmap später)
- Brainpool-Kurven (Web Crypto / Browser-Support begrenzt; P-256 üblich und BSI-konform)

## Verwandte Docs

- [`SECURITY-PRIVACY.md`](SECURITY-PRIVACY.md)
- [`COMPLIANCE.md`](COMPLIANCE.md)
- [`ASVS-L2.md`](ASVS-L2.md)
- [`OPERATIONS.md`](OPERATIONS.md)
