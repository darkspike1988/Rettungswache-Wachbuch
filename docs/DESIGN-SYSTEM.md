# Wachbuch Klar - Designregeln

Stand: 28. Juli 2026

## Entscheidung

Die Webapp verwendet kein vollstaendiges Admin-Template. Tabler und vergleichbare
Dashboard-Vorlagen bringen fuer diesen Anwendungsfall zu viele Karten,
Kennzahlen, Icons und Bootstrap-Abhaengigkeiten mit. Pico CSS ist leicht, bildet
aber komplexere Rollen-, Fehler- und Pruefprozesse nicht ausreichend ab.

`Wachbuch Klar` ist deshalb eine kleine projektspezifische Oberflaeche. Sie uebernimmt
erprobte, nicht markengebundene Muster aus offenen Designsystemen:

| Quelle | Lizenz | Uebernommenes Muster |
|---|---|---|
| [GOV.UK Frontend](https://github.com/alphagov/govuk-frontend) | MIT | Task-first Seiten, Formstruktur, Fehlerzusammenfassung, Summary Lists |
| [NHS.UK Frontend](https://github.com/nhsuk/nhsuk-frontend) | MIT | Mobile-first Layout, klare Typografie, lineare Aufgabenlisten |
| [USWDS](https://github.com/uswds/uswds) | Public Domain/CC0 mit dokumentierten Dritt-Lizenzen | Responsive, semantische Tabellen |
| [Tabler](https://github.com/tabler/tabler) | MIT | Nur Referenz fuer App-Shells; bewusst nicht eingebunden |
| [Pico CSS](https://github.com/picocss/pico) | MIT | Semantisches HTML als Referenz; bewusst nicht eingebunden |

Es wurden keine Logos, Markenfarben, proprietaeren Schriften oder kopierten
Komponentenpakete eingebunden. Die eigene CSS-Schicht bleibt klein, lokal und
offline-faehig. Minimales JavaScript dient ausschliesslich der installierbaren
PWA (Service-Worker, Installationshinweis, Online-Status) und ist keine
Voraussetzung fuer die Kernablaeufe.

## Zehn verbindliche Regeln

1. Jede Seite hat genau eine Hauptaufgabe und genau eine `h1`.
2. Pro Ansicht gibt es hoechstens eine hervorgehobene Primaeraktion.
3. Das Dashboard zeigt Status der aktiven Uebergaben, einen kurzen Schnellzugriff
   auf Schichtaufgaben sowie die naechsten drei Termine.
4. Kritische Informationen stehen offen sichtbar, nie in einem geschlossenen
   Accordion oder nur hinter Farbe.
5. Status und Prioritaet werden immer ausgeschrieben. Farbe ist nur zusaetzlich.
6. Jedes interaktive Ziel ist mindestens 44 x 44 CSS-Pixel gross.
7. Mobile beginnt einspaltig; weitere Spalten entstehen erst ab ausreichendem
   Inhaltsplatz, nicht anhand bestimmter Geraetemodelle.
8. Fliesstext bleibt auf ungefaehr 65 bis 70 Zeichen pro Zeile begrenzt.
9. Listen und Schreibformulare liegen auf getrennten URLs.
10. Rot ist fuer dringende Zustaende und Fehler reserviert, nicht fuer Dekoration.

## Informationsarchitektur

Die globale Navigation besitzt vier Punkte:

- `Uebersicht`: priorisierte aktive Uebergaben und naechste Termine
- `Uebergaben`: Aktiv, Dringend und Archiv mit Pagination
- `Kalender`: chronologische Agenda
- `Mehr`: aktivierte Zusatzmodule und rollenabhaengige Verwaltung

Kalendertermine, Tagesaufgaben, Kassenbuchungen, Geburtstagsfreigaben und
Teamfreigaben werden jeweils auf einer eigenen Seite erfasst. Region zeigt nie
Nachrichten und Verkehr gleichzeitig, sondern einen ausgewaehlten Inhaltstyp.

Tagesaufgaben folgen der Wandtafel: gruene taegliche Routine, gelbe
Wochentagsrotation, blaue zusaetzliche Punkte. Details in
[`WALL-BLOCKS.md`](WALL-BLOCKS.md).

## Installierbare App (PWA)

Die Webapp bleibt serverseitig gerendert und kann als Standalone-App auf Handy
oder Wachenterminal installiert werden:

- Web-App-Manifest mit Shortcuts zu Uebersicht, Uebergaben und Dringend
- Service Worker mit Shell-Precache und Network-first fuer Lese-Navigation
- Offline-Hinweisseite; keine Offline-Schreibwarteschlange
- Safe-Area- und Standalone-Anpassungen fuer Notch und Home-Indicator
- ICS-Export einzelner Wachentermine fuer den Geraetekalender

## Responsive Verhalten

- Bis `48rem` beziehungsweise typischerweise 768 CSS-Pixel: eine Spalte,
  vierteilige Navigation am unteren Rand, mobile Key-Value-Tabellen.
- Ueber `48rem`: Navigation unter dem App-Header, Identitaet bleibt sichtbar.
- Bis `64rem`: Inhaltsbereiche bleiben einspaltig, damit Tablets nicht in enge
  Zwei-Spalten-Layouts gezwungen werden.
- Ueber `64rem`: nur die Uebersicht darf Uebergaben und Termine nebeneinander
  darstellen.
- Bei 320 CSS-Pixel darf die Gesamtseite nicht horizontal scrollen.

## Barrierefreiheit

Ziel ist WCAG 2.2 AA mit einer strengeren internen Touchziel-Vorgabe von 44
CSS-Pixeln. Verbindlich sind sichtbarer Tastaturfokus, semantische Tabellen,
permanente Feldlabels, Erhalt fehlerhafter Eingaben, Text plus Farbe fuer Status
und `prefers-reduced-motion`-freundliche Darstellung ohne notwendige Animation.

Referenzen:

- [WCAG 2.2 Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
- [WCAG 2.2 Target Size](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [WCAG 2.2 Use of Color](https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html)
- [GOV.UK Form structure](https://www.gov.uk/service-manual/design/form-structure)
- [NHS.UK Layout](https://service-manual.nhs.uk/design-system/styles/layout)
- [USWDS Table](https://designsystem.digital.gov/components/table/)
