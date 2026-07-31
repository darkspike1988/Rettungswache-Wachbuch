# Roadmap

## Phase 0 - technische Basis

- Docker-Deployment mit lokalem Login und Reverse-Proxy
- Rollen, Uebergaben, Kalender, Tagesaufgaben, Geburtstage, Kaffeekasse und Behoerdenfeeds
- automatisierte Fach- und Zugriffstests

## Phase 1 - geschlossener Test

- reale Arbeitsablaeufe mit Testdaten durchspielen
- Rollenmatrix und Formulare mit dem Team vereinfachen
- Loeschfristen je Datenart organisatorisch freigeben; Feed-Retention und
  optionale Audit-Fristen sind technisch vorbereitet (`apply_retention`)
- Backup/Restore, Monitoring, Updates und Incident-Ablauf testen
- TOTP im Team erproben; Passkeys spaeter nachziehen
- verbleibende Befunde aus [`AUDIT-2026-07.md`](AUDIT-2026-07.md) abarbeiten

## Phase 2 - formaler betrieblicher Pilot

- Datenschutz-/Mitbestimmungsunterlagen abschliessen
- MFA-Pflicht (`MFA_REQUIRED`) und Passkey-Strategie festlegen
- barrierearme Nutzung und gemeinsame Wachenterminals pruefen
- Audit-Export und automatisierte Restore-Tests ergaenzen

## Phase 3 - Produktion

- ASVS-L2-Sicherheitspruefung und Lasttest
- finalen Betriebs-, Support- und Notfallprozess abnehmen
- erst nach schriftlichem Go-live einen oeffentlichen DNS-Namen anbinden

Die installierbare PWA ist Teil der Basis. Spaetere Optionen sind CalDAV-Export,
Web-Push fuer dringende Uebergaben und weitere offizielle Verkehrsdaten. Chat,
Patientendaten, Dienstplanung und Uploads bleiben ausserhalb des Wachbuchs,
solange kein eigener freigegebener Zweck besteht.
