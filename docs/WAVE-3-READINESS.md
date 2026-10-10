# Wave-3-Abnahmen: Readiness-Bewertung

Stand: 10. Oktober 2026. Bewertung der Abnahme-Readiness für die offenen
Roadmap-Items R-015 bis R-020 (REMEDIATION-ROADMAP-2026-08.md). Diese
Bewertung ersetzt keine Abnahme; sie benennt, was vor der jeweiligen
Abnahme erledigt oder bereitgestellt werden muss.

## Bewertungsmatrix

| Item | Abnahme | Readiness | Begründung |
|---|---|---|---|
| R-015 | Externer Pentest / ASVS-L2 | **Hoch** | Sicherheits-Regressionstests als CI-Gate, CSP ohne unsafe-inline, MFA/Passkeys, Rate-Limiting DB-backed, Token-API versioniert + OpenAPI. Angriffsfläche ist dokumentiert (docs/SECURITY-PRIVACY.md, ASVS-L2.md). Pentester kann sofort starten; Scope-Liste existiert in der Roadmap |
| R-016 | Monitoring + Incident-Probe | **Mittel** | /healthz, Correlation-IDs, strukturierte Request-Logs (wachbuch.requests), Gunicorn- und Postgres-Tuning vorhanden. Fehlt: Alarmierung (kein definiertes Alert-Backend), Health-Dashboard, Incident-Runbook existiert aber ist ungetestet |
| R-017 | Offsite-Backup + Restore-Nachweis | **Mittel** | backup/restore-Skripte, Least-Privilege-Backuprolle (R-010), Restore-Test-Container in docker-compose vorhanden. Fehlt: verschlüsseltes Offsite-Ziel, dokumentierte RPO/RTO, automatisierter Restore-Nachweis |
| R-018 | Barrierefreiheitsabnahme | **Mittel** | High-Contrast-Theme (Web + App folgt prefers-contrast), Design-System-Regeln, Fokus-Verbesserungen R-008. Fehlt: Screenreader-Test (NVDA/VoiceOver), 400-%-Zoom-Reflow-Nachweis, Abnahme durch reale Nutzer |
| R-019 | Last- und Resilienztest | **Mittel-hoch** | DB-Indexes (Migration 0020), Redis-Cache, Gunicorn-Worker-Tuning, Rate-Limits. Fehlt: definierter Lasttest (k6/locust o.ä.), Messung unter großem Team, DB-Ausfall-Wiederanlauf-Nachweis |
| R-020 | E2EE-Schlüsselverifikation | **Niedrig** | E2EE funktional (Chat/Post, ciphertext-only server), aber keine Fingerprints/QR-Verifikation, kein signierter nativer Client mit reproduzierbaren Builds. Größter offener Punkt – konzeptionelle Entscheidung erforderlich |

## Empfohlene Reihenfolge

1. **R-017 zuerst** – Backup ist die grundlegendste Versicherung und am
   schnellsten mit vorhandener Infrastruktur umsetzbar (Skripte existieren).
2. **R-016 parallel** – Alarmierung auf Basis der vorhandenen Logs/healthz
   ist ein begrenzter Engineering-Aufwand und dehnt sich nicht in die
   Fachlogik aus.
3. **R-015 als nächstes** – externe Prüfung profitiert davon, dass R-016/R-017
   bereits Stands haben; Scope-Liste steht, keine Blocker im Code.
4. **R-019** – nach R-015, damit Erkenntnisse des Pentests in den Lasttest
   einfließen.
5. **R-018** – parallel zu R-019 möglich; Nutzer aus dem Wachbetrieb
   einbinden (siehe GO-LIVE-CHECKLIST).
6. **R-020 zuletzt** – konzeptionelle Arbeit (Fingerprint-/QR-Design,
   reproduzierbare Builds), kein Abnahme-Blocker für Pilotbetrieb, aber
   notwendig für das langfristige E2EE-Vertrauensmodell.

## Vorbedingungen je Abnahme (kompakt)

- **R-015**: Testfenster + Staging-Instanz mit realitätsnahen Daten;
  Scope-Definition aus der Roadmap als Vertrag.
- **R-016**: Alert-Kanal (z.B. Healthchecks auf /healthz, Log-Alarmierung
  auf ERROR-Rate), Incident-Runbook-Trockenübung mit Zeitmessung.
- **R-017**: Offsite-Ziel (verschlüsselt, z.B. Object Storage/Borg-Repo),
  RPO/RTO-Vorgabe vom Betreiber, automatisierter Restore in frischer
  Compose-Umgebung mit Assert auf Fachdaten.
- **R-018**: Testgeräte (Windows + NVDA/JAWS, iOS + VoiceOver), Checkliste
  aus ROADMAP-Item, mindestens zwei reale Nutzer.
- **R-019**: Lasttest-Werkzeug, definiertes Szenario (Wachgröße, Chat- und
  Auditvolumen), Erfolgskriterien (p95-Latenz, Fehlerquote).
- **R-020**: Konzeptentscheidung (Fingerprint-Format, QR-Ablauf,
  Build-Reproduzierbarkeit), danach Implementierung und Abnahme.
