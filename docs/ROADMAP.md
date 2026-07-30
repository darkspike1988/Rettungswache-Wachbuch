# Roadmap

Stand: 30. Juli 2026

Dieses Dokument beschreibt den Weg von der jetzigen Codebasis zu einer
Anwendung, die im taeglichen Wachenalltag traegt. Es benennt auch, was
absichtlich nicht gebaut wird.

## Der eine Satz

> Die Schichtuebergabe einer Rettungswache, digital, betrieben von der Wache
> selbst.

Alles, was sich diesem Satz nicht unterordnet, ist ein optionales Modul oder
faellt weg. Dieser Satz ist der Massstab fuer jede Entscheidung unten.

## Was der Vergleich mit anderen Produkten ergeben hat

Betrachtet wurden kommerzielle Wachen- und Schichtuebergabe-Produkte
(Station Boss, Station Check, APX Data im Feuerwehrbereich; Shiftconnector und
Innovapptive im industriellen Schichtbetrieb) sowie offene Projekte im
deutschsprachigen Raum (EmergencyForge/ignis, gampig/feuerwehr-app,
abrain/einsatzverwaltung, Retschga/FWmonitor).

**Das wichtigste Ergebnis:** Bei jedem Produkt, das sich an Wachen richtet,
steht die **wiederkehrende Checkliste** im Mittelpunkt - Fahrzeugcheck,
Wachenrundgang, Tages-, Wochen- und Monatsaufgaben, abgehakt am Tablet, mit
Mangelmeldung an die Schichtleitung. Genau das steht auf dem Papierbogen dieser
Wache unter "Tagesaufgaben" mit Ankreuzfeldern - und genau das fehlt in der
Anwendung bisher vollstaendig. Freitext-Uebergaben ersetzen keine Checkliste.

Weitere uebereinstimmende Muster der Wettbewerber:

| Muster | Stand hier |
| --- | --- |
| Wiederkehrende Checklisten mit Haken je Punkt | **fehlt** |
| Mangel aus der Checkliste wird automatisch zur Aufgabe | **fehlt** |
| Foto zum Mangel | **fehlt** |
| Offline erfassen und spaeter senden | **fehlt** |
| Lesebestaetigung fuer Wichtiges | vorhanden |
| Bericht als PDF fuer die Akte | vorhanden |
| Unveraenderliche Historie | vorhanden, sogar auf Datenbankebene |
| KI-Zusammenfassungen | bewusst nicht geplant, siehe unten |

Die offenen deutschsprachigen Projekte decken den Wachenalltag nicht ab:
`ignis`/`intraRP` zielt auf Rollenspiel-Communities (FiveM), `feuerwehr-app` auf
Mannschaftsbuch und Kleiderkammer, `einsatzverwaltung` auf oeffentliche
Einsatzberichte, `FWmonitor` auf Alarmdarstellung. Diese Nische ist frei.

**Was hier besser ist als bei den kommerziellen Produkten** und den Kern der
Positionierung bildet: selbst gehostet, AGPL, keine Lizenzkosten, keine
Anbieterbindung, Datenschutz- und Aufbewahrungsregeln fest eingebaut, keine
Patienten- oder Einsatzdaten per Konstruktion.

## Was gestrichen wird

- **KI-Zusammenfassungen.** Wettbewerber bewerben sie stark. Fuer eine Wache
  mit wenigen Eintraegen je Schicht loesen sie kein Problem, erzeugen aber eine
  Datenschutzfrage und eine Abhaengigkeit. Nein.
- **Einsatz-, Alarm- und Patientendaten.** Unveraendert ausgeschlossen.
- **Dienstplanung.** Dafuer gibt es Fachverfahren; der Kalender bleibt ein
  Wachenkalender.
- **Inventar- und Ausbildungsverwaltung** (Station Boss kann das). Eigenes
  Produkt, nicht dieses.

## Phase 0 - betriebsfaehig (Blocker)

Ohne diese Punkte laeuft nichts produktiv. Sie stehen zuerst, weil alles
andere darauf aufbaut.

- [ ] **Docker-Stack auf echter Hardware verifizieren.** Bislang ist der Build
      nie durchgelaufen, weil die Entwicklungsumgebung kein PyPI erreicht.
      Seitdem sind `reportlab`, `pyotp`, `qrcode`, ein `maintenance`-Container
      und die Cache-Tabelle dazugekommen - alles ungetestet im Container.
- [ ] SMTP hinterlegen und Passwort-Reset einmal mit echtem Postfach durchspielen
- [ ] `OPERATOR_*`-Angaben setzen, bis `check --deploy` nichts mehr meldet
- [ ] Backup wiederherstellen und den Restore-Test dokumentieren

**Fertig, wenn:** Ein frischer Server startet aus dem Repository heraus, ein
Admin kann sich anmelden, sein Passwort zuruecksetzen und die Wache einrichten.

## Phase 1 - der Wachenalltag (das Produkt)

Hier entsteht der Nutzen. Reihenfolge ist bewusst gewaehlt: die Checkliste
zuerst, weil sie der taegliche Anlass ist, die Anwendung ueberhaupt zu oeffnen.

### 1.1 Checklisten (groesster Einzelposten)

- Vorlagen je Wache: Punkte, Reihenfolge, Rhythmus (taeglich, woechentlich,
  monatlich, je Fahrzeug)
- Erledigung je Tag mit Haken, Person und Zeitpunkt - unveraenderlich wie die
  bestehenden Revisionen
- Die Wochenansicht zeigt je Tag den Stand ("7 von 9")
- Ein nicht erledigter Punkt bleibt sichtbar, verschwindet nicht lautlos

Neue Modelle: `ChecklistTemplate`, `ChecklistItem`, `ChecklistRun`,
`ChecklistResult`. Damit steigt die Modellzahl - im Gegenzug faellt in 1.4
anderes weg.

### 1.2 Mangel wird zur Aufgabe

Ein Punkt auf "Mangel" erzeugt direkt einen Uebergabe-Eintrag mit Verweis auf
Checkliste und Punkt. Das ist die Schleife, die aus Dokumentation Arbeit macht -
und der Punkt, an dem alle Wettbewerber ihren Nutzen zeigen.

### 1.3 Dienstbeginn und Dienstende

- "Dienst beginnen": was ist seit der letzten Uebergabe passiert, was ist offen,
  was ist noch nicht bestaetigt
- "Dienst beenden": offene Punkte durchgehen, Team fuer den Tag bestaetigen

Bildet den Ablauf ab, den die Leute ohnehin im Kopf haben.

### 1.4 Verschlanken

- **Feeds-Modul entfernen** (RSS, Verkehr, Muellabfuhr). Es kostet Allowlist,
  SSRF-Haertung, einen Worker-Container, eine Datenbankrolle und ICS-Parsing -
  fuer Abfuhrtermine. Als eigenes optionales Plugin auslagern oder streichen.
  Das ist eine Migration, die Tabellen verwirft, und braucht eine bewusste
  Entscheidung.
- **Rollen von fuenf auf drei**: Mitglied, Schichtleitung, Admin. Kassenwart und
  Auditor gehen in Admin auf; die Nachvollziehbarkeit leistet das Audit-Log.
  Braucht eine Datenmigration fuer bestehende Mitgliedschaften.

**Fertig, wenn:** Eine Schicht kann einen kompletten Tag ausschliesslich in der
Anwendung abwickeln, ohne zum Papier zu greifen.

## Phase 2 - feldtauglich

- **Offline lesen.** Ein Service Worker haelt die laufende Woche und die letzte
  Uebergabe vor. Im Fahrzeugraum und im Keller ist oft kein Netz. Dies ist die
  einzige Stelle, an der JavaScript in das Werkzeug kommt - weil sie echten
  Nutzen hat.
- **Foto zum Mangel**, serverseitig verkleinert, ohne Personenbezug, mit klarer
  Loeschfrist.
- Erfassen in einer Hand: Eintrag anlegen mit so wenig Feldern wie moeglich,
  Kategorie und Prioritaet vorbelegt.
- Lasttest mit realistischem Bestand (mehrere Jahre Eintraege).

**Fertig, wenn:** Die laufende Woche laesst sich ohne Netz lesen und ein Mangel
mit Foto in unter dreissig Sekunden erfassen.

## Phase 3 - Uebergabe an andere Wachen

- Installationsanleitung, die jemand ohne Django-Kenntnisse durcharbeiten kann
- Wachen-Logo hochladbar statt Platzhalter
- Upgrade-Pfad zwischen Versionen dokumentiert und getestet
- Entscheidung zur Mandantenfaehigkeit: eine Instanz je Wache (heutiges Modell,
  einfach) oder eine Kreis-Instanz mit mehreren Wachen (dafuer waeren die
  bekannten Grenzen zu schliessen)

**Fertig, wenn:** Eine fremde Wache installiert das Wachbuch ohne Rueckfrage.

## Phase 4 - formaler Betrieb

- Barrierefreiheit extern nach EN 301 549 / WCAG 2.2 AA pruefen lassen und die
  Erklaerung mit dem Ergebnis fuellen
- Externer Sicherheitstest beziehungsweise Pruefung gegen OWASP ASVS Level 2
- Datenschutz und Mitbestimmung abschliessen (DSG NRW, LPVG NRW, DSFA-Vorpruefung)
- Loeschfristen mit der verantwortlichen Stelle festlegen und aktivieren
- Betriebs-, Support- und Notfallprozess abnehmen

**Fertig, wenn:** Eine schriftliche Go-live-Freigabe vorliegt.

## Vorgehen quer zu allen Phasen

- **Eine Schicht mitfahren, bevor Phase 1 beginnt.** Jedes Wort mitschreiben,
  das die Leute benutzen, und es genau so in die Oberflaeche uebernehmen.
  "Betrifft Tag" sagt niemand; die Frage lautet "Fuer welchen Tag?".
- **Fuenf Nutzertests am echten Geraet** nach jeder Phase. Nicht am Schreibtisch,
  sondern dort, wo gearbeitet wird.
- Jede neue Idee gegen den einen Satz oben pruefen. Im Zweifel: nicht bauen.

## Was bereits steht

Uebergaben mit Versionierung und nachvollziehbarer Korrektur, Wochenprotokoll
mit Team je Tag und PDF-Export, Volltextsuche, Lesebestaetigung fuer Dringendes,
Kalender, Kaffeekasse mit Einzahlwegen, freiwillige Geburtstage, Rollen und
Audit, Mehrfachzugehoerigkeit fuer Springer, Passwort-Reset mit Drosselung,
Zwei-Faktor per Authenticator-App, Loeschfristen mit taeglichem Lauf,
Demobetrieb, Rechtstexte mit Deploy-Pruefung, helles und dunkles Farbschema,
Touchbedienung ab `pointer: coarse`, 127 automatisierte Tests.
