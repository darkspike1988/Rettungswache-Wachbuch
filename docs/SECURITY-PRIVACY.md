# Datenschutz und Sicherheit

## Privacy by Design

- Keine Felder fuer Patienten-, Diagnose-, Einsatznummern- oder Alarmdaten.
- Uebergabeformular mit sichtbarem Verbot solcher Inhalte.
- Geburtstage standardmaessig aus und jederzeit widerrufbar.
- Kaffeekasse als nachvollziehbares Ledger statt stiller Aenderungen.
- Audit speichert Feldnamen und Ereignisse, nicht die fachlichen Freitexte.
- Keine Rankings, Lesestatistiken oder personenbezogene Leistungskennzahlen.

## Vor einem betrieblichen Pilotbetrieb klaeren

- verantwortliche Stelle und anwendbares Recht: DSG NRW/LPVG,
  BDSG/BetrVG oder kirchliches Datenschutzrecht
- konkrete Rechtsgrundlage je Modul und Verzeichnis der Verarbeitungstaetigkeiten
- DSFA-Schwellenwertpruefung, gegebenenfalls vollstaendige DSFA
- Beteiligung und Freigabe durch Datenschutz, Informationssicherheit und
  Betriebs-/Personalrat beziehungsweise Mitarbeitervertretung
- abgestimmte Rollen, Loeschfristen, Korrekturverfahren und Auswertungsverbote
- Betroffeneninformationen und Verfahren fuer Auskunft, Berichtigung, Loeschung
  sowie Datenschutzverletzungen

## Technische Baseline

- TLS durch einen kontrollierten Reverse-Proxy vor dem Docker-Port
- lokaler HTTP-Zugriff nur ueber Loopback; sichere Cookies bei jedem TLS-Betrieb
- persoenliche lokale Konten, Login-Drosselung und keine gemeinsam genutzten Zugaenge
- sichere Session-Cookies, CSRF-Schutz, CSP und restriktive Browser-Header
- serverseitige Objekt- und Rollenpruefung
- separate Datenbank ohne veroeffentlichten Port
- Abhaengigkeits-, Container- und Anwendungsscan vor Go-live
- Sicherheitsabnahme gegen OWASP ASVS 5.0 Level 2 als Ziel

Ein privates Netz ersetzt weder das Rollenmodell noch eine organisatorische
Freigabe.
