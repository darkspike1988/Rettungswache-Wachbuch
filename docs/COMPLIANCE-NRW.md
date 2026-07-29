# Rechtliche Einordnung fuer Betreiber in NRW (z.B. einen Kreis)

Diese Seite ordnet die technisch umgesetzten Bausteine den einschlaegigen
Rechtsgrundlagen zu und markiert, was zusaetzlich durch die verantwortliche
Stelle selbst zu klaeren ist. Sie ist eine Orientierung, keine Rechtsberatung
und ersetzt nicht die Pruefung durch die Datenschutzbeauftragte/den
Datenschutzbeauftragten, den Personalrat und ggf. die Rechtsaufsicht des
Betreibers.

## Datenschutz (DSGVO, DSG NRW)

| Anforderung | Stand |
| --- | --- |
| Rechtsgrundlage je Modul, Informationspflicht (Art. 13 DSGVO) | Datenschutzerklaerung unter `/datenschutz/` vorbereitet, Angaben zur verantwortlichen Stelle ueber `OPERATOR_*`/`DPO_CONTACT` zu ergaenzen. Fehlen sie im Produktivbetrieb, warnt `manage.py check --deploy` mit `wachbuch.W001` |
| Verzeichnis von Verarbeitungstaetigkeiten, DSFA-Schwellenwertpruefung | offen, Aufgabe des Betreibers (siehe `docs/SECURITY-PRIVACY.md`) |
| Datenminimierung, Zweckbindung | technisch durchgesetzt: keine Patienten-/Einsatzdaten-Felder, Geburtstage nur mit Einwilligung, Audit ohne Freitextkopien |
| Loesch-/Aufbewahrungsfristen | technisch umgesetzt: Fristen je Wache unter `/einstellungen/`, Ausfuehrung ueber `manage.py purge_expired`. Welche Fristen gelten, entscheidet weiterhin der Traeger; Kassenbuchungen sind wegen Aufbewahrungspflichten ausgenommen |
| Betroffenenrechte, Aufsichtsbehoerde | in der Datenschutzerklaerung benannt: Landesbeauftragte fuer Datenschutz und Informationsfreiheit NRW (LDI NRW) |
| Zugangssicherung | Passwort plus optionaler zweiter Faktor (TOTP); Anmeldeversuche gedrosselt. Ob 2FA verpflichtend ist, entscheidet die verantwortliche Stelle |
| Auftragsverarbeitung bei externem Hosting | AVV mit dem Hosting-/Betriebsdienstleister durch den Betreiber abzuschliessen |

Als oeffentliche Stelle in NRW gilt fuer einen Kreis ergaenzend zur DSGVO das
Datenschutzgesetz Nordrhein-Westfalen (DSG NRW).

### Lesebestaetigung und Auswertungsverbot

Dringende Eintraege koennen quittiert werden. Gespeichert wird nur, *dass* eine
Person einen Eintrag gelesen hat - es gibt keine Auswertung ueber Personen
hinweg, keine Zeitmessung und keine Erinnerungsfunktion. Die Bestaetigung
unterliegt trotzdem der Mitbestimmung, weil sie personenbezogen ist; sie sollte
also in der Dienstvereinbarung ausdruecklich erwaehnt werden.

## Personalvertretung (LPVG NRW)

Uebergaben, Audit-Log und Kaffeekassen-Ledger koennen als technische
Einrichtungen gelten, die geeignet sind, Verhalten oder Leistung von
Beschaeftigten zu ueberwachen (vgl. § 72 Abs. 1 Nr. 3 LPVG NRW). Vor dem
Wirkbetrieb sollte deshalb die Mitbestimmung des Personalrats eingeholt
werden, auch wenn eine Ueberwachung nicht bezweckt ist.

## Impressumspflicht (§ 5 TMG / § 18 MStV)

Seite unter `/impressum/` vorbereitet; zeigt Platzhalter, bis `OPERATOR_NAME`,
`OPERATOR_ADDRESS`, `OPERATOR_REPRESENTATIVE` und `OPERATOR_CONTACT` gesetzt
sind.

## Barrierefreiheit (EU-Richtlinie 2016/2102, BGG NRW)

| Anforderung | Stand |
| --- | --- |
| Barrierefreiheitserklaerung | Geruest unter `/barrierefreiheit/` vorhanden |
| Technische Basismassnahmen | Sprungmarke, Tastaturfokus, 44px-Bedienelemente, kein horizontales Scrollen, kein rein farbbasierter Status, helles/dunkles Farbschema |
| Formale Pruefung nach EN 301 549/WCAG 2.1 AA | steht noch aus |
| Geltungsbereich | Die Anwendung ist ein anmeldepflichtiges Extranet fuer Wachenpersonal; Art. 1 Abs. 4 der Richtlinie nimmt reine Intranet-/Extranetangebote von der Pflicht aus. Der Betreiber sollte diese Einordnung selbst pruefen und ggf. mit der eigenen Barrierefreiheitsbeauftragten/dem Barrierefreiheitsbeauftragten abstimmen. |
| Durchsetzungsverfahren | Kontakt zur zustaendigen Ueberwachungsstelle des Landes NRW durch den Betreiber zu ergaenzen |

## Externe Datenabrufe

RSS-/Verkehrsquellen, Abfallkalender (ICS) und Geocoding laufen ausschliesslich
gegen eine vom Betreiber vorab freigegebene Hostliste (`FEED_ALLOWED_HOSTS`,
`GEOCODING_HOST`), sind standardmaessig deaktiviert und uebertragen keine
personenbezogenen Nutzerdaten (siehe `docs/SECURITY-PRIVACY.md`). Bei
oeffentlichen Diensten Dritter (z.B. `nominatim.openstreetmap.org`) empfiehlt
sich fuer volle Datenkontrolle eine selbst gehostete Instanz.

## Was diese Software nicht abdeckt

- Vergaberechtliche Fragen bei Einfuehrung/Betrieb (z.B. Eigenbetrieb vs.
  Beauftragung Dritter)
- Aufbewahrungspflichten nach dem Landesarchivgesetz NRW fuer als amtliche
  Unterlagen eingestufte Eintraege
- IT-Sicherheitsvorgaben grosser/kritischer Rettungsleitstellen (KRITIS/NIS2);
  fuer eine einzelne Wache im hier beschriebenen Umfang in der Regel nicht
  einschlaegig, im Zweifel mit der eigenen IT-Sicherheitsbeauftragten/dem
  IT-Sicherheitsbeauftragten klaeren
