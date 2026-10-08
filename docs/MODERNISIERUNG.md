# Modernisierung: Schichtüberblick (Slice R-025)

Dokumentation des Funktionsslices *Schichtüberblick* im Rahmen der Modernisierungs-Roadmap.

## Roadmap-Zuordnung

- **Roadmap-ID:** `R-025`
- **Titel:** Druckbarer, read-only Schichtüberblick auf Basis bestehender Wachenmodelle
- **Bezug:** Ergänzt die Maßnahmen aus `docs/REMEDIATION-ROADMAP-2026-08.md` (IDs R-001 bis R-024 belegt; R-025 als neuer eindeutiger Punkt) sowie die Zielsetzung aus `docs/ROADMAP.md` (Wachalltag im Blick).
- **Status:** `[x]` umgesetzt und durch automatisierte Regressionstests belegt.
  *(Hinweis: Die unabhängige manuelle Browser- und A4-Druckabnahme erfolgt durch den Elternagenten und wird hier explizit nicht als bereits erfolgt behauptet.)*

---

## 1. Fachliche Produktgrenze und Zweck

Der Schichtüberblick fasst für die aktive Schicht die operative Gesamtlage einer Rettungswache zusammen. Er dient der schnellen Orientierung bei Wachablösung und Schichtbeginn.

### Nicht verhandelbare Grenzen
- **Keine Patienten- oder Behandlungsdaten:** Keine Diagnosen, Vitalwerte oder medizinischen Notizen.
- **Keine Einsatz- oder Alarmierungsdaten:** Keine Einsatznummern, Alarmzeiten oder Einsatzstellen.
- **Keine Personalakten:** Keine Qualifikationskontrollen oder arbeitsmedizinischen Daten.
- **Keine Leistungsbewertung:** Keine Ranglisten, keine Erledigungsquoten pro Mitarbeiter.
- **Kein Dienstplan:** Keine Schichtplanung oder Urlaubsverwaltung.
- **Kein rechtsverbindliches Protokoll:** Klarer Hinweis im UI, dass es sich um eine operative Arbeitsübersicht handelt; keine serverseitige Quittierungspflicht oder Signaturkette in diesem Slice.

---

## 2. Technischer Vertrag und Implementierung

### 2.1 Routing & HTTP-Methode
- **Endpunkt:** `GET /uebergaben/schichtueberblick/`
- **URL-Name:** `handover_shift_overview`
- **Methoden-Restriktion:** Strikt GET-only (`@require_GET`). POST-Requests werden mit HTTP 405 (*Method Not Allowed*) beantwortet.
- **Verlinkung:** In der Übergabenliste (`/uebergaben/`, `templates/core/handover_list.html`) über eine sekundäre Aktionsschaltfläche neben »Übergabe anlegen«.

### 2.2 Datenmodell & Queries
Es wurden **keine neuen Modelle und keine Migrationen** angelegt (`makemigrations --check --dry-run` liefert `No changes detected`).

Die Ansicht aggregiert ausschließlich bestehende Modelle der aktiven Station (`station = request.membership.station`):

1. **Offene & wichtige Übergaben (`HandoverEntry`):**
   - Nutzt die kanonische Helper-Funktion `prioritized_handovers(station)`.
   - Erledigte Übergaben (`status == DONE`) werden strikt ausgeschlossen.
   - Sortierung: Dringend vor Wichtig vor Normal, gefolgt von Status (Offen vor In Bearbeitung) und Aktualisierungszeitpunkt.
   - `select_related("author")` zur Vermeidung von N+1-Queries.

2. **Fahrzeuge und Geräte (`StationAsset`):**
   - Zeigt nur Einsatzmittel mit Klärungsbedarf (`exclude(status=StationAsset.Status.READY)`).
   - `select_related("updated_by")`.
   - Gibt Typ, Bezeichnung, Kennung, Status und Notiz aus.

3. **Offene Mängel (`Defect`):**
   - Zeigt aktive Mängel (`exclude(status=Defect.Status.DONE)`).
   - Sortiert nach Priorität (Dringend zuerst), Frist (`due_at`) und Erstellungsdatum.
   - `select_related("owner", "created_by")`.

4. **Heutige Wachenaufgaben (`StationTask`, `StationTaskCompletion`):**
   - **Feature-Flag:** Wird nur abgefragt und gerendert, wenn `station.tasks_enabled == True`.
   - Nutzt die bestehende Wandtafel-Logik: `ensure_default_station_tasks(station)` und `day_board(station, timezone.localdate())`.
   - Zeigt die 3 Bänder (Täglich, Wochentag, Zusatz) inklusive Erledigungsstatus.

5. **Fällige Prüfungen & Checklisten (`ChecklistSchedule`, `Checklist`):**
   - **Feature-Flag:** Wird nur abgefragt und gerendert, wenn `station.checklists_enabled == True`.
   - Zeigt aktive Checklisten mit fälligen Intervallen (`due_next <= now`).
   - `select_related("checklist")`.

### 2.3 Berechtigungen & Mandantenisolation
- Gesichert mit `@membership_required(CONTENT_ROLES)`.
- Rollen mit Zugriff: `member`, `shift_lead`, `cashier`, `admin`.
- **Rolle `auditor`:** Wird mit HTTP 403 (*PermissionDenied*) abgewiesen; Revisor sieht keine operativen Freitexte.
- **Unauthentifizierte Nutzer:** Werden mit HTTP 302 auf `/anmelden/?next=...` weitergeleitet.
- **Nutzer ohne aktive Mitgliedschaft:** Werden auf `/zugang/` umgeleitet.
- **Mandantentrennung:** Alle Abfragen sind strikt an `station=request.membership.station` gebunden. Ein Zugriff auf Fremdwachen-Daten ist unmöglich.

### 2.4 Serverzeit & UI-Hinweise
- Zeitstempel basiert auf realer lokaler Serverzeit (`timezone.localtime(timezone.now())`).
- Keine erfundenen Schichtzeiten.
- Prominenter Informationstext im Kopfbereich:
  *»Schichtüberblick – Wachenorganisation. Aktueller Arbeitsstand zur Schichtübergabe auf Grundlage bestehender Wachendaten. Keine Patienten-, Einsatz- oder Personaldaten. Dieser Überblick dient der operativen Orientierung und stellt kein rechtsverbindliches Übergabeprotokoll dar.«*

### 2.5 Barrierefreiheit & Design-System
- Gestaltet nach `Wachbuch Klar` (BOS-Tokens, Source Sans 3 lokal, keine CDNs).
- Automatische Template-Escaping-Mechanismen ohne unsichere `|safe`-Filter.
- Eigene Stylesheet-Datei: `core/static/core/shift_overview.css`.
- Keine Inline-Styles (`style="..."`), strikt konform mit der Content Security Policy (`style-src 'self'`).
- Touch-Ziele von mindestens 48×48 px für alle interaktiven Elemente.
- Responsive Darstellung: Bis 48rem Einspalten-Ansicht; kein horizontaler Overflow bei 320 CSS-Pixeln.

### 2.6 A4-Druckansicht (`@media print`)
- Druckauslösung über Tastenkombination (`Ctrl+P` / `Cmd+P`) oder barrierefreie Schaltfläche »Drucken (A4)« via globalem Event-Delegator (`data-action="print"` in `core/static/core/app.js`).
- Ausblenden von App-Header, Hauptnavigation (`.app-nav`), Footer, Bannern, Skip-Links und Aktionsbuttons.
- Schwarz-Weiß-/Graustufen-Optimierung mit hohem Kontrast.
- Vermeidung unschöner Seitenumbrüche: `break-inside: avoid;` / `page-break-inside: avoid;` für Tabellen, Zeilen, Abschnitte und Aufgabenblöcke.
- Seitenformat: `@page { size: A4 portrait; margin: 1.5cm 1.2cm; }`.

---

## 3. Nachweise und Qualitätssicherung

### 3.1 Automatisierte Testabdeckung (`core/test_shift_overview.py`)
Folgende 13 isolierte Tests sichern den Funktionsslice ab:

| Testname | Geprüfte Invariante |
|---|---|
| `test_anonymous_redirect` | Unauthentifizierter Zugriff leitet auf Login mit `next`-Parameter um. |
| `test_no_membership_redirect` | Authentifiziertes Konto ohne Wachenmitgliedschaft wird auf `/zugang/` geleitet. |
| `test_auditor_access_forbidden` | Auditor erhält HTTP 403 (kein Zugriff auf operative Freitexte). |
| `test_post_method_not_allowed` | POST auf den Endpunkt liefert HTTP 405. |
| `test_station_isolation` | Strikte Isolation: Daten von Fremdstationen tauchen unter keinen Umständen auf. |
| `test_done_handovers_excluded_and_prioritized` | Erledigte Übergaben (`status=DONE`) werden ausgeblendet; Dringend/Wichtig wird priorisiert. |
| `test_assets_filtering` | Nur eingeschränkte/defekte Assets erscheinen; einsatzklare Assets bleiben in der Einschränkungsliste verborgen. |
| `test_defects_filtering` | Erledigte Mängel werden ausgeblendet; offene Mängel erscheinen nach Priorität. |
| `test_optional_modules_disabled` | Bei deaktivierten Feature-Flags (`tasks_enabled=False`, `checklists_enabled=False`) erfolgen keine Queries und keine HTML-Abschnitte. |
| `test_optional_modules_enabled` | Bei aktivierten Flags werden heutige Aufgaben und fällige Checks korrekt gerendert. |
| `test_query_count_is_bounded` | Abfragen sind konstant (keine N+1-Queries bei wachsender Elementanzahl). |
| `test_link_in_handover_list` | Übergaben-Hauptliste verlinkt auf den neuen Endpunkt. |
| `test_ui_disclaimer_and_timestamp` | Stand-Zeitstempel und Hinweistext sind im gerenderten Dokument enthalten. |

### 3.2 Standardprüfungen

```bash
# 1. Migrationsprüfung (keine Änderungen)
DJANGO_SECRET_KEY=test-only DATABASE_URL=sqlite:///:memory: \
  /opt/data/services/rettungswache-wachbuch/.venv/bin/python manage.py makemigrations --check --dry-run --settings=config.test_settings
# Ergebnis: No changes detected

# 2. Syntaxprüfung der Frontend-Assets
node --check core/static/core/app.js
node --check core/static/core/json_data.js
# Ergebnis: 0 Fehler

# 3. Static-Files-Sammlung
DJANGO_SECRET_KEY=test-only DATABASE_URL=sqlite:///:memory: \
  /opt/data/services/rettungswache-wachbuch/.venv/bin/python manage.py collectstatic --noinput --dry-run --settings=config.test_settings
# Ergebnis: 146 Dateien erfasst (inklusive shift_overview.css)

# 4. Volle Testsuite
DJANGO_SECRET_KEY=test-only DATABASE_URL=sqlite:///:memory: \
  /opt/data/services/rettungswache-wachbuch/.venv/bin/python manage.py test --settings=config.test_settings
# Ergebnis: Alle Tests bestanden (307 Tests, 1 skipped, 0 failures, 0 errors)
```

---

## 4. Verbleibende Grenzen und Handoff

- **Keine Quittierung:** Dieser Slice implementiert rein die lesende Schichtübergabeübersicht. Ein interaktiver Quittierungsflow (`HandoverAck`) ist ein separater Schritt.
- **Keine PDF-Engine:** Die Ausgabe nutzt Browser-Printing (`@media print`). Keine serverseitigen PDF-Bibliotheken (wie Weasyprint/ReportLab), um Angriffsfläche und Abhängigkeiten gering zu halten.
- **Keine Auth-/MFA-/Middleware-Änderungen:** Der parallel entwickelte MFA-Fix in einem anderen Worktree bleibt unberührt.
- **Keine Demo-/Main-Änderungen:** Demo-Routen, Demo-Daten und Demo-Flags bleiben eingefroren.
- **Abnahme:** Die visuelle Browser- und Druckabnahme obliegt dem Elternagenten.
