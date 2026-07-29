# Rettungswache-Wachbuch

[![CI](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml/badge.svg)](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

Ein selbst gehostetes, mobiles Wachbuch fuer die interne Organisation einer
Rettungswache. Die Anwendung ist kein Einsatzleit-, Alarmierungs-,
Dienstplanungs- oder Patientendokumentationssystem.

## Funktionen

- versionierte Uebergaben mit Prioritaet, Status und nachvollziehbarer Korrektur
- Volltextsuche in Titel und Text der Uebergaben
- Lesebestaetigung fuer dringende Eintraege
- Wochenprotokoll mit Team je Tag, analog zum Papier-Uebergabebogen, als PDF exportierbar
- einfacher Wachenkalender
- freiwillige Geburtstagsanzeige ohne Geburtsjahr
- unveraenderliches Kaffeekassen-Ledger mit Korrekturbuchungen
- optionale offizielle RSS- und Verkehrsquellen, gefiltert nach Ort/Kreis der Wache
- optionaler Abfallkalender je Wache (ICS-Abo-Link)
- optionale Ort-/Kreis-Ermittlung aus der Wachenadresse (offener Geocoding-Dienst)
- Kaffeekasse mit optionalen, gebuehrenfrei nutzbaren Einzahlwegen (PayPal.me, Wero, Echtzeitueberweisung)
- stationsbezogene Rollen und nachvollziehbare Audit-Ereignisse
- Mehrfachzugehoerigkeit: Springer koennen auf mehreren Wachen freigegeben sein
  und dort mit unterschiedlichen Rollen arbeiten
- lokaler Login mit Passwort-Reset per E-Mail oder Anmeldung ueber Tailscale
- optionale Zwei-Faktor-Anmeldung per Authenticator-App inklusive
  Wiederherstellungscodes
- konfigurierbare Loeschfristen je Wache
- responsive, JavaScript-freie Oberflaeche mit hellem und dunklem Farbschema
- Impressum, Datenschutz- und Barrierefreiheitserklaerung als ausfuellbares Seiten-Geruest

## Administration

Die Anwendung hat drei Navigationspunkte: `Woche` (die Startseite),
`Suchen` und `Wache`. Persoenliches liegt unter `/konto/` beim eigenen Namen.

Stationsadministratoren koennen unter `/wache/einstellungen/` den Namen, den Standort
(angezeigt zentriert im Kopfbereich unter dem Namen), die Adresse und die
sichtbaren Module selbst festlegen. Ein Button ermittelt Ort und Kreis/Landkreis
aus der gespeicherten Adresse ueber einen offenen Geocoding-Dienst (siehe unten).
Unter `/lage/` (Reiter "Muellabfuhr", erreichbar ueber `Wache`) koennen Admins ausserdem den ICS-Abo-Link
des oertlichen Abfallkalenders hinterlegen; kommende Abholtermine erscheinen dort
automatisch nach der naechsten Synchronisierung. Unter `/kaffeekasse/` legen
Admins fest, ueber welche gebuehrenfreien Wege eingezahlt werden kann
(PayPal.me-Link, Wero-Link/-Kontakt und/oder IBAN mit Kontoinhaber fuer
Echtzeitueberweisungen); alle Mitglieder sehen die hinterlegten Wege direkt auf
der Kassenseite. Unter `/wache/team/` verwalten Admins Freigaben und Rollen. Zugang wird ueber die
genaue E-Mail-Adresse des bestehenden Kontos freigegeben - Konten anderer
Wachen werden bewusst nicht aufgelistet. Wer auf mehreren Wachen freigegeben
ist, wechselt die aktive Wache unter `Wache`.
Technische Administratoren konfigurieren unter `/django-admin/` Systemkonten
und externe Quellen. Fachliche Datensaetze sind dort bewusst nur lesbar, damit
Versionierung und Audit nicht umgangen werden.

## Schnellstart mit Docker

Voraussetzungen sind Docker Engine mit Compose v2 und ein freier lokaler Port.

```bash
git clone https://github.com/Darkspike1988/Rettungswache-Wachbuch.git
cd Rettungswache-Wachbuch
cp .env.example .env
```

In `.env` muessen alle Platzhalter durch unabhaengige Zufallswerte ersetzt
werden. Geeignete Werte erzeugt beispielsweise `openssl rand -hex 32`. Das
Backup-Verzeichnis muss fuer den PostgreSQL-Benutzer im Container schreibbar
sein:

```bash
sudo chown 70:70 backups
docker compose up --build -d
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py grant_station_admin BENUTZERNAME
```

Danach ist die Anwendung standardmaessig unter `http://127.0.0.1:8090` und die
Anmeldung unter `/anmelden/` erreichbar. Der Port bindet absichtlich nur an
Loopback. Fuer andere Geraete ist ein abgesicherter Reverse-Proxy mit TLS oder
Tailscale Serve erforderlich. `SECURE_COOKIES=false` ist ausschliesslich fuer
diesen lokalen HTTP-Schnellstart vorgesehen.

Der erste Login des per `grant_station_admin` freigeschalteten Kontos fuehrt
automatisch in einen gefuehrten Einrichtungsassistenten (`/einrichtung/`): Name
und Standort, Module aktivieren, fertig - jederzeit ueberspringbar und spaeter
unter `/einstellungen/` aenderbar. Fuer eine Demo bietet sich
`DEFAULT_STATION_NAME=Rettungswache Demo` in `.env` an.

Tests:

```bash
docker compose exec web python manage.py test --settings=config.test_settings
```

## Tailscale-Anmeldung

Fuer eine Tailnet-only-Installation werden in `.env` mindestens diese Werte
gesetzt:

```dotenv
TRUST_TAILSCALE_HEADERS=true
TAILSCALE_ADMIN_LOGIN=admin@example.org
SECURE_COOKIES=true
ALLOWED_HOSTS=your-host.example.ts.net
CSRF_TRUSTED_ORIGINS=https://your-host.example.ts.net
```

Die Identitaetsheader duerfen nur an einem nicht oeffentlich erreichbaren
Loopback-Port akzeptiert werden. Hinweise zur Proxy-Konfiguration stehen in
[`docs/OPERATIONS.md`](docs/OPERATIONS.md).

`createsuperuser` erzeugt bewusst einen globalen technischen Administrator fuer
den Django-Admin. Eine stationsbezogene Adminrolle allein vergibt keine globalen
Systemrechte.

## Externe Quellen

Zulaessige Quellhosts werden zuerst kommasepariert mit `FEED_ALLOWED_HOSTS` in
`.env` freigegeben. Anschliessend koennen HTTPS-RSS-Quellen unter
`/django-admin/core/feedsource/` angelegt werden. Der CSV-Importer unterstuetzt
das dokumentierte Bielefelder Verkehrsmeldungsformat. Private Zieladressen,
Weiterleitungen, andere Ports und Antworten ueber 2 MB werden abgewiesen.
Bei einem Upgrade von Version 0.2 muessen die Hosts bereits vorhandener Quellen
vor dem Neustart explizit in diese Liste uebernommen werden. Das `locality`-Feld
einer Quelle muss dem Ort oder Kreis-Namen der jeweiligen Wache entsprechen
(z.B. `Steinhagen` oder `Kreis Guetersloh`), damit Meldungen und Verkehr nur den
passenden Wachen angezeigt werden. Ohne hinterlegten Ort/Kreis an der Wache
bleibt es beim bisherigen Verhalten: alle Quellen dieses Typs werden angezeigt.

Der Abfallkalender je Wache nutzt dieselbe Allowlist: der Host des ICS-Links
muss zuerst in `FEED_ALLOWED_HOSTS` freigegeben werden, danach koennen
Stationsadmins ihren Abo-Link selbst unter `/lage/?typ=muell` eintragen. Es gibt
keine einheitliche bundesweite API fuer Muellabfuhrtermine; genutzt wird der
offene iCal-Standard, den nahezu jede Kommune/jeder Kreis als
"Kalender abonnieren"-Link fuer die eigene Adresse anbietet.

## Ort/Kreis aus der Adresse

Mit `GEOCODING_HOST` in `.env` kann ein Nominatim-kompatibler, offener
Geocoding-Dienst angebunden werden (leer = deaktiviert). Empfohlen ist eine
selbst gehostete Instanz; alternativ die oeffentliche
`nominatim.openstreetmap.org` unter Beachtung von deren Nutzungsbedingungen
(niedrige Anfragerate, klarer User-Agent). Admins loesen die Ermittlung manuell
unter `/einstellungen/` aus, es laeuft kein automatischer Hintergrundabgleich.

## Passwort-Reset und Konten

Konten legen technische Administratoren unter `/django-admin/` an; die
E-Mail-Adresse ist dabei Pflicht, sonst kann sich die Person das Passwort
spaeter nicht selbst zuruecksetzen. Unter `/team/` markiert das Wachbuch
Mitglieder ohne Adresse sichtbar.

Fuer den Versand werden in `.env` die `EMAIL_*`-Werte gesetzt. Ohne
`EMAIL_HOST` schreibt Django die Nachrichten nur in das Containerlog - fuer
einen Test brauchbar, fuer den Betrieb nicht. Angemeldete Personen aendern ihr
Passwort selbst unter `Konto -> Passwort aendern`.

## Demobetrieb

Fuer eine oeffentliche Schaufenster-Instanz, auf der Interessierte das Wachbuch
ausprobieren sollen:

```dotenv
DEMO_MODE=true
```

```bash
docker compose exec web python manage.py seed_demo
```

Danach koennen Besucher unter `/demo/` eine Sitzung als Demokonto starten und
die vollstaendige Oberflaeche bedienen. Ein Banner weist durchgehend auf den
Demobetrieb hin, der `maintenance`-Container setzt die Daten taeglich zurueck.

Der Demobetrieb gehoert auf eine eigene Instanz. Auf einem System mit echten
Wachendaten muss `DEMO_MODE=false` bleiben - sonst kann jeder Besucher eine
Sitzung starten. `manage.py check --deploy` weist mit `wachbuch.W002` darauf
hin, solange der Demobetrieb aktiv ist.

## Zwei-Faktor-Anmeldung

Jede Person richtet den zweiten Faktor selbst unter
`Konto -> Zwei-Faktor-Anmeldung` ein: QR-Code mit einer TOTP-App scannen
(Google Authenticator, Aegis, FreeOTP), einmal bestaetigen, fertig. Danach
fragt die Anmeldung nach dem Passwort zusaetzlich einen sechsstelligen Code ab.

Beim Aktivieren erscheinen acht Wiederherstellungscodes - jeder gilt einmal und
sie werden nur an dieser einen Stelle angezeigt. Sie gehoeren ausgedruckt oder
in einen Passwortmanager, nicht ins Wachbuch. Sind Handy und Codes weg, loescht
die technische Verwaltung das Geraet unter
`/django-admin/core/totpdevice/`; danach kann die Person neu einrichten.

Der TOTP-Schluessel liegt im Klartext in der Datenbank, weil der Server ihn zum
Pruefen braucht - so arbeiten auch die gaengigen Django-Bibliotheken. Der Schutz
der Datenbank gehoert damit zur Sicherheit des zweiten Faktors.

Im Tailscale-Modus entfaellt die Codeabfrage: dort ist das freigegebene Geraet
selbst der zweite Faktor.

## Loeschfristen

Unter `/wache/einstellungen/` legt die Wache je Datenart fest, nach wie vielen Tagen
geloescht wird (`0` = keine automatische Loeschung). Geloescht wird erst, wenn
der Betrieb den Befehl ausfuehrt:

```bash
docker compose run --rm migrate python manage.py purge_expired --dry-run
docker compose run --rm migrate python manage.py purge_expired
```

Der Befehl laeuft bewusst im `migrate`-Container: das Anwendungskonto darf
Audit-Ereignisse und Revisionen auf Datenbankebene nicht loeschen.
Kassenbuchungen sind wegen ihrer Aufbewahrungspflicht ausgenommen. Die Fristen
legt die verantwortliche Stelle fest, nicht die Software.

## Rechtliches (Impressum, Datenschutz, Barrierefreiheit)

Für öffentliche Betreiber (z.B. einen Kreis) sind unter `/impressum/`,
`/datenschutz/` und `/barrierefreiheit/` bereits ausformulierte Seiten
verlinkt (Fußzeile), die aber deutliche Platzhalter zeigen, bis folgende
Variablen in `.env` gesetzt sind: `OPERATOR_NAME`, `OPERATOR_ADDRESS`,
`OPERATOR_REPRESENTATIVE`, `OPERATOR_CONTACT`, `DPO_CONTACT` und
`ACCESSIBILITY_CONTACT`. Die Inhalte orientieren sich an § 5 TMG/§ 18 MStV,
Art. 13 DSGVO i.V.m. dem Datenschutzgesetz NRW (DSG NRW) sowie der
EU-Richtlinie (EU) 2016/2102 zur Barrierefreiheit. Sie ersetzen keine
rechtliche Prüfung durch die Datenschutzbeauftragte/den Datenschutzbeauftragten
und den Personalrat der verantwortlichen Stelle - Details und offene Punkte
stehen in [`docs/COMPLIANCE-NRW.md`](docs/COMPLIANCE-NRW.md).

## Datenschutz

Nicht in das Wachbuch gehoeren:

- Patienten-, Gesundheits-, Einsatz- oder Alarmierungsdaten
- Krankheitsgruende, Leistungsbewertungen oder private Konflikte
- gemeinsam genutzte Konten

Ein technischer Betrieb ersetzt keine Datenschutzpruefung, Mitbestimmung,
Loeschfristen oder organisatorische Freigabe. Details stehen in
[`docs/SECURITY-PRIVACY.md`](docs/SECURITY-PRIVACY.md).

## Dokumentation

- [Architektur](docs/ARCHITECTURE.md)
- [Betrieb, Backup und Updates](docs/OPERATIONS.md)
- [Datenschutz und Sicherheit](docs/SECURITY-PRIVACY.md)
- [Rechtliche Einordnung NRW/Kreis](docs/COMPLIANCE-NRW.md)
- [Test- und Go-live-Checkliste](docs/GO-LIVE-CHECKLIST.md)
- [Recherche und Quellen](docs/RESEARCH.md)
- [Roadmap](docs/ROADMAP.md)
- [Designregeln](docs/DESIGN-SYSTEM.md)

## Mitwirken

Beitraege sind willkommen. Vor einem Pull Request bitte
[`CONTRIBUTING.md`](CONTRIBUTING.md) und fuer vertrauliche Meldungen
[`SECURITY.md`](SECURITY.md) beachten.

## Lizenz

Copyright (C) 2026 Darkspike1988. Veroeffentlicht unter der GNU Affero General
Public License v3.0 oder spaeter. Wer eine geaenderte Fassung als Netzwerkdienst
betreibt, muss den Benutzern den zugehoerigen Quellcode anbieten.
