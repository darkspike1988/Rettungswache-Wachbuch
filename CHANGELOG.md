# Changelog

## 0.3.0 - 2026-07-31

- Compliance-Doku zu DSGVO, TDDDG-Cookies, EU AI Act und NRW oeffentlichem Dienst
- Datenschutz-/Cookie-Transparenzseite unter `/datenschutz/` ohne Tracking-Banner
- oeffentliche Startseite unter `/` praesentiert das Projekt; Fachfunktionen erst nach Login
- Dashboard unter `/uebersicht/`; Logout und unauthentifizierte App-Routen fuehren zu Startseite bzw. Anmeldung
- sichtbare Produktmarke einheitlich `Wachbuch`; Header-Unterzeile zeigt den Stationsnamen
- sichtbare SemVer-Version in Footer, `/healthz/` und Image-Label
- dokumentierter Versions- und Update-/Rollback-Ablauf
- Tagesaufgaben-Modul nach Wandbogen: gruen taeglich, gelb Wochentag, blau zusaetzlich
- Heute-Liste, Wochenbogen, Vorlagenverwaltung und Audit fuer Erledigungen
- installierbare PWA mit Manifest, Service Worker, Icons und Offline-Hinweis
- App-Shell mit Safe Areas, Installationshinweis, Dringend-Badge und Schnellzugriff
- ICS-Export fuer einzelne Wachentermine
- Design der Oberflaeche fuer Standalone-Nutzung aufpoliert
- Tailscale-Header-Login und zugehoerige Konfiguration vollstaendig entfernt
- Authentifizierung nur noch ueber lokale Django-Konten hinter Docker/Reverse-Proxy
- Docker-Image mit Labels, ausfuehrbaren Startskripten und Healthcheck gestrafft
- Compose-Projektname und Image-Name vereinheitlicht; Stack-Dokumentation bereinigt
- Geburtstage speichern Tag/Monat nur noch bei aktivem Opt-in und pruefen echte Kalenderdaten
- Geburtstagsliste blendet inaktive Mitglieder aus
- erneute Teamfreigabe reaktiviert bestehende Mitgliedschaften statt in einen 500-Fehler zu laufen
- Kaffeekorrekturen sperren die Originalbuchung und fangen parallele Doppelkorrekturen ab
- Feedansicht zeigt nur aktivierte Quellen und benennt die Guetersloh-Datenluecke
- Migration setzt externe Meldungen nach dem Modul-Upgrade wieder auf Opt-in
- Audit-Dokument mit Funktionsueberblick und Folgeplan ergaenzt

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
