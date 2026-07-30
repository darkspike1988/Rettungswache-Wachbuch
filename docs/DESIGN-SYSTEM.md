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
Komponentenpakete eingebunden. Die eigene CSS-Schicht bleibt klein, lokal,
offline-faehig und ohne JavaScript-Abhaengigkeit.

## Zehn verbindliche Regeln

1. Jede Seite hat genau eine Hauptaufgabe und genau eine `h1`.
2. Pro Ansicht gibt es hoechstens eine hervorgehobene Primaeraktion.
3. Es gibt kein Dashboard. Die laufende Woche ist die Startseite; dieselben
   Daten werden nicht in einer zweiten Ansicht wiederholt.
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

Die globale Navigation besitzt drei Punkte. Mehr braucht es nicht, und eine
Sammelschublade namens `Mehr` gibt es ausdruecklich nicht mehr:

- `Woche` (`/`): die laufende Kalenderwoche mit Team und Aufgabenstand je Tag,
  Allgemeines und einem offenen Hinweisstreifen auf dringende, noch nicht
  bestaetigte Eintraege. Das ist die Anwendung, nicht ein Reiter darin.
  Die Aufgaben eines Tages (`/aufgaben/<datum>/`) haengen an diesem Tag und
  bekommen ausdruecklich **keinen** vierten Menuepunkt.
- `Suchen` (`/suchen/`): Aktiv, Dringend und Archiv mit Volltextsuche. Eine
  Liste mit Filtern dient dem Wiederfinden - also heisst sie so.
- `Wache` (`/wache/`): Module im Dienst (Kalender, Kaffeekasse, Geburtstage,
  optionale externe Quellen) und darunter, rollenabhaengig, die Verwaltung
  (Aufgabenlisten, Team, Einstellungen, Audit). Angelegt wird hier, abgehakt
  wird am Tag - Verwaltung und taegliche Bedienung teilen sich keine Seite.

Persoenliches liegt beim eigenen Namen oben rechts (`/konto/`): Passwort,
Zwei-Faktor-Anmeldung, freiwillige Geburtstagsangabe. Es gehoert nicht in einen
gemeinsamen Bereich mit Wachenverwaltung.

Schreibvorgaenge liegen weiterhin auf eigenen URLs. Alte Adressen
(`/uebergaben/`, `/wochenprotokoll/`, `/mehr/`) leiten dauerhaft weiter, damit
Lesezeichen nicht ins Leere laufen.

## Responsive Verhalten

- Bis `48rem` beziehungsweise typischerweise 768 CSS-Pixel: eine Spalte,
  vierteilige Navigation am unteren Rand, mobile Key-Value-Tabellen.
- Ueber `48rem`: Navigation unter dem App-Header, Identitaet bleibt sichtbar.
- Bis `64rem`: Inhaltsbereiche bleiben einspaltig, damit Tablets nicht in enge
  Zwei-Spalten-Layouts gezwungen werden.
- Ueber `64rem`: der Inhalt bleibt einspaltig. Die Wochenansicht lebt von
  vertikaler Lesbarkeit, nicht von Spalten.
- Bei 320 CSS-Pixel darf die Gesamtseite nicht horizontal scrollen.

## Bewegung

Im Arbeitswerkzeug bewegt sich beim Laden nichts. Die Seite steht sofort, weil
jemand um drei Uhr nachts etwas nachsehen will und nicht auf eine Einblendung
warten moechte. Bewegung gibt es nur als Rueckmeldung auf eine eigene Handlung -
ein Aufklappen, ein Tastendruck.

Die Demoseite darf mehr: dort erklaeren horizontale Slides und ein
scrollgebundener Fortschrittsbalken das Produkt. Das ist Marketing und gehoert
nicht in die Wochenansicht.

Verbindlich:

1. Jede Animation endet nach hoechstens 0,35 Sekunden.
2. Unter `prefers-reduced-motion: reduce` bleibt jede Animation aus.
3. Kein Inhalt ist erst nach einer Animation lesbar oder bedienbar.
4. Kein Einblenden beim Seitenaufbau im Werkzeugteil.
5. Slides und andere Scrollbereiche scrollen in sich, die Gesamtseite bleibt
   ab 320 Pixel frei von horizontalem Scrollen.

Fuellstaende und andere berechnete Groessen kommen als CSS-Klasse, nicht als
`style`-Attribut: die Content-Security-Policy erlaubt keine Inline-Styles.

## Touchbedienung

Tablets und Smartphones sind der Hauptfall, nicht die Ausnahme. Maßgeblich ist
`pointer: coarse` und nicht die Fensterbreite - ein Tablet im Querformat ist
breit und trotzdem Touch.

1. Hovereffekte gelten nur unter `(hover: hover) and (pointer: fine)`. Sonst
   bleibt auf Touch ein Hoverzustand nach dem Antippen haengen und sieht wie
   eine Auswahl aus.
2. Unter `pointer: coarse` wachsen Bedienziele auf mindestens 48 Pixel,
   Eingabefelder ebenfalls, und die Abstaende werden groesser.
3. Interaktive Elemente tragen `touch-action: manipulation` - das nimmt die
   Verzoegerung durch die Doppeltipp-Zoom-Erkennung.
4. Statt Hover gibt es auf Touch eine `:active`-Rueckmeldung.
5. Eingabefelder bleiben bei mindestens 16 Pixel Schriftgroesse, damit iOS beim
   Fokus nicht hineinzoomt.

## Dichte statt Karten

Gegliedert wird mit Weissraum und Trennlinien. Rahmen und Flaechen nur, wo
wirklich etwas abgegrenzt werden muss - flaechendeckende Karten lassen jede
Anwendung wie einen Dashboard-Baukasten aussehen und kosten Platz, der dem
Inhalt fehlt. Zwei bis drei abgegrenzte Flaechen pro Seite sind das Maximum.

Die Typo-Skala ist die eines Werkzeugs, nicht einer Startseite: `h1` bei
1,6rem, Abschnittstitel bei 1,05rem. Grosse Anzeigengroessen verschenken auf
einem Diensthandy die halbe Sichtflaeche.

## Keine Mehrfachbenennung

Ein Name erscheint einmal pro Seite. Der Wachenname steht mittig im
Kopfbereich - nicht zusaetzlich neben der Rolle und nicht in der Kontextzeile.
In Listenzeilen steht der Personenname einmal; Aktionslinks heissen
`Bearbeiten` und tragen den Namen nur unsichtbar fuer Screenreader nach.

Ein Zustand wird einmal ausgedrueckt. Eine abgehakte Aufgabe traegt die Marke
`Erledigt` rechts; die Zeile darunter nennt nur noch Person und Uhrzeit, nicht
noch einmal den Zustand. Ein Wort bezeichnet eine Sache: eine Sammlung heisst
`Aufgabenliste`, ein Punkt darin `Aufgabe` - nicht abwechselnd Checkliste,
Vorlage und Punkt.

Ausdruecklich keine Doppelung sind: der Navigationspunkt der aktuellen Seite
neben deren `h1` (Navigation und Seitentitel sind verschiedene Dinge, beide
sind fuer Orientierung und Struktur notwendig) und gleiche Werte in
verschiedenen Datenzeilen.

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
