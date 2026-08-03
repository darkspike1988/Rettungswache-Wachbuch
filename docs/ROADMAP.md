# Roadmap

Stand: 31. Juli 2026.

## Erreicht (Basis bis 0.11.0)

- Docker, lokaler Login, Rollen, Uebergaben, Tagesaufgaben, Geburtstage, Kasse-Ledger
- PWA, oeffentliche Startseite, persoenlicher Bereich, Wachenchat
- Master-Admin legt Nutzer an/gibt frei; optionale Selbstregistrierung
- Profilbild, Passwort und Zwei-Faktor im persoenlichen Bereich
- E2EE fuer Wachenchat, private Chats und interne Post (Admin sieht keine Klartexte)
- Krypto an BSI TR-02102 angelehnt (AES-256-GCM, ECDH P-256, Argon2id, TLS 1.3)
- **API-Fundament** `/api/v1/` mit App-Tokens fuer Mobile-Clients
- **AGPL Flutter-Client** https://github.com/darkspike1988/Wachbuch-Client (Spiegel `clients/wachbuch-mobile/`)
- **Android-APK** sideloadbar (Phone/Tablet-Layout, FOSS-Build)
- Mobile-Onboarding: Server-Adresse/QR → Login; Play-Richtlinien-Doku; Repos aufeinander abgestimmt
- optionale MFA (TOTP/Passkeys), Web-Push, Wachen-ICS-Abos, Retention, Audit-Diffs
- gesetzliche Feiertage NRW im fortlaufenden Kalender/ICS (`holidays_enabled`)
- Compliance- und ASVS-L2-Matrix dokumentiert

## Naechste Fachbausteine (Fahrplan)

Priorisierte Umsetzung der noch offenen Wuensche. Keine Kalenderzeit-Schaetzung;
Reihenfolge nach Nutzen und Abhaengigkeiten.

### 1. Kaffeekasse: Zahlungsweg-Hinweise (PayPal.me, Wero, IBAN) — umgesetzt

**Ziel:** Beim Kassenstand klar zeigen, wohin freiwillig eingezahlt werden kann –
ohne Zahlungsabwicklung oder Gebuehrenlogik im Produkt.

| Schritt | Inhalt | Status |
| --- | --- | --- |
| 1.1 | Stationseinstellungen: Felder `paypal_me_url`, `wero_link`, `iban`, `bic` (optional), `payment_note` | ✓ |
| 1.2 | Anzeige in Kaffeekasse und optional auf „Mehr": Links / kopierbare IBAN | ✓ |
| 1.3 | Nur HTTPS-Links fuer PayPal.me/Wero; IBAN-Formatpruefung; keine Speicherung von Transaktions-IDs Dritter | ✓ |
| 1.4 | Datenschutzhinweis: oeffentliche Team-Zahlungsdaten, Zweck Gemeinschaftskasse | ✓ |
| 1.5 | Tests + Kurz-Doku in OPERATIONS/COMPLIANCE | ✓ |

**Nicht im Scope:** automatischer Abgleich mit PayPal/Wero, QR-Payment-API, SEPA-Mandate.

### 2. Fortlaufender Kalender: Feiertage (NRW) + Muellkalender

**Ziel:** Der Wachenkalender zeigt neben eigenen Terminen gesetzliche Feiertage
(NRW) und spaeter Abfuhrtermine; alles auch als iCal/Abo.

| Schritt | Inhalt |
| --- | --- |
| 2.0 | **Feiertage NRW** im fortlaufenden Kalender + ICS (Modul `holidays_enabled`) – erledigt in 0.6.1 |
| 2.1 | Recherche/Freigabe der offiziellen Muell-Quelle (AbfallNavi / RegioIT-iCal) |
| 2.2 | Stationsfelder: Gemeinde/Ort, Strasse bzw. Quellen-ID, gewaehlte Fraktionen |
| 2.3 | Admin-UI: Auswahl Ort → Strasse/Standort |
| 2.4 | Sync → Abfuhren im selben fortlaufenden Kalender/ICS |
| 2.5 | Token-Abo analog Wachenkalender |
| 2.6 | Dashboard: naechste Abfuhren; Kennzeichnung externe Quelle |

**Abhaengigkeit Muell:** Freigabe der Datenquelle. Fallback: manuelle ICS-URL
pro Station. Feiertage sind unabhaengig davon nutzbar.

### 3. Empfohlene Reihenfolge

```text
1. Kaffeekasse-Zahlungshinweise
2. Feiertage im fortlaufenden Kalender   (umgesetzt)
3. Muellkalender: manueller ICS-URL-Fallback je Station
4. Muellkalender: Ort/Strasse-Auswahl Kreis GT + Sync
5. API v1 / AGPL-Client ausbauen (E2EE-Chat über API, Stores/F-Droid; Schreiben für Übergaben/Kalender/Kasse/Checklisten ist in 0.14)
6. Feinschliff UX (Dashboard, Kopieren-Buttons)
```
### 4. Bewusst weiterhin ausserhalb

- Patientendaten, Einsatz-/Alarmierung, Dienstplanung
- allgemeine Datei-Uploads (Ausnahme: kleines Profilbild im Konto)
- Messenger ausserhalb von Wachenchat / Privat / interner Post
- automatische Zahlungseinzuege und Banking-APIs
- volles CalDAV-Serverprodukt (ICS-Abo bleibt der Weg)

## Phase 1 - geschlossener Test (Betrieb)

- reale Arbeitsablaeufe mit Testdaten
- MFA/Passkeys und Push im Team erproben
- ASVS-Matrix abhaken; Backup/Restore und Updates testen
- Fachbausteine 1–2 parallel oder direkt nach Stabilisierung

## Phase 2 - formaler Pilot

- Datenschutz-/Mitbestimmung, MFA-Pflicht ggf. aktivieren
- Audit-Export, Barrierearmut / Wachenterminals
- Muellkalender-Quelle schriftlich freigeben
- erste AGPL-Mobile-Clients gegen `/api/v1/` (Lesen, spaeter Schreiben)

## Phase 3 - Produktion

- unabhaengige ASVS-L2-Pruefung und Lasttest
- Go-live-Checkliste; erst danach oeffentlicher DNS-Name

Siehe auch [`AUDIT-2026-07.md`](AUDIT-2026-07.md), [`COMPLIANCE.md`](COMPLIANCE.md),
[`ASVS-L2.md`](ASVS-L2.md).
