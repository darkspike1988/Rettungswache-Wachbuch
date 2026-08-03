# Roadmap

Stand: 3. August 2026.

## Sicherheits-, Betriebs- und Design-Remediation

Die verbindliche Folgeplanung aus der Review vom 3. August 2026 steht in
[`REMEDIATION-ROADMAP-2026-08.md`](REMEDIATION-ROADMAP-2026-08.md).
Arbeitsregeln fuer weitere Coding-Agenten stehen in [`../AGENTS.md`](../AGENTS.md).

Aktueller Stand der ersten Welle:

- [~] CSP-kompatible Empfaengerauswahl fuer verschluesselte Post
- [x] sichere JSON-Einbettung ohne `|safe`/`innerHTML`
- [x] Sicherheitsregressionstests
- [x] E2EE-Texte an das reale Vertrauensmodell angepasst
- [~] Race-Condition-Schutz fuer Tagesaufgaben
- [x] scheme-relative Redirects blockiert
- [~] vierteilige Hauptnavigation, Fokus- und mobile Wochenansicht verbessert
- [ ] Least-Privilege-Backuprolle
- [ ] gemeinsames Rate Limiting hinter explizit vertrautem Proxy
- [~] CI-Baseline; weitere Supply-Chain-Gates, Push-Outbox und zugaenglicher Entsperrdialog offen
- [ ] externe ASVS-, Penetrations-, Last-, Restore- und Accessibility-Abnahme

`[~]` bedeutet: Code ist im Review-Branch umgesetzt, die in der Detail-Roadmap
genannte Browser-, Parallelitaets- oder manuelle UX-Abnahme steht noch aus.
Django- und Docker-CI waren auf Commit `6af6689` (Run 59) gruen.

## Erreicht (Basis bis 0.14.2)

- Docker, lokaler Login, Rollen, Uebergaben, Tagesaufgaben, Geburtstage, Kasse-Ledger
- PWA, oeffentliche Startseite, persoenlicher Bereich, Wachenchat
- Master-Admin legt Nutzer an/gibt frei; optionale Selbstregistrierung
- Profilbild, Passwort und Zwei-Faktor im persoenlichen Bereich
- clientseitig verschluesselte Speicherung fuer Wachenchat, private Chats und
  interne Post; Webclient und Server bleiben Teil des Vertrauensmodells
- Krypto an BSI TR-02102 angelehnt (AES-256-GCM, ECDH P-256, Argon2id, TLS 1.3)
- **API-Fundament** `/api/v1/` mit App-Tokens fuer Mobile-Clients
- **AGPL Flutter-Client** https://github.com/darkspike1988/Wachbuch-Client (Spiegel `clients/wachbuch-mobile/`)
- **Android-APK** sideloadbar (Phone/Tablet-Layout, FOSS-Build)
- Mobile-Onboarding: Server-Adresse/QR -> Login; Play-Richtlinien-Doku; Repos aufeinander abgestimmt
- optionale MFA (TOTP/Passkeys), Web-Push, Wachen-ICS-Abos, Retention, Audit-Diffs
- gesetzliche Feiertage NRW im fortlaufenden Kalender/ICS (`holidays_enabled`)
- Compliance- und ASVS-L2-Matrix dokumentiert

## Naechste Fachbausteine (Fahrplan)

Priorisierte Umsetzung der noch offenen Wuensche. Keine Kalenderzeit-Schaetzung;
Reihenfolge nach Nutzen und Abhaengigkeiten. Sicherheits- und Betriebsblocker aus
der Remediation-Roadmap haben Vorrang vor neuen Fachmodulen.

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

| Schritt | Inhalt | Status |
| --- | --- | --- |
| 2.0 | **Feiertage NRW** im fortlaufenden Kalender + ICS (Modul `holidays_enabled`) – erledigt in 0.6.1 | ✓ |
| 2.1 | Recherche/Freigabe der offiziellen Muell-Quelle (AbfallNavi / RegioIT-iCal) | offen |
| 2.2 | Stationsfelder: ICS-URL (Fallback), Anzeigename, Modulschalter | ✓ (Fallback) |
| 2.3 | Admin-UI: Auswahl Ort -> Strasse/Standort | offen (vom ICS-Fallback obsolet, kommt mit 2.1) |
| 2.4 | Sync -> Abfuhren im selben fortlaufenden Kalender/ICS | ✓ |
| 2.5 | Token-Abo analog Wachenkalender | ✓ (gleiche ICS-Abo-Route, Abfuhren inklusive) |
| 2.6 | Dashboard: naechste Abfuhren; Kennzeichnung externe Quelle | ✓ |

**Abhaengigkeit Muell:** Freigabe der Datenquelle. **Fallback (umgesetzt):
manuelle ICS-URL pro Station** mit SSRF-Schutz wie bei RSS-Feeds. Feiertage
sind unabhaengig davon nutzbar.

### 3. Empfohlene Reihenfolge

```text
0. Review-Remediation Wave 0-2
1. Kaffeekasse-Zahlungshinweise
2. Feiertage im fortlaufenden Kalender   (umgesetzt)
3. Muellkalender: manueller ICS-URL-Fallback je Station   (umgesetzt)
4. Muellkalender: Ort/Strasse-Auswahl Kreis GT + Sync
5. API v1 / AGPL-Client ausbauen (E2EE-Chat über API, Stores/F-Droid; Schreiben für Übergaben/Kalender/Kasse/Checklisten ist in 0.14; Demo-Modus in 0.15)
6. Feinschliff UX (Dashboard, Kopieren-Buttons)
7. Review-Remediation Wave 3 und formale Produktionsfreigabe
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
- Remediation Wave 0–2 und ASVS-Matrix abarbeiten
- Backup/Restore und Updates testen

## Phase 2 - formaler Pilot

- Datenschutz-/Mitbestimmung, MFA-Pflicht ggf. aktivieren
- Audit-Export, Barrierearmut / Wachenterminals
- Muellkalender-Quelle schriftlich freigeben
- erste AGPL-Mobile-Clients gegen `/api/v1/`

## Phase 3 - Produktion

- Remediation Wave 3
- unabhaengige ASVS-L2-Pruefung und Lasttest
- Go-live-Checkliste; erst danach oeffentlicher DNS-Name

Siehe auch [`AUDIT-2026-07.md`](AUDIT-2026-07.md), [`COMPLIANCE.md`](COMPLIANCE.md),
[`ASVS-L2.md`](ASVS-L2.md) und
[`REMEDIATION-ROADMAP-2026-08.md`](REMEDIATION-ROADMAP-2026-08.md).
