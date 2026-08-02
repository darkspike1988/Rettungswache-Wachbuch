# Compliance: DSGVO, Cookies, AI Act, NRW oeffentlicher Dienst

Stand: 31. Juli 2026. Technische und organisatorische Orientierung fuer Betreiber.
Keine Rechtsberatung.

## Kurzfazit

| Thema | Produktstand |
| --- | --- |
| DSGVO | Privacy by Design, Rollen, Audit ohne Freitextkopien, Modulschalter |
| Cookies / TDDDG | nur notwendige Session- und CSRF-Cookies; Transparenz unter `/datenschutz/` |
| EU AI Act | Produkt ist kein KI-System; keine automatisierte Bewertung von Beschaeftigten |
| NRW oeffentlicher Dienst | DSG NRW / LPVG-Hinweise; Mitbestimmung und VVT bleiben Betreiberpflicht |
| Versionierung | SemVer in `core/version.py`, Footer, `/healthz/`, Changelog |
| Updates | dokumentierter Release-/Rollback-Ablauf in `OPERATIONS.md` |

## DSGVO und Privacy by Design

Technisch umgesetzt oder vorbereitet:

- Zweckbindung: Wachenorganisation, keine Patienten-/Einsatzakte
- Datenminimierung: Geburtstage ohne Jahr, Audit ohne Fachfreitexte
- Integritaet: Append-only-Kasse, Revisionshistorie, DB-Rechte
- Vertraulichkeit: TLS-Proxy (TLS 1.3 / BSI TR-02102-2), sichere Cookies, CSP,
  Rollenisolation, E2EE mit AES-256-GCM (siehe [`CRYPTO-BSI.md`](CRYPTO-BSI.md))
- Passwoerter: Argon2id; TOTP-Geheimnisse AES-256-GCM at rest
- Betroffenenrechte: organisatorisch in der Go-live-Checkliste; technisch
  Austrittsbereinigung (Geburtstage), Feed-Retention und optionale Audit-Fristen
  vorbereitet; weitere Fristen nach Freigabe schaerfen

Verantwortliche Stelle, Rechtsgrundlagen je Modul, VVT (Art. 30) und ggf. DSFA
muessen vor Pilotbetrieb freigegeben sein.

## Cookies und TDDDG (vormals TTDSG)

§ 25 TDDDG verlangt Einwilligung fuer nicht notwendige Zugriffe auf Endgeraete.
Dieses Produkt setzt absichtlich **keine** Analyse-, Marketing- oder Social-
Cookies. Notwendige Cookies:

| Cookie | Zweck | Einwilligung |
| --- | --- | --- |
| `rwsth_session` | Anmeldung / Sitzung | nein (technisch notwendig) |
| `rwsth_csrf` | CSRF-Schutz | nein (technisch notwendig) |

Transparenz: Seite `/datenschutz/`. Kein Cookie-Banner fuer Opt-in-Tracking.
PWA-Service-Worker und lokaler Installationshinweis speichern keine Werbe-IDs.
Werden spaeter Analyse-Tools eingefuehrt, ist vorher ein Consent-Banner und eine
Rechtspruefung noetig.

## EU-KI-Verordnung (AI Act)

- Das Wachbuch ist klassische SSR-/PWA-Software ohne eingebettetes Modell, das
  ueber Personen inferiert.
- Es erzeugt keine Rankings, Scores oder Verhaltensprofile von Beschaeftigten.
- Externe KI-Werkzeuge in der **Entwicklung** (z. B. Coding-Assistenten) gehoeren
  nicht zum betriebenen Produkt; der Betreiber bleibt fuer eigene KI-Einsaetze
  verantwortlich.
- Verboten im Betrieb: Audit- oder Aufgabendaten als Social Scoring oder zur
  heimlichen Leistungsueberwachung zu nutzen.

Aendert sich das Produkt (z. B. KI-gestuetzte Schichtvorschlaege), ist eine neue
AI-Act- und Datenschutzpruefung erforderlich.

## Oeffentlicher Dienst NRW

Fuer kommunale oder landesnahe Rettungsdienststellen typischerweise relevant:

- DSG NRW und spezielle Regelungen fuer oeffentliche Stellen
- LPVG NRW § 72: Mitbestimmung bei technischen Einrichtungen, die geeignet sind,
  Verhalten oder Leistung zu ueberwachen (Login, Audit, Zeitstempel)
- keine Gemeinschaftskonten; persoenliche Konten und Rollenmodell
- Auskunfts-, Berichtigungs- und Loeschprozesse organisatorisch festlegen
- Loeschfristen je Datenart (Uebergaben, Audit, Kasse, Aufgaben) freigeben

Die Anwendung ersetzt weder Personalratsbeteiligung noch behördliche Freigaben.

## Versionierung

- Canonical Version: [`core/version.py`](../core/version.py) (`APP_VERSION`)
- Override: Umgebungsvariable `APP_VERSION`
- Anzeige: Footer und JSON-Feld `version` unter `/healthz/`
- Aenderungen: [`CHANGELOG.md`](../CHANGELOG.md) nach Keep-a-Changelog / SemVer
- Image-Label: `org.opencontainers.image.version` im Dockerfile

Empfohlene Nummernkreise:

- `0.x.y` vor formalem Go-live
- Patch: Sicherheits-/Bugfixes ohne Schemabruch
- Minor: neue Module oder Rueckwaertskompatible Features
- Major: brechende Migrationen oder Auth-Wechsel

## Updates und Rollback

Siehe ausfuehrlichen Ablauf in [`OPERATIONS.md`](OPERATIONS.md). Mindeststandard:

1. Changelog und Migrationshinweise lesen
2. Backup + Restore-Test
3. Abhaengigkeiten/Image-Digest pruefen und scannen
4. Staging oder Wartungsfenster
5. `docker compose up -d --build`, Healthcheck inkl. Versionsfeld
6. Fachsmoke: Login, Uebergabe, Tagesaufgaben, optional Feeds
7. Bei Stoerung: vorheriges Image + Dump-Restore, keine manuellen Tabellenfixes

## Betreiber-Checkliste (Ergaenzung)

- [ ] Verantwortliche Stelle und anwendbares Recht (DSG NRW / BDSG / Kirche) bestimmt
- [ ] VVT und Betroffeneninformation freigegeben
- [ ] Cookie-/Datenschutzseite verlinkt und inhaltlich angepasst
- [ ] AI-Act-Pruefung dokumentiert (Produkt ohne KI-System)
- [ ] Personalvertretung zu Login/Audit/Aufgaben beteiligt
- [ ] Versions- und Updateprozess im Betriebshandbuch verankert
