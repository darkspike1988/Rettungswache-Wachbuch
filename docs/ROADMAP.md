# Roadmap

## Bereits umgesetzt

- Docker-Deployment mit lokalem Login oder Tailscale
- Rollen, Uebergaben, Wochenprotokoll (Kalenderwoche mit Team je Tag),
  Kalender, Geburtstage, Kaffeekasse und Behoerdenfeeds
- Wachenname und Standort zentriert im Kopfbereich; Adresse sowie Ort/Kreis
  ueber einen offenen Geocoding-Dienst ermittelbar
- Meldungen und Verkehr nach Ort/Kreis der Wache gefiltert; Abfallkalender je
  Wache ueber ICS-Abo-Link
- Kaffeekasse mit konfigurierbaren, gebuehrenfrei nutzbaren Einzahlwegen
  (PayPal.me, Wero, Echtzeitueberweisung)
- helles und dunkles Farbschema (`prefers-color-scheme`, nachtdiensttauglich)
- Impressum, Datenschutz- und Barrierefreiheitserklaerung als Seiten-Geruest
  mit deutlich markierten Platzhaltern fuer die verantwortliche Stelle
- automatisierte Fach- und Zugriffstests

## Phase 1 - geschlossener Test

- reale Arbeitsablaeufe mit Testdaten durchspielen
- Rollenmatrix und Formulare mit dem Team vereinfachen
- Impressum-/Datenschutz-/Barrierefreiheitserklaerung mit echten Angaben der
  verantwortlichen Stelle fuellen (`OPERATOR_*`-Variablen, siehe README und
  `docs/COMPLIANCE-NRW.md`)
- Loeschfristen technisch umsetzen, sobald sie freigegeben sind
- Backup/Restore, Monitoring, Updates und Incident-Ablauf testen

## Phase 2 - formaler betrieblicher Pilot

- Datenschutz-/Mitbestimmungsunterlagen abschliessen (DSG NRW,
  Personalratsbeteiligung nach LPVG NRW, DSFA-Schwellenwertpruefung)
- verwaltete Benutzer und MFA-/Passkey-Strategie festlegen
- Barrierefreiheit nach EN 301 549/WCAG 2.1 AA extern pruefen und Erklaerung
  mit Pruefergebnis aktualisieren
- Audit-Export und automatisierte Restore-Tests ergaenzen

## Phase 3 - Produktion

- ASVS-L2-Sicherheitspruefung und Lasttest
- finalen Betriebs-, Support- und Notfallprozess abnehmen
- erst nach schriftlichem Go-live einen oeffentlichen DNS-Namen anbinden

Spaetere Optionen sind eine installierbare PWA, CalDAV-Export und weitere
offizielle Quellen (z.B. amtliche Wetterwarnungen). Chat, Patientendaten,
Dienstplanung und Uploads bleiben ausserhalb des Wachbuchs, solange kein
eigener freigegebener Zweck besteht.
