# Changelog

## Unreleased

- Touchbedienung geschaerft: Hovereffekte gelten nur noch fuer echte
  Zeigegeraete, damit auf Tablet und Smartphone kein Hoverzustand nach dem
  Antippen haengenbleibt. Unter `pointer: coarse` wachsen Bedienziele und
  Eingabefelder auf 48 Pixel - das greift auch beim Tablet im Querformat, nicht
  erst bei schmalen Fenstern. `touch-action: manipulation` nimmt die
  Verzoegerung durch die Doppeltipp-Zoom-Erkennung.
- Mehrfachbenennungen entfernt: Der Wachenname stand auf jeder Seite bis zu
  dreimal (mittig im Kopf, neben der Rolle, in der Kontextzeile) - jetzt genau
  einmal. In der Teamliste heisst der Aktionslink `Bearbeiten` statt den Namen
  der Person zu wiederholen.
- Fortschrittsbalken der Feature-Tour folgt direkt der Scrollposition, Karten
  und Tagesbloecke tauchen beim Hereinscrollen auf (scroll-gesteuerte
  CSS-Animationen, nur wo der Browser sie unterstuetzt).
- Sanfte Seitenwechsel ueber Cross-Document View Transitions: Kopfbereich,
  Navigation und Fusszeile bleiben stehen, nur der Inhalt wechselt. Reines CSS,
  Browser ohne Unterstuetzung blenden schlicht um.
- Feature-Tour auf der Demoseite als horizontale Slides (CSS-Scroll-Snap),
  bedienbar per Wischen, Mausrad, Tastatur und Sprungmarken - ohne JavaScript.
- Fortschrittsbalken bei der Lesebestaetigung, dazu Karten mit leichtem Anheben,
  sanft aufklappende Detailbloecke und kurz aufpoppende Statuszeichen. Alles
  vollstaendig aus bei `prefers-reduced-motion`.
- Fehler behoben: Der Fuellstand des Fortschrittsbalkens kam als Inline-Style
  und wurde deshalb von der Content-Security-Policy verworfen - der Balken war
  immer voll. Der Wert kommt jetzt als CSS-Klasse, die CSP bleibt unangetastet.
- Fehler behoben: Die lange Quellcode-URL auf der Demoseite liess die Seite auf
  schmalen Bildschirmen horizontal scrollen.
- Die Demo zeigt jetzt die echte Anwendung statt einer nachgebauten Vorschau.
  Mit `DEMO_MODE=true` und `manage.py seed_demo` entsteht eine Demowache mit
  erfundenen Daten; Besucher starten unter `/demo/` eine Sitzung als Demokonto
  und klicken sich durch die vollstaendige Oberflaeche. Ein Banner weist
  durchgehend darauf hin, der Wartungscontainer setzt den Bestand regelmaessig
  zurueck. Standardmaessig ist der Demobetrieb aus; ist er an, meldet das der
  Deploy-Check `wachbuch.W002`. Damit kann die Demo auch nicht mehr von der
  echten Oberflaeche abweichen.
- Zurueckhaltende Bewegung beim Seitenaufbau und bei Bedienelementen, komplett
  in CSS und abgeschaltet, sobald das System reduzierte Bewegung wuenscht.
- Zwei-Faktor-Anmeldung per Authenticator-App (Google Authenticator, Aegis und
  andere TOTP-Apps). Einrichtung unter `Mehr -> Zwei-Faktor-Anmeldung` mit
  QR-Code und manuell eintragbarem Schluessel. Ein benutzter Code laesst sich
  nicht erneut verwenden, Fehlversuche sind gedrosselt. Beim Aktivieren gibt es
  acht einmalig nutzbare Wiederherstellungscodes, die nur als Hash gespeichert
  werden. Bei Anmeldung ueber Tailscale entfaellt die Abfrage, weil dort das
  Geraet der zweite Faktor ist.
- Eine Person kann jetzt auf mehreren Wachen freigegeben sein. Bisher verhinderte
  das eine Datenbankbedingung - im Rettungsdienst arbeiten Springer und
  Aushilfen aber regelmaessig auf mehr als einer Wache. Unter `Mehr` laesst sich
  die aktive Wache wechseln; Rolle und Daten richten sich immer nach der
  gewaehlten Wache. Wird ein Zugang entzogen, faellt die Auswahl automatisch
  zurueck.
- Datenschutzluecke geschlossen: Unter `Zugang freigeben` wurden bisher alle
  Konten der gesamten Installation aufgelistet, also auch die anderer Wachen.
  Die Freigabe erfolgt jetzt ueber die genaue E-Mail-Adresse; als wartend
  zaehlen nur noch Konten ohne jede Wachenzuordnung.
- Passwort-Reset wird jetzt gedrosselt (Standard: 3 Anfragen je Adresse und 12
  je IP pro Stunde). Gedrosselte Versuche bekommen dieselbe Antwort wie
  erfolgreiche, damit sich daraus nichts ueber vorhandene Konten ablesen laesst.
  Die Zaehler liegen im Datenbank-Cache und gelten damit ueber alle
  Gunicorn-Worker hinweg.
- Neuer `maintenance`-Container fuehrt `purge_expired` taeglich aus. Bisher
  waren Loeschfristen zwar einstellbar, wurden aber ohne manuellen Aufruf nie
  angewendet.
- Passwort-Reset per E-Mail (`/passwort-vergessen/`) samt Passwortwechsel unter
  `Mehr -> Passwort aendern`. Neue Konten brauchen im Django-Admin zwingend
  eine E-Mail-Adresse; `/team/` markiert Konten ohne Adresse. SMTP wird ueber
  die `EMAIL_*`-Werte in `.env` konfiguriert.
- Volltextsuche in den Uebergaben (Titel und Text), kombinierbar mit den
  vorhandenen Ansichten Aktiv/Dringend/Archiv.
- Lesebestaetigung fuer dringende Eintraege: Wer sie gelesen hat, quittiert das
  einmal; die Uebersicht zeigt die eigenen offenen Bestaetigungen. Es gibt
  bewusst keine Auswertung ueber Personen hinweg.
- Wochenprotokoll als PDF-Export, im Aufbau am Papierbogen orientiert.
- Loeschfristen je Wache unter `/einstellungen/` plus Befehl
  `manage.py purge_expired` (mit `--dry-run`). Der Befehl braucht die
  Owner-Rolle und laesst Kassenbuchungen unberuehrt.
- Deploy-Check `wachbuch.W001` meldet fehlende Betreiberangaben, damit die
  Rechtstexte im Produktivbetrieb nicht mit Platzhaltern online gehen.
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
