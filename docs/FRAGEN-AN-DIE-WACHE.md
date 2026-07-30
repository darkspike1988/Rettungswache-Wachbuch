# Fragen an die Wache

Diese Fragen kann eine Software nicht selbst beantworten. Sie entscheiden
darueber, wie das Wachbuch gebaut wird - nicht daurueber, ob es huebsch
aussieht, sondern ob es im Alltag benutzt oder umgangen wird.

> **Stand 30. Juli 2026:** A1, B3, C2 und E1 sind beantwortet. Die Antworten
> stehen jeweils unter der Frage, zusammen mit dem, was daraufhin gebaut wurde.
> Offen sind vor allem A2 bis A4 und C3 bis C6.

**So funktioniert das Dokument:** Jede Frage hat vorgegebene Antworten. Kreuze
an oder schreib daneben, wenn nichts passt - "keine der Antworten trifft es"
ist die wertvollste Rueckmeldung. Unter jeder Frage steht, **was sich in der
Software aendert**, je nachdem wie sie ausfaellt. Wo ich eine Empfehlung habe,
steht sie dabei; wo ich keine habe, sage ich das.

Es muss nicht alles auf einmal beantwortet werden. Block A und C sind die
dringendsten, Block F kann warten.

---

## A - Schichtbetrieb und was ein "Tag" ist

Diese Fragen waren die wichtigsten im Projekt: die Anwendung war um den
Kalendertag herum gebaut - Wochenprotokoll, Team-Feld, Aufgabenlisten. A1 ist
beantwortet und der Kalendertag inzwischen ersetzt; A2 bis A4 sind offen.

### A1 - Wie sind die Dienste geschnitten?

- [x] **24-Stunden-Dienst** (z.B. 07:00 bis 07:00 am Folgetag) - auf der
      eigenen Wache
- [x] **12 Stunden**, Tag und Nacht - auf anderen Wachen im Kreis
- [ ] **8 Stunden**: Frueh, Spaet, Nacht
- [x] **Gemischt** - es gibt verschiedene Wachenkonstellationen

> **Antwort (30.07.2026):** Beides, je nach Wache. Die Recherche im
> Rettungsdienstbedarfsplan 2025 des Kreises Guetersloh bestaetigt das und geht
> noch weiter: der Plan weist **je Fahrzeug** eigene Vorhaltezeiten aus, und
> der neue Standort Langenberg wird als **Tages-Standort** eingerichtet, also
> nur einen Teil des Tages besetzt. Ein Schichtmodell ist dort ausserdem nichts
> Festes - die Vorhaltezeiten sollen schrittweise verlaengert werden. Belege in
> [`RESEARCH.md`](RESEARCH.md).
>
> **Gebaut:** Der Wachentag ist nicht mehr der Kalendertag. Jede Wache stellt
> ein, wann ihr Betriebstag beginnt (Vorgabe 07:00); ein Haken um 02:00 Uhr
> zaehlt seitdem zum Dienst, der am Vortag begonnen hat. Dazu ein
> Schichtmodell, das die Wache selbst beschreibt (`Wache` -> `Schichten`): wer
> eine Besetzung je Tag hat, legt keine an und merkt nichts davon; wer zwei
> hat, bekommt zwei Team-Felder je Tag und kann Aufgabenlisten an eine Schicht
> binden. Der Betriebstag wird schon im Einrichtungsassistenten abgefragt.

### A2 - Wie viele verschiedene Besetzungen hat ein Kalendertag?

- [ ] **Eine** - ein Team hat den ganzen Tag Dienst
- [ ] **Zwei** - Tag und Nacht
- [ ] **Drei oder mehr**
- [ ] Wechselt

> **Was sich aendert:** Das Team-Feld hat heute genau **eine** Zeile pro Tag
> ("Team: Dotzki/Huber"), so wie auf eurem Papierbogen. Bei zwei oder drei
> Besetzungen braucht es mehrere Zeilen je Tag - oder das Feld gehoert an die
> Schicht statt an den Tag.

### A3 - Gibt es einen festen Moment "Uebergabe"?

- [ ] **Ja**, die abloesende und die abgebende Schicht setzen sich zusammen
- [ ] **Halb** - man liest den Zettel und fragt nach, wenn was unklar ist
- [ ] **Nein**, laeuft nebenbei / man sieht sich oft gar nicht

> **Was sich aendert:** Das ist die Grundlage fuer den geplanten Ablauf
> "Dienst beginnen / Dienst beenden" (Roadmap 1.3). Bei "Nein" waere ein
> gefuehrter Uebergabe-Bildschirm falsch gedacht - dann muss die Information
> die Person finden, nicht die Person den Bildschirm.

### A4 - Wer traegt heute die Uebergabe ins Buch ein?

- [ ] Die **Schichtleitung**
- [ ] **Jede und jeder** traegt selbst ein, was er/sie hat
- [ ] Meist **eine bestimmte Person**, weil sie es halt macht

> **Was sich aendert:** Die Rechte. Heute darf jedes Mitglied schreiben und nur
> die Schichtleitung fremde Eintraege korrigieren. Wenn faktisch nur eine
> Person schreibt, ist das Formular fuer die falsche Zielgruppe gebaut.

---

## B - Geraete und Netz

### B1 - Womit wird das Wachbuch bedient? (mehrere moeglich)

- [ ] **Festes Tablet an der Wache** (Flur, Kueche, Fahrzeughalle)
- [ ] **Eigene Smartphones** der Kolleginnen und Kollegen
- [ ] **PC/Laptop** im Wachenbuero
- [ ] **Dienst-Tablet im Fahrzeug**

> **Was sich aendert:** Die Oberflaeche ist heute fuer Touch ausgelegt (48 Pixel
> Mindestgroesse ab Fingerbedienung) und funktioniert am PC genauso. Was davon
> der Hauptfall ist, entscheidet aber, wo ich Aufwand hinstecke - und ob
> "Offline lesen" (Roadmap 2) dringend oder Beiwerk ist.

### B2 - Wo ist an der Wache kein Netz?

- [ ] Ueberall Netz, kein Problem
- [ ] **Fahrzeughalle** ist ein Funkloch
- [ ] **Keller / Lager**
- [ ] Anders: ______________________________

> **Was sich aendert:** Der Fahrzeugcheck findet in der Halle statt. Wenn dort
> kein Netz ist, ist die Aufgabenliste dort unbenutzbar - dann rueckt der
> Offline-Modus von Phase 2 nach vorn. Das ist die einzige Stelle, an der
> JavaScript in die Anwendung kaeme; ich baue es nur, wenn es diesen Grund gibt.

### B3 - Wenn ein gemeinsames Tablet an der Wache haengt: wie wird es benutzt?

- [x] Gemeinsames Tablet, und es soll **kein Name** an den Haken stehen
- [ ] **Jede/r meldet sich kurz an**, hakt ab, meldet sich ab
- [ ] Es bleibt bei dem angemeldet, der es zuletzt benutzt hat

> **Antwort (30.07.2026):** Gemeinsames Geraet, keine Namen.
>
> **Gebaut:** Die Wache stellt unter `Einstellungen` -> `Namen bei Aufgaben`
> auf "Keinen Namen anzeigen". Dann steht an der Zeile nur noch die Uhrzeit,
> und im Wochen-PDF faellt die Spalte "Von" ganz weg, statt leer zu bleiben -
> eine durchgehend leere Spalte sieht auf Papier aus wie ein Versaeumnis.
>
> **Was dabei bewusst nicht passiert:** Gespeichert bleibt, an welchem Zugang
> der Haken gesetzt wurde. Ohne das waere das Audit-Log wertlos. Angezeigt wird
> es nur nicht mehr.
>
> **Was noch offen ist:** Die Einstellung wirkt auf die Aufgaben. Uebergaben
> und Lesebestaetigungen haengen weiter an persoenlichen Konten - "3 von 12
> haben gelesen" waere sonst keine Aussage mehr. Wenn auch Uebergaben vom
> gemeinsamen Geraet aus geschrieben werden sollen, ist das eine eigene
> Entscheidung, die wir getrennt treffen sollten.

---

## C - Aufgaben (gerade gebaut, Rueckmeldung am wertvollsten)

### C1 - Wie viele Listen und wie viele Punkte kommen realistisch zusammen?

- [ ] **Eine Liste**, ca. 5-10 Punkte (wie der Papierbogen)
- [ ] **Zwei bis vier Listen** (Tagesaufgaben plus Fahrzeugchecks)
- [ ] **Fuenf oder mehr**
- [ ] Weiss ich noch nicht

> **Was sich aendert:** Ab etwa 30 Punkten pro Tag wird die Tagesansicht eine
> Bleiwueste, und ich sollte Listen einklappbar machen oder auf Reiter
> umstellen. Bei 10 Punkten waere das unnoetige Komplexitaet.

### C2 - Wie sind Fahrzeugchecks organisiert?

- [ ] **Eine Liste je Fahrzeug** ("Fahrzeugcheck RTW 1", "... RTW 2")
- [ ] **Eine Liste**, aber pro Fahrzeug einmal abzuhaken
- [ ] Fahrzeugchecks laufen ueber ein **anderes System**
- [x] **Spaeter, als eigenes Modul**

> **Antwort (30.07.2026):** Kann man spaeter reinmachen, als zusaetzliches
> Modul.
>
> **Folge:** Fahrzeugchecks werden vorerst nicht eigens gebaut. Wer heute schon
> einen braucht, legt ihn als gewoehnliche Aufgabenliste an - das funktioniert,
> ist aber nicht mehr als eine Liste mit passendem Namen. Ein echtes Modul
> (Fahrzeugstamm, Liste je Fahrzeug, Pruefintervalle) steht jetzt in Phase 3
> der Roadmap und wird erst begonnen, wenn die taeglichen Aufgaben im Betrieb
> laufen.

### C3 - Was passiert heute mit einer Aufgabe, die nicht erledigt wurde?

- [ ] Nichts, sie faellt einfach aus
- [ ] Sie wird **muendlich** an die naechste Schicht weitergegeben
- [ ] Sie wird **auf dem Zettel vermerkt**
- [ ] Sie muss **nachgeholt** werden

> **Was sich aendert:** Heute bleibt ein nicht abgehakter Punkt einfach offen
> und die Wochenansicht zeigt "5/9". Wenn Nichterledigtes bei euch aber
> weitergereicht werden muss, sollte die Software das aktiv tun - etwa beim
> Dienstende danach fragen (Roadmap 1.3).

### C4 - An wen geht heute eine Mangelmeldung?

- [ ] **Schichtleitung**
- [ ] **Wachleitung**
- [ ] **Technik / Geraetewart**
- [ ] **Hausmeister / Kreis** (bei Gebaeudesachen)
- [ ] Kommt drauf an: ______________________________

> **Was sich aendert:** Ein gemeldeter Mangel wird heute zu einer Uebergabe -
> also fuer alle sichtbar, aber an niemanden konkret gerichtet. Wenn es feste
> Adressaten gibt, waere eine Zuweisung sinnvoll ("geht an Technik"). Das ist
> ein kleiner Schritt, aber ich baue ihn nicht auf Verdacht.

### C5 - Braucht ein Mangel ein Foto?

- [ ] **Ja**, oft - ein Bild sagt mehr als drei Saetze
- [ ] **Selten**, geht auch ohne
- [ ] **Nein**, und ich moechte auch keine Kamera in der Anwendung

> **Was sich aendert:** Fotos stehen in Roadmap 2. Sie bringen Dateispeicher,
> Groessenbegrenzung, Metadaten-Entfernung und eine eigene Loeschfrist mit -
> spuerbarer Aufwand. Und ein Foto in einer Rettungswache kann versehentlich
> Personen zeigen; dazu braeuchte es eine klare Regel.

### C6 - Gibt es Pruefungen, die nur woechentlich oder monatlich anfallen?

- [ ] **Ja** (z.B. monatlicher Grosscheck, woechentliche Geraetepruefung)
- [ ] **Nein**, alles taeglich
- [ ] Ja, aber die laufen woanders

> **Was sich aendert:** Der monatliche Rhythmus ist gebaut, macht das Formular
> aber komplizierter (zwei Felder, von denen je nach Rhythmus nur eines gilt).
> Bei "Nein" wuerde ich ihn wieder entfernen und das Formular auf die
> Wochentage reduzieren.

---

## D - Rollen

Heute gibt es fuenf: Mitglied, Schichtleitung, Kassenwart, Admin, Auditor.
Mein Vorschlag ist, auf drei zu gehen.

### D1 - Wer fuehrt die Kaffeekasse?

- [ ] **Dieselbe Person, die die Wache verwaltet** - *empfohlen, dann faellt die
      Rolle "Kassenwart" weg*
- [ ] **Eine andere Person**, die aber nicht Team und Einstellungen verwalten
      soll - dann bleibt die Rolle
- [ ] **Kaffeekasse brauchen wir nicht**

### D2 - Gibt es bei euch eine externe Pruefung, die ins Wachbuch schauen wuerde?

- [ ] **Nein** - *dann faellt die Rolle "Auditor" weg, empfohlen*
- [ ] **Ja**, gelegentlich (Rechnungspruefung, Datenschutz, Kreis)
- [ ] Weiss ich nicht

> **Was sich aendert:** Der "Auditor" sieht heute **nur** das Aenderungsprotokoll
> und sonst nichts von der Wache. Dafuer gibt es an sechs Stellen im Code einen
> Sonderweg. Bei "Ja, gelegentlich" wuerde ich die Rolle trotzdem streichen und
> fuer die Dauer einer Pruefung einen Admin-Zugang geben - das ist ehrlicher als
> eine Dauerrolle fuer einen Einzelfall.

### D3 - Gibt es die "Schichtleitung" bei euch formal?

- [ ] **Ja**, klar benannt
- [ ] **Informell** - irgendwer ist der Erfahrenere
- [ ] **Nein**, alle gleich

> **Was sich aendert:** Die Schichtleitung darf heute fremde Eintraege
> korrigieren, den Status aendern und das Team eintragen. Bei "Nein, alle
> gleich" waeren das zwei Rollen statt drei - noch einfacher.

---

## E - Module

Alles hier laesst sich einzeln abschalten. Die Frage ist, was **standardmaessig**
an sein soll, wenn eine fremde Wache das Wachbuch installiert.

### E1 - Externe Meldungen (Nachrichten-RSS, Verkehr, Muellkalender)

- [ ] **Alles raus**
- [x] **Muellkalender ist wichtig** - der bleibt
- [ ] **Alles behalten**

> **Antwort (30.07.2026):** Der Muellkalender ist wichtig.
>
> **Folge:** Mein Vorschlag, das Feeds-Modul zu streichen, ist damit vom Tisch;
> der entsprechende Punkt faellt aus der Roadmap. Die Absicherung gegen
> Server-Side-Request-Forgery und die Host-Freigabeliste bleiben noetig,
> solange die Anwendung fremde Adressen abruft - das ist der Preis des Moduls,
> nicht der Anteil, den man wegsparen kann.
>
> **Was ich stattdessen vorschlage:** RSS und Verkehrsmeldungen sind damit
> nicht mitbeantwortet. Wenn davon nur der Muellkalender gebraucht wird, kann
> der eigene Worker-Container entfallen und die Termine direkt beim
> Seitenaufruf geholt werden - deutlich weniger bewegliche Teile bei gleichem
> Nutzen. Die Frage steht offen; siehe E1a.

### E1a - Werden RSS und Verkehrsmeldungen gebraucht?

- [ ] **Ja, beides**
- [ ] **Nur die Nachrichten** (Kreis/Stadt)
- [ ] **Nein, nur der Muellkalender** - dann faellt ein Container weg
- [ ] Weiss noch nicht

> **Was sich aendert:** Bei "nur der Muellkalender" holt die Anwendung die
> Abfuhrtermine beim Seitenaufruf statt ueber einen Hintergrunddienst. Das
> spart einen Container, ein Datenbankkonto und ein eigenes Netz - der Rest der
> Absicherung bleibt.

### E2 - Wachenkalender

- [ ] **Nutzen wir** (Uebungen, Sitzungen, Termine)
- [ ] **Haben wir woanders** (Outlook, Dienstplansoftware)
- [ ] Weiss noch nicht

### E3 - Geburtstage

- [ ] **Nette Sache, behalten**
- [ ] **Brauchen wir nicht**

> **Was sich aendert:** Geburtstage sind freiwillig, ohne Jahr und jederzeit
> widerrufbar - datenschutzrechtlich sauber, aber es ist ein Modul mehr. Bei
> "brauchen wir nicht" wuerde ich es standardmaessig ausschalten.

---

## F - Betrieb und Organisation (kann warten)

### F1 - Wie viele Personen arbeiten auf der Wache?

- [ ] Bis 10
- [ ] 10 bis 25
- [ ] Mehr als 25

> **Was sich aendert:** Die Lesebestaetigung fuer dringende Eintraege zeigt
> "3 von 12 haben gelesen". Ab etwa 30 Personen wird das eine sinnlose Zahl.

### F2 - Geht es um eine Wache oder mehrere?

- [ ] **Nur unsere Wache**
- [ ] **Mehrere Wachen im Kreis**, jede mit eigener Installation
- [ ] **Mehrere Wachen in einer gemeinsamen Installation**

> **Was sich aendert:** Die dritte Antwort ist die anspruchsvollste. Die
> Mandantentrennung ist vorhanden und getestet, aber fuer eine Kreis-Instanz
> mit echten Daten aus mehreren Wachen wuerde ich sie extern pruefen lassen,
> bevor sie live geht. Steht als offene Entscheidung in Roadmap 3.

### F3 - Wer betreibt den Server?

- [ ] **Ich selbst** / jemand aus der Wache
- [ ] **Die IT des Kreises**
- [ ] **Noch offen**

> **Was sich aendert:** Bei der Kreis-IT gelten deren Vorgaben fuer Backup,
> Zugriff, Protokollierung und Netz. Dann sollte
> `docs/GO-LIVE-CHECKLIST.md` vorher an diese Vorgaben angepasst werden statt
> hinterher.

### F4 - Sind Datenschutz und Personalrat schon eingebunden?

- [ ] **Ja**
- [ ] **Nein, aber geplant**
- [ ] **Noch gar nicht daran gedacht**

> **Was sich aendert:** Nichts an der Software - aber es ist der Punkt, an dem
> Projekte im oeffentlichen Dienst haengenbleiben. Ein Wachbuch, das
> nachvollziehbar festhaelt, wer wann was gemacht hat, ist mitbestimmungs-
> pflichtig. Details in `docs/COMPLIANCE-NRW.md`. Je frueher, desto besser -
> und wenn dabei Auflagen kommen, baue ich sie lieber jetzt ein.

### F5 - Gibt es Vorgaben, wie lange so ein Buch aufbewahrt werden muss?

- [ ] **Ja**: ______________________________
- [ ] **Nein, nichts Schriftliches**
- [ ] Muss ich erfragen

> **Was sich aendert:** Loeschfristen sind einstellbar, stehen aber
> standardmaessig auf "nie loeschen". Die Frist festzulegen ist Sache der
> verantwortlichen Stelle, nicht der Software - aber ohne Festlegung sammelt
> sich alles unbegrenzt an, und das ist datenschutzrechtlich der schlechteste
> Zustand.

### F6 - Soll das Papier verschwinden oder parallel weiterlaufen?

- [ ] **Papier weg**, sobald es laeuft
- [ ] **Erst mal parallel**, ein paar Wochen
- [ ] **Papier bleibt**, die Anwendung ist eine Ergaenzung

> **Was sich aendert:** Bei "parallel" muss der PDF-Export exakt wie der
> Papierbogen aussehen, damit man beides nebeneinanderlegen kann. Bei "Papier
> weg" darf die Anwendung eigene Wege gehen, wo sie besser sind.

---

## G - Und zum Schluss

### G1 - Was nervt im Wachenalltag am meisten, das eine Software loesen koennte?

Freitext - das ist die wichtigste Zeile im ganzen Dokument:

```


```

### G2 - Was ist an dem, was jetzt gebaut ist, offensichtlich falsch gedacht?

Zwoelf Jahre Rettungsdienst schlagen jede Wettbewerbsanalyse. Wenn etwas
"nach Buero" aussieht statt nach Wache, ist es das vermutlich auch:

```


```

---

## Was ich mit den Antworten mache

- **Block A und C** entscheiden ueber Roadmap 1.3 (Dienstbeginn/Dienstende) und
  ueber Korrekturen an den gerade gebauten Aufgabenlisten.
- **Block B** entscheidet, ob der Offline-Modus (Roadmap 2) vorgezogen wird.
- **Block D und E** sind Aufraeumarbeiten, die ich sofort umsetzen kann.
- **Block F** gehoert in die Go-live-Vorbereitung.
- **Block G** kann alles davon ueber den Haufen werfen. Gut so.

## Was aus den bisherigen Antworten geworden ist

| Frage | Antwort | Umgesetzt |
| --- | --- | --- |
| A1 Schichtmodell | 24 h und 12 h, je nach Wache | Betriebstag mit einstellbarem Beginn, Schichtmodell je Wache |
| B3 Gemeinsames Geraet | Kein Name an den Haken | Einstellung "Namen bei Aufgaben", Spalte faellt auch im PDF weg |
| C2 Fahrzeugchecks | Spaeter als eigenes Modul | Nach Phase 3 verschoben, vorerst als gewoehnliche Liste moeglich |
| E1 Feeds | Muellkalender ist wichtig | Streichung zurueckgenommen, Modul bleibt |

**Als naechstes waeren A2 bis A4 dran** - wie viele Besetzungen ein Tag hat,
ob es einen festen Uebergabemoment gibt und wer eintraegt. Daran haengt
Roadmap 1.3, der gefuehrte Dienstbeginn und das Dienstende.
