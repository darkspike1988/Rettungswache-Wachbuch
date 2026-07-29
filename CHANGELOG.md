# Changelog

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
