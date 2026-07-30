# Recherche und Quellen

Stand: 30. Juli 2026. Dieses Dokument ist eine technische Vorpruefung und keine
Rechtsberatung.

## Ergebnisse

1. Ein allgemeines Wachbuch darf nicht zur zweiten Patientenakte werden.
   Personenbezogene Einsatz- und Gesundheitsdaten bleiben in den dafuer
   zugelassenen Fachverfahren.
2. Beschaeftigtendaten brauchen je Zweck eine dokumentierte Rechtsgrundlage.
   Technisch auswertbare Benutzerkennungen und Zeitstempel loesen regelmaessig
   Mitbestimmung aus.
3. Geburtstage sind nur als freiwilliges Opt-in sinnvoll. Gespeichert werden
   Tag und Monat, niemals das Geburtsjahr.
4. Es gibt keine pauschale gesetzliche Aufbewahrungsfrist fuer ein Wachbuch.
   Kategorien benoetigen fachlich und datenschutzrechtlich freigegebene
   Loeschfristen.
5. Fuer Bielefeld existiert ein offizieller strukturierter Datensatz zu
   Verkehrsmeldungen. Fuer Guetersloh wurde kein gleichwertiger vollstaendiger
   Baustellenfeed verifiziert; die Anzeige muss diese Luecke benennen.
6. **Es gibt kein Schichtmodell, das fuer alle Wachen passt.** Der
   Rettungsdienstbedarfsplan 2025 des Kreises Guetersloh weist je Fahrzeug
   eigene Vorhaltezeiten aus, und der neue Standort Langenberg wird
   ausdruecklich als *Tages-Standort* eingerichtet, also nur einen Teil des
   Tages besetzt. Eine Anwendung, die einen 24-Stunden-Dienst voraussetzt,
   waere schon im eigenen Kreis falsch. Naeheres unten.

## Schichtbetrieb im Rettungsdienstbereich Kreis Guetersloh

Ausgewertet wurde der vom Kreistag am 30. Juni 2025 beschlossene
Rettungsdienstbedarfsplan 2025. Fuer die Anwendung sind vier Punkte
entscheidend:

- **Traegerstruktur.** Der Kreis betreibt neun Rettungswachen (Halle,
  Harsewinkel, Herzebrock-Clarholz, Rheda-Wiedenbrueck, Rietberg, Schloss
  Holte-Stukenbrock, Steinhagen, Verl, Versmold). Die Stadt Guetersloh ist
  nach Paragraf 6 Abs. 2 RettG NRW eigene Traegerin einer Rettungswache. Das
  sind zehn organisatorisch getrennte Einheiten in einem Kreis - genau die
  Konstellation, fuer die Phase 3 der Roadmap die Entscheidung zwischen
  Einzelinstanz und Kreisinstanz offenhaelt.
- **Unterschiedliche Vorhaltezeiten je Fahrzeug.** Der Plan fuehrt
  Vorhaltezeiten und Fahrzeuge in einer eigenen Aufstellung (Abschnitt 4.5).
  Eine Wache hat damit nicht *ein* Schichtmodell, sondern je Fahrzeug eines.
- **Tages-Standorte.** Langenberg wird als Aussenstelle der Rettungswache
  Rietberg zunaechst mit einem Tages-RTW eingerichtet; die Vorhaltezeiten
  sollen erst schrittweise verlaengert werden. Ein Schichtmodell ist also
  nichts Festes, sondern etwas, das sich waehrend des Betriebs aendert.
- **Dienstzeit ist mehr als Arbeitszeit.** Fuer die Kreisleitstelle haelt der
  Plan fest, dass die Mitarbeiterinnen und Mitarbeiter des operativen Dienstes
  im 24-Stundendienst taetig sind und sich die Dienstzeit aus Arbeits- und
  Bereitschaftszeit zusammensetzt.

**Was daraus folgt:** Die Wache beschreibt ihr Schichtmodell selbst
(`Wache` -> `Schichten`), und der Wachentag beginnt zu einer einstellbaren
Uhrzeit statt um Mitternacht. Die genauen Vorhaltezeiten je Wache stehen im
Plan nur als Abbildung und liessen sich aus dem PDF nicht als Text
uebernehmen; sie sind fuer die Anwendung auch nicht noetig, weil jede Wache
ihre Schichten ohnehin selbst eintraegt.

## Rechts- und Sicherheitsquellen

- [DSGVO, insbesondere Art. 5, 6, 9, 25, 30, 32 und 35](https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:02016R0679-20160504)
- [BDSG Paragraf 26 - Beschaeftigtendaten](https://www.gesetze-im-internet.de/bdsg_2018/__26.html)
- [DSG NRW, insbesondere Paragrafen 10, 16 und 18](https://recht.nrw.de/lrgv/gesetz/01042026-datenschutzgesetz-nordrhein-westfalen)
- [RettG NRW, insbesondere Paragraf 7a](https://recht.nrw.de/lrgv/gesetz/01012016-gesetz-ueber-den-rettungsdienst-sowie-die-notfallrettung-und-den)
- [BetrVG Paragraf 87](https://www.gesetze-im-internet.de/betrvg/__87.html)
- [LPVG NRW Paragraf 72](https://recht.nrw.de/lrgv/gesetz/14062023-personalvertretungsgesetz-fuer-das-land-nordrhein-westfalen)
- [LDI NRW - Datenschutz-Folgenabschaetzung](https://www.ldi.nrw.de/datenschutz/wirtschaft/datenschutz-folgenabschaetzung)
- [BSI IT-Grundschutz-Kompendium](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html)
- [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/)

## Rettungsdienstliche Quellen

- [Rettungsdienstbedarfsplan 2025 fuer den Rettungsdienstbereich Kreis Guetersloh](https://www.kreis-guetersloh.de/themen/bevoelkerungsschutz/rettungsdienst/rettungsdienstbedarfsplan-2025.pdf), Stand Juni 2025, beschlossen am 30.06.2025
- [Kreis Guetersloh - Rettungsdienst](https://www.kreis-guetersloh.de/themen/bevoelkerungsschutz/rettungsdienst/)
- [Kreis Guetersloh - Schrittweise Umsetzung des Rettungsdienstbedarfsplans (09.09.2025)](https://www.kreis-guetersloh.de/aktuelles/presse-und-oeffentlichkeitsarbeit/pressemitteilungen/09-09-2025-umsetzung-rettungsdienstbedarfsplan/)

## Offizielle Inhaltsquellen

- [Kreis Guetersloh RSS](https://www.kreis-guetersloh.de/kreis-gt-aktuelles/rss.xml)
- [Stadt Guetersloh RSS](https://www.guetersloh.de/de/rathaus/presseportal/news/rss.php)
- [Stadt Bielefeld Pressemeldungen RSS](https://www.bielefeld.de/de/pressedienst/presse-rss)
- [Bielefeld Open Data - Verkehrsmeldungen](https://open-data.bielefeld.de/dataset/verkehrsmeldungen), Lizenz CC BY 4.0

Externe Inhalte werden nur als Klartext mit Quelle, Originallink, Importzeit und
Aktualitaetsstatus angezeigt. Die Anwendung behauptet keine Vollstaendigkeit.
