# Roadmap

Stand: 31. Juli 2026.

## Erreicht (Basis bis 0.6.0)

- Docker, lokaler Login, Rollen, Uebergaben, Tagesaufgaben, Geburtstage, Kasse-Ledger
- PWA, oeffentliche Startseite, Registrierung mit Freigabe, persoenlicher Bereich, Wachenchat
- optionale MFA (TOTP/Passkeys), Web-Push, Wachen-ICS-Abos, Retention, Audit-Diffs
- Compliance- und ASVS-L2-Matrix dokumentiert

## Naechste Fachbausteine (Fahrplan)

Priorisierte Umsetzung der noch offenen Wuensche. Keine Kalenderzeit-Schaetzung;
Reihenfolge nach Nutzen und Abhaengigkeiten.

### 1. Kaffeekasse: Zahlungsweg-Hinweise (PayPal.me, Wero, IBAN)

**Ziel:** Beim Kassenstand klar zeigen, wohin freiwillig eingezahlt werden kann –
ohne Zahlungsabwicklung oder Gebuehrenlogik im Produkt.

| Schritt | Inhalt |
| --- | --- |
| 1.1 | Stationseinstellungen: Felder `paypal_me_url`, `wero_handle`/`wero_link`, `iban`, `bic` (optional), `payment_note` |
| 1.2 | Anzeige in Kaffeekasse und optional auf „Mehr“: Links / kopierbare IBAN |
| 1.3 | Nur HTTPS-Links fuer PayPal.me; IBAN-Formatpruefung; keine Speicherung von Transaktions-IDs Dritter |
| 1.4 | Datenschutzhinweis: oeffentliche Team-Zahlungsdaten, Zweck Gemeinschaftskasse |
| 1.5 | Tests + Kurz-Doku in OPERATIONS/COMPLIANCE |

**Nicht im Scope:** automatischer Abgleich mit PayPal/Wero, QR-Payment-API, SEPA-Mandate.

### 2. Muellkalender Kreis Guetersloh (Ort/Standort → iCal)

**Ziel:** Pro Wache den passenden Abfuhrkalender waehlen und als iCal/Abo nutzbar
machen (Wachentablet / persoenliche Kalender-Apps).

| Schritt | Inhalt |
| --- | --- |
| 2.1 | Recherche/Freigabe der offiziellen Quelle (AbfallNavi / RegioIT-iCal) und erlaubte Hosts |
| 2.2 | Stationsfelder: Gemeinde/Ort, Strasse bzw. Quellen-ID, gewaehlte Fraktionen |
| 2.3 | Admin-UI: Auswahl Ort → Strasse/Standort (gestaffelte Listen, Cache der Metadaten) |
| 2.4 | Sync-Job oder On-Demand-Abruf → interne `WasteCollectionEvent` bzw. Spiegel als ICS |
| 2.5 | Ausgabe: stationsweiter ICS-Feed + optional Token-Abo (analog Wachenkalender) |
| 2.6 | Dashboard/Mehr: naechste Abfuhren; klare Kennzeichnung „externe Behoerdenquelle“ |
| 2.7 | Allowlist, SSRF-Haertung, Attribution, Ausfallhinweis wenn Quelle fehlt |

**Abhaengigkeit:** rechtliche/organisatorische Freigabe der Datenquelle; kein Scraping
ohne stabile, freigegebene Schnittstelle. Fallback: manuell hinterlegte ICS-URL
pro Station, bis die gestaffelte Auswahl steht.

**Nicht im Scope:** Ersatz der offiziellen App, Push fuer jede Tonne, kreisweite
Haushalte ausserhalb der konfigurierten Wache.

### 3. Empfohlene Reihenfolge

```text
1. Kaffeekasse-Zahlungshinweise   (klein, sofort nutzbar)
2. Muellkalender: manueller ICS-URL-Fallback je Station
3. Muellkalender: Ort/Strasse-Auswahl Kreis GT + Sync
4. Feinschliff UX (Dashboard-Kachel Abfuhr, Kopieren-Buttons)
```

### 4. Bewusst weiterhin ausserhalb

- Patientendaten, Einsatz-/Alarmierung, Dienstplanung
- Datei-Uploads, allgemeiner Messenger ausserhalb des Wachenchats
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

## Phase 3 - Produktion

- unabhaengige ASVS-L2-Pruefung und Lasttest
- Go-live-Checkliste; erst danach oeffentlicher DNS-Name

Siehe auch [`AUDIT-2026-07.md`](AUDIT-2026-07.md), [`COMPLIANCE.md`](COMPLIANCE.md),
[`ASVS-L2.md`](ASVS-L2.md).
