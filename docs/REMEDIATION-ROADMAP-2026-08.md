# Review-Remediation-Roadmap

Stand: 10. August 2026. Grundlage: technische, Sicherheits-, Design- und Integrationsreviews bis Server `0.16.x` / Client `0.6.x`. Diese Roadmap ist die operative Quelle für Folgeagenten. Sie ersetzt keine externe Sicherheits-, Datenschutz- oder Barrierefreiheitsprüfung.

## Statuslegende

- `[x]` umgesetzt und durch vorhandene Regressionstests/CI abgesichert
- `[~]` wesentliche Teile umgesetzt, externe/manuelle Abnahme oder Restarbeit offen
- `[ ]` offen

## Zielzustand

Das Wachbuch erreicht einen reproduzierbar getesteten Pilotstand mit klarer Produktgrenze, sicherer Webausgabe, belastbaren Betriebsprozessen, zugänglichen Kernabläufen und nachvollziehbarer Lieferkette. Produktionsfreigabe erfolgt erst, wenn die technischen Gates grün sind und `GO-LIVE-CHECKLIST.md` sowie die externen Wave-3-Abnahmen abgeschlossen sind.

## Reihenfolge

```text
Wave 0  Sofortige Web-Sicherheitsfehler
Wave 1  Code-, UX- und Dokumentationshärtung
Wave 2  Betrieb, Lieferkette und asynchrone Verarbeitung
Wave 3  Unabhängige Abnahme und Produktionsfreigabe
Wave 4  Stärkeres E2EE-Vertrauensmodell
```

## Wave 0 – P0 Web-Sicherheit

### [~] R-001 CSP-kompatible verschlüsselte Post

Empfängerauswahl und JSON-Einbettung wurden CSP-kompatibel auf DOM-APIs/`json_script` umgestellt. Offen bleibt die vollständige manuelle Browser-/Screenreader-Abnahme des gesamten E2EE-Flows.

### [x] R-002 Sichere JSON-Einbettung

Betroffene Chat-/Post-Templates verwenden Djangos `json_script`; unsichere `|safe`-JSON-Sinks wurden entfernt und Benutzerwerte werden nicht als HTML interpretiert.

### [x] R-003 Sicherheitsregressionstests

`core/test_security_regressions.py` prüft JSON-Sinks, CSP, Script-Reihenfolge, Navigation und Redirect-Schutz. Die Gates laufen in der regulären CI.

### [x] R-021 MFA-Durchsetzung, Push-Endpoint-Allowlist, CSP-Kaffeekasse

Umgesetzt und in den 0.16-Integrationsstand übernommen:

- Token-Ausgabe respektiert die MFA-Pflicht und unterscheidet `mfa_required` / `mfa_setup_required`.
- Push-Subscriptions akzeptieren nur HTTPS/443 ohne Credentials und nur Hosts aus `PUSH_ALLOWED_ENDPOINT_HOSTS` bzw. zulässige Host-Suffixe.
- IBAN-Kopie-Handler liegt in `core/static/core/app.js`; kein CSP-blockiertes Inline-Skript.
- MFA-Fehlercodes sind Teil des kanonischen API-Fehlervertrags.

**Restgrenze:** Web-MFA-Setup/Durchsetzung weiterhin separat im manuellen Auth-Review prüfen.

## Wave 1 – Anwendung und UX

### [x] R-004 E2EE-Versprechen an Bedrohungsmodell angleichen

UI- und Sicherheitsdokumentation unterscheiden Schutz gespeicherter Daten von einem aktiv kompromittierten Server/Webclient. Stärkeres Vertrauensmodell bleibt R-020.

### [~] R-005 Aufgaben-Race-Conditions schließen

Initialisierung und Abschluss/Wiedereröffnung verwenden Datenbanksperren. Parallele Last-/Resilienzabnahme bleibt Teil R-019.

### [x] R-006 Scheme-relative Redirects blockieren

Security-Middleware neutralisiert `Location: //…`; Regressionstest und CI sind vorhanden. Direkte Zielvalidierung mit `url_has_allowed_host_and_scheme` bleibt Best Practice bei künftigen View-Refactorings.

### [~] R-007 Vier globale Navigationsziele

Mobile/Desktop-Hauptnavigation folgt `Übersicht`, `Übergaben`, `Kalender`, `Mehr`. Reale Nutzerabnahme bleibt Wave 3.

### [~] R-008 Fokus und mobile Wochenansicht

Fokusindikator, Forced-Colors-Fallback, ausreichende Zielgrößen und mobile Wochenliste sind implementiert. 400-%-Zoom/Screenreader-Abnahme bleibt R-018.

### [x] R-009 Zugänglicher Entsperrdialog statt `window.prompt`

Der Entsperrflow verwendet einen eigenen zugänglichen Dialog mit beschriftetem Eingabefeld, Fehlerstatus, Anzeigen/Verbergen, Abbrechen, Fokusmanagement und Session-Lock. `window.prompt` wurde aus diesem Kernpfad entfernt. Regressionstests sichern den Flow ab.

### [x] R-014 Fehlerseiten und API-Konsistenz

Umgesetzt:

- zentrale strukturierte JSON-Fehlerantworten
- stabile Fehlercodes einschließlich MFA-Codes
- Korrelations-ID in API-Antworten/Logging
- eigene Fehlerhandler statt Stacktrace-Ausgabe an Clients
- Client kann neuen Vertrag und Legacy-Fehler lesen

Kanonischer Vertrag ist in `docs/API.md` und `core/api/openapi_v1.yaml` dokumentiert.

## Wave 2 – Betrieb und Lieferkette

### [~] R-010 Least-Privilege-Backuprolle

Dauerhafte Rolle `rwsth_backup` besitzt nur die für Dumps notwendigen Leserechte; Web läuft als `rwsth_app`. Restore mit Owner-Rechten ist explizit/kurzlebig. Offen bleiben verschlüsseltes Offsite-Ziel und regelmäßig nachgewiesener Restore (R-017).

### [x] R-011 Gemeinsames Rate Limiting und Proxy-Vertrauen

DB-basiertes `RateLimit`-Model mit `select_for_update`, gehashte Schlüssel über `RATELIMIT_KEY_SALT` und explizites `TRUSTED_PROXY` für `X-Forwarded-For`. Regressionstests verhindern triviale Proxy-/Worker-Umgehung.

### [~] R-012 CI-/Supply-Chain-Gates

Vorhanden sind u. a. Python-Compile, JavaScript-Syntax, Django-Migrationscheck, `check --deploy`, Tests und isolierter PostgreSQL/Docker-Pfad. Clientseitig existieren Flutter-/Android-/iOS-/Dependency-Security-Gates und SBOM-Artefakte.

Noch offen/zu vertiefen:

1. Ruff Format/Lint mit dokumentierter Baseline
2. vollständiger Dependency-/Container-Scan
3. CodeQL/SAST und Secret Scan
4. Server-SBOM + Build-Provenance
5. Browser-Smoke-Test, CSP-Konsole und Axe-Core

Actions und Images weiterhin auf unveränderliche SHAs/Digests pinnen.

### [x] R-013 Push-Outbox

Externe Push-Aufrufe laufen nicht mehr im Gunicorn-Fachrequest. `PushOutbox` speichert deduplizierte Jobs; der Worker verarbeitet Retry/Backoff, entfernt ungültige 404/410-Subscriptions und besitzt begrenzte Aufbewahrung/Cleanup. Betriebsmonitoring der Queue bleibt R-016.

## 0.16 Wachalltag – Integrationsstatus

### [x] Persistente Demo-Parität

Server und Client besitzen denselben produktiven Kernvertrag für:

- Mängel + Ereignis-/Audit-Verlauf
- authentifizierte Mängelfotos
- Fahrzeug-/Gerätestatus
- Schlüssel-/Pool-Ausgabe
- Übergabe-Quittierung
- wiederkehrende Checklisten
- leichte Stationsauswertung
- token-/servergebundenes Offline-Lesen im Client

### [x] Mobile Source of Truth

`darkspike1988/Wachbuch-Client` ist die kanonische Flutter-/iOS-/Android-Quelle. Der historische `clients/wachbuch-mobile/`-Spiegel im Server-Repo darf nicht zurückpubliziert werden; das frühere Force-Publish-Skript ist deaktiviert.

### [x] Request-Wiederholung / Datenintegrität

Nicht-idempotente Client-Mutationen wie Token-Erzeugung, Mangelanlage, Foto-Upload, Asset-/Inventar-Stammdaten und Checklistenabschluss werden nicht automatisch erneut gesendet. Sichere Reads bzw. serverseitig idempotente Zustandsoperationen dürfen Retry verwenden.

### [~] Post-Merge-Hardening

PR #54 schließt zwei in der Nachkontrolle gefundene Edge Cases:

- stark überfällige wiederkehrende Checks werden nach Abschluss entlang ihrer Kadenz bis zur ersten zukünftigen Fälligkeit fortgeschrieben
- Bilder werden zusätzlich zu MIME/Signatur mit Pillow vollständig validiert und auf 25 Megapixel begrenzt
- Owner-Zuordnung verlangt aktiven Django-User plus aktive Stationsmitgliedschaft

Status erst nach grünem finalem PR-Head auf `[x]` setzen.

## Wave 3 – Pilot- und Produktionsabnahme

### [ ] R-015 Externe ASVS-L2-Prüfung und Penetrationstest

Schwerpunkte: Rollen-/Stationsisolation, Auth/MFA/Passkeys, API-Tokens, SSRF, PWA-/Mobile-Cache, Upload, E2EE-Schnittstellen, CSP und Admin-Grenzen.

### [ ] R-016 Monitoring und Incident-Probe

Health, Fehlerquote, Queue/Worker, DB, Backupalter, Zertifikate, Speicher und ungewöhnliche Auth-Fehler alarmieren. Incident-Runbook praktisch üben.

### [ ] R-017 Verschlüsseltes Offsite-Backup und Restore-Nachweis

RPO/RTO festlegen; automatisierter Restore in isolierter Umgebung; Ergebnis und Backupalter sichtbar. Lokales Kurzzeit-Backup allein reicht nicht.

### [ ] R-018 Barrierefreiheitsabnahme

- Tastatur und 400-%-Zoom
- Reflow bei 320 CSS-Pixel
- NVDA/JAWS unter Windows
- VoiceOver auf iPhone/iPad
- Kontrast, Fokus, Fehler, Auth/MFA, Tabellen, Dialoge
- reale Nutzer aus dem Wachbetrieb

### [ ] R-019 Last- und Resilienztest

Gunicorn/DB-Grenzen, große Teams, Chat-/Auditwachstum, Feedfehler, langsame Pushziele, parallele Fachmutationen, Neustart während Migration und Wiederanlauf nach DB-Ausfall prüfen.

## Wave 4 – stärkeres E2EE-Vertrauensmodell

### [ ] R-020 Schlüsselverifikation und unabhängiger Client

Optionen bewerten und dokumentieren:

- sichtbare Schlüssel-Fingerprints/Sicherheitsnummern
- QR-Verifikation zwischen Kollegen
- Key-Change-Warnungen und nachvollziehbares Schlüsselverzeichnis
- signierter nativer Client mit reproduzierbaren Builds
- Migration/Backup bei Schlüsselwechsel

Erst danach darf ein Schutzversprechen gegen einen aktiv böswilligen Serverbetreiber erwogen werden.

## Agenten-Handoff

Bei jeder Fortsetzung zuerst `AGENTS.md`, diese Roadmap, `docs/API.md` und `docs/CLIENT.md` lesen. Keine Mobile-Änderung im historischen Server-Mirror beginnen. Sicherheits- oder Betriebsänderungen erhalten eine Roadmap-ID bzw. einen klar abgegrenzten PR mit Ursache, Risiko, Umsetzung, negativen Tests, Betriebsauswirkung, Rollback und verbleibenden Grenzen.
