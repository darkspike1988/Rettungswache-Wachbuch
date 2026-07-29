# Changelog

## Unreleased

- Uebergaben sind jetzt bearbeitbar (`/uebergaben/<id>/bearbeiten/`): Verfasserin
  oder Verfasser korrigiert eigene Eintraege, Schichtleitung und Admin auch
  fremde; jede Aenderung erhoeht die Version, schreibt eine unveraenderliche
  Revision und ein Audit-Ereignis. Die Aenderungshistorie zeigt den jeweiligen
  Titel der Fassung.
- Fehler behoben: Die Einstellungsseite und der Einrichtungsassistent liefen in
  einen HTTP 500, sobald in der Datenbank eine ungueltige IBAN stand. Die
  IBAN-Pruefung haengt jetzt am Feld statt an `Station.clean()` und wirkt nur
  noch in Formularen, die das Feld auch anzeigen.
- Fehler behoben: Gruppierte IBANs mit vielen Leerzeichen (lange auslaendische
  Formate) wurden wegen der Laengenpruefung vor dem Normalisieren abgewiesen.
- oeffentliche, nicht-interaktive Demo-Ansicht unter `/demo/` (Beispieldaten,
  kein Login, kein Schreibzugriff) zum Vorstellen des Projekts fuer andere
  Wachen/Kreise; verlinkt von der Fusszeile und der Anmeldeseite
- Anmelden-Link oben rechts im Kopfbereich fuer nicht angemeldete Besucher
- generischer Platzhalter-Logo (`core/static/core/logo-placeholder.svg`,
  kein geschuetztes Kennzeichen wie Rotes Kreuz/Stern des Lebens) fuer die
  Demo-Ansicht
- gefuehrter Einrichtungsassistent (`/einrichtung/`): neu angelegte Wachen
  fuehren den ersten Admin-Login in 3 einfachen Schritten (Name/Standort,
  Module, Fertig) statt der vollen Einstellungsseite; jederzeit ueberspringbar
- Kaffeekasse: konfigurierbare, gebuehrenfrei nutzbare Einzahlwege
  (PayPal.me-Link, Wero-Link/-Kontakt, IBAN mit Kontoinhaber für
  Echtzeitüberweisung), sichtbar für alle, editierbar nur für Admins
- helles und dunkles Farbschema per `prefers-color-scheme` (nachtdiensttauglich)
- Impressum, Datenschutz- und Barrierefreiheitserklärung unter `/impressum/`,
  `/datenschutz/`, `/barrierefreiheit/`, verlinkt aus der Fußzeile; Inhalte
  über `OPERATOR_*`/`DPO_CONTACT`/`ACCESSIBILITY_CONTACT` konfigurierbar
- neuer Compliance-Leitfaden `docs/COMPLIANCE-NRW.md`, Roadmap auf aktuellen
  Stand gebracht
- Kopfzeile zeigt Wachenname und Standort zentriert statt statischem Markennamen
- Standort der Wache unter `/einstellungen/` pflegbar (Feld `Station.location`)
- Wochenprotokoll (`/wochenprotokoll/`) gruppiert Uebergaben nach Tag analog zum
  Papier-Uebergabeprotokoll, inklusive Team-je-Tag und Allgemeines-Abschnitt
- Uebergaben koennen optional einem Tag zugeordnet werden (`for_date`)
- Wachenadresse (Strasse, PLZ, Ort, Kreis) unter `/einstellungen/` pflegbar
- optionale Ort-/Kreis-Ermittlung aus der Adresse ueber einen offenen,
  Nominatim-kompatiblen Geocoding-Dienst (`GEOCODING_HOST`, standardmaessig aus)
- Meldungen und Verkehr werden nach Ort/Kreis der Wache gefiltert, sobald
  dieser hinterlegt ist; ohne Angabe unveraendertes Verhalten
- Abfallkalender je Wache: Stationsadmins hinterlegen einen ICS-Abo-Link unter
  `/lage/?typ=muell`, kommende Abholtermine werden automatisch synchronisiert
- gemeinsame SSRF-gehaertete HTTP-Abrufschicht (`core/net.py`) fuer Feeds und
  Geocoding

## Unreleased - Open-Source-Basis

- portable Docker-Konfiguration ohne servergebundene Hosts und Datenbank-URLs
- sichere, stationsbezogene Einstellungsseite fuer Name und optionale Module
- lokaler Login und reproduzierbarer Erstadmin-Workflow ergaenzt
- Migrationen vom dauerhaften Webprozess getrennt
- Build-Kontext gegen Backups, Datenbanken und Bytecode abgesichert
- Adminzugriff auf fachliche und unveraenderliche Datensaetze eingeschraenkt
- GitHub-CI, Beitrags- und Sicherheitsrichtlinie vorbereitet
- Lizenz auf GNU AGPL v3 umgestellt

## 2026-07-28 - UI 0.2.0

- Dashboard auf aktive Uebergaben und die naechsten drei Termine reduziert
- globale Navigation auf Uebersicht, Uebergaben, Kalender und Mehr vereinfacht
- Schreibformulare auf eigene, lineare Seiten verschoben
- Uebergaben fachlich nach Dringlichkeit sortiert und Archiv getrennt
- Feedansicht nach Meldungen und Verkehr getrennt sowie paginiert
- Kassenbuch und Audit als semantische responsive Tabellen umgesetzt
- mobile Navigation, 768-Pixel-Tablet-Reflow und 44-Pixel-Touchziele eingefuehrt
- offene Designquellen und zehn verbindliche UX-Regeln dokumentiert

## 2026-07-28 - Tailnet-Pilot 0.1.0

- Django/PostgreSQL-Projektbasis und eigenes Git-Repository angelegt
- Uebergaben, Kalender, Geburtstage, Kaffeekasse, Teamrollen und Audit umgesetzt
- offizielle Guetersloh-/Bielefeld-Feeds und Bielefelder Verkehrsdaten integriert
- Tailscale-Identitaet, Loopback-Bindung und getrennte Docker-Netze eingerichtet
- eingeschraenkte PostgreSQL-Rollen und Append-only-Rechte gesetzt
- taegliches lokales Backup, Restic-Offsite-Pfad und Restore-Test eingerichtet
- 21 automatisierte Tests, Deployment-Checks und Trivy-Scans bestanden
- Pilot ausschliesslich im Tailnet bereitgestellt; oeffentliche Domain bleibt offline
