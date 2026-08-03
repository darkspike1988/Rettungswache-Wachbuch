# Review-Remediation-Roadmap

Stand: 3. August 2026. Grundlage: technische und Design-Review des `main`-Stands
0.14.2. Diese Roadmap ist die operative Quelle fuer Folgeagenten. Sie ersetzt
keine externe Sicherheits-, Datenschutz- oder Barrierefreiheitspruefung.

## Zielzustand

Das Wachbuch erreicht einen reproduzierbar getesteten Pilotstand mit klarer
Produktgrenze, sicherer Webausgabe, belastbaren Betriebsprozessen, zugänglichen
Kernablaeufen und nachvollziehbarer Lieferkette. Produktionsfreigabe erfolgt erst,
wenn Wave 0–3 abgenommen und die `GO-LIVE-CHECKLIST.md` abgeschlossen sind.

## Reihenfolge

```text
Wave 0  Sofortige Web-Sicherheitsfehler
Wave 1  Code-, UX- und Dokumentationshaertung
Wave 2  Betrieb, Lieferkette und asynchrone Verarbeitung
Wave 3  Unabhaengige Abnahme und Produktionsfreigabe
Wave 4  Staerkeres E2EE-Vertrauensmodell
```

## Wave 0 – P0 Web-Sicherheit

### [x] R-001 CSP-kompatible verschluesselte Post

**Problem:** Die Empfaengerauswahl wurde durch ein Inline-Skript erzeugt, waehrend
`script-src 'self'` Inline-Skripte blockiert.

**Umsetzung:** Empfaenger werden in `core/static/core/json_data.js` mit DOM-APIs
erzeugt. Das Inline-Skript wurde entfernt.

**Abnahme:**

- keine ausführbaren Inline-Skripte im Posteingang
- Empfaenger mit Schluesseln erscheinen als Checkboxen
- keine CSP-Verletzung im Browser
- Versand mit mindestens einem Empfaenger funktioniert

**Dateien:** `templates/core/secure_mail_inbox.html`,
`core/static/core/json_data.js`, `templates/base.html`.

### [x] R-002 Sichere JSON-Einbettung

**Problem:** `|safe` in JSON-Scriptbloecken ermoeglichte HTML-/Stored-XSS-Risiken.

**Umsetzung:** Alle betroffenen Chat-/Post-Templates verwenden Djangos
`json_script`. Die Kompatibilitaet mit den derzeit vorserialisierten
Context-Werten wird ohne HTML-Parsing hergestellt.

**Abnahme:**

- kein `|safe` in den vier E2EE-Templates
- kein `innerHTML` fuer Benutzer-, Nachrichten- oder Empfaengerdaten
- Testdaten mit `</script><img src=x onerror=alert(1)>` bleiben Text/JSON

### [x] R-003 Sicherheitsregressionstests

**Umsetzung:** `core/test_security_regressions.py` prueft JSON-Sinks, CSP,
Script-Reihenfolge, Navigation und Redirect-Schutz.

**Abnahme:** normaler Django-Testlauf ist gruen.

## Wave 1 – Anwendung und UX

### [x] R-004 E2EE-Versprechen an Bedrohungsmodell angleichen

**Umsetzung:** UI- und Sicherheitsdokumentation unterscheiden Schutz gespeicherter
Daten von einem aktiven kompromittierten Server/Webclient. Keine Aussage mehr,
dass der Server generell keine Klartexte erlangen koenne.

**Restgrenze:** Fingerprints, Key Transparency und unabhaengig signierte Clients
sind R-020.

### [x] R-005 Aufgaben-Race-Conditions schliessen

**Umsetzung:** Initialisierung sperrt die stabile Stationszeile; Abschluss/
Wiedereroeffnung sperrt die Aufgabenzeile, auch wenn noch keine Completion existiert.

**Abnahme:** parallele Erstaufrufe erzeugen eine Standardvorlage; paralleles
Abhaken erzeugt maximal einen Abschluss und keinen 500-Fehler.

### [x] R-006 Scheme-relative Redirects blockieren

**Umsetzung:** Security-Middleware ersetzt `Location: //...` durch `/`.

**Folgearbeit:** Direkte Zielvalidierung mit `url_has_allowed_host_and_scheme`
bei jeder nutzerbeeinflussten Weiterleitung bleibt bevorzugt, sobald die betroffene
View refaktoriert wird.

### [x] R-007 Vier globale Navigationsziele

**Umsetzung:** Mobile/desktop Hauptnavigation folgt wieder der Designregel
`Uebersicht`, `Uebergaben`, `Kalender`, `Mehr`. Chat bleibt unter `Mehr` erreichbar;
Chatseiten markieren `Mehr` als aktiv.

### [x] R-008 Fokus und mobile Wochenansicht

**Umsetzung:** zweifarbiger Fokusindikator, Forced-Colors-Fallback, 44-Pixel-
Chat-/Empfaengerziele und einspaltige Wochenliste unter 48 rem.

**Abnahme:** 320 CSS-Pixel ohne horizontale Wochenmatrix; Tastaturfokus auf hellen
und dunklen Flaechen sichtbar.

### [ ] R-009 Zugaenglicher Entsperrdialog statt `window.prompt`

**Plan:** eigenes `<dialog>` mit Label, Fehlerstatus, Anzeigen/Verbergen,
Abbrechen, Fokusmanagement und „jetzt sperren“. `window.prompt` komplett entfernen.

**Tests:** Tastatur, Escape, VoiceOver/NVDA, falsche Passphrase, Session-Lock.

## Wave 2 – Betrieb und Lieferkette

### [ ] R-010 Least-Privilege-Backuprolle

**Plan:** dauerhaften Backup-Container vom DB-Owner trennen. Eigene Login-Rolle
mit nur fuer `pg_dump` benoetigten Rechten; Owner-Zugang nur fuer kurzlebige,
manuell gestartete Restore-/Migrationsschritte.

**Abnahme:** Backup gelingt; Backuprolle kann keine Fachzeile aendern/loeschen;
Restore-Test in isolierter DB ist gruen; Offsite-Ziel ist verschluesselt.

### [ ] R-011 Gemeinsames Rate Limiting und Proxy-Vertrauen

**Plan:** registrierungsbezogene Limits in Redis oder transaktionaler DB-Tabelle,
IP nur hinter explizit vertrautem Proxy auswerten, gehashten Schluessel verwenden,
Aufbewahrung dokumentieren.

**Abnahme:** mehrere Gunicorn-Worker teilen denselben Zaehler; gefaelschtes
`X-Forwarded-For` umgeht das Limit nicht.

### [ ] R-012 CI-/Supply-Chain-Gates

**Plan in getrennten kleinen PRs:**

1. `manage.py check --deploy` und Compile-Check
2. Ruff Format/Lint mit dokumentierter Baseline
3. Dependency-Audit und Container-Scan
4. CodeQL/SAST und Secret Scan
5. SBOM plus Build-Provenance
6. Browser-Smoke-Test, CSP-Konsole und Axe-Core

Actions und Images weiterhin auf unveraenderliche SHAs/Digests pinnen.

### [ ] R-013 Push-Outbox

**Plan:** Transaktion schreibt einen Outbox-Datensatz; separater Worker sendet
Push mit Retry, Backoff, Idempotenz und begrenzter Aufbewahrung. Kein externer
Netzaufruf im Gunicorn-Request.

### [ ] R-014 Fehlerseiten und API-Konsistenz

**Plan:** eigene 400/403/404/429/500-Seiten, einheitliche JSON-Fehlercodes,
Korrelations-ID ohne personenbezogene Nutzdaten, keine Stacktraces.

## Wave 3 – Pilot- und Produktionsabnahme

### [ ] R-015 Externe ASVS-5.0-L2-Pruefung und Penetrationstest

Schwerpunkte: Rollen-/Stationsisolation, Auth/MFA/Passkeys, API-Tokens, SSRF,
PWA-Cache, Upload, E2EE-Schnittstellen, CSP und Admin-Grenzen.

### [ ] R-016 Monitoring und Incident-Probe

Health, Fehlerquote, Queue/Worker, DB, Backupalter, Zertifikate, Speicher und
ungewoehnliche Auth-Fehler alarmieren. Incident-Runbook praktisch ueben.

### [ ] R-017 Verschluesseltes Offsite-Backup und Restore-Nachweis

RPO/RTO festlegen; automatisierter Restore in isolierter Umgebung; Ergebnis und
Backupalter sichtbar. Lokales Sieben-Tage-Verzeichnis allein reicht nicht.

### [ ] R-018 Barrierefreiheitsabnahme

- Tastatur und 400-Prozent-Zoom
- Reflow bei 320 CSS-Pixel
- NVDA/JAWS unter Windows
- VoiceOver auf iPhone/iPad
- Kontrast, Fokus, Fehler, Auth/MFA, Tabellen, Dialoge
- reale Nutzer aus dem Wachbetrieb

### [ ] R-019 Last- und Resilienztest

Gunicorn/DB-Grenzen, grosse Teams, Chat-/Auditwachstum, Feedfehler, langsame
Pushziele, Neustart waehrend Migration und Wiederanlauf nach DB-Ausfall pruefen.

## Wave 4 – staerkeres E2EE-Vertrauensmodell

### [ ] R-020 Schluesselverifikation und unabhaengiger Client

Optionen bewerten und dokumentieren:

- sichtbare Schluessel-Fingerprints/Sicherheitsnummern
- QR-Verifikation zwischen Kollegen
- Key-Change-Warnungen und nachvollziehbares Schluesselverzeichnis
- signierter nativer Client mit reproduzierbaren Builds
- Migration/Backup bei Schluesselwechsel

Erst danach darf ein Schutzversprechen gegen einen aktiv boeswilligen
Serverbetreiber erwogen werden.

## Agenten-Handoff

Bei jeder Fortsetzung zuerst `AGENTS.md` lesen und genau eine Roadmap-ID waehlen.
PR-Titel beginnen mit der ID, zum Beispiel:

```text
R-010: restrict backup database privileges
```

PR-Beschreibung enthaelt Ursache, Risiko, Umsetzung, negative Tests,
Betriebsauswirkung, Rollback und verbleibende Grenzen.
