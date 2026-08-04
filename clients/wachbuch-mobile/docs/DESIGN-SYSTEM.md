# Wachbuch Design System

Stand: August 2026. Systemunabhängiges Design für iOS, Android und Web-PWA.

## Prinzipien

1. **WCAG AAA Kontrast** (mindestens 7:1) — nutzbar bei Sonne, Nachtschicht, Helm-Beleuchtung
2. **48dp Touch-Ziele** — bedienbar mit Handschuhen und in Eile
3. **Farbcodierung** — Rot/Gelb/Grün/Blau einheitlich für Prioritäten und Status
4. **Mindest-Schriftgröße 14sp** — lesbar auf Wachenterminals und Handys
5. **Dark/Light/HighContrast** — Solar-Berechnung, manueller Override, Emergency-Modus

## Farbpalette

### Prioritäten (Übergaben)

| Token | Hex | Bedeutung |
| --- | --- | --- |
| `urgent` | `#DC2626` | Dringend — sofortige Aufmerksamkeit |
| `important` | `#F59E0B` | Wichtig — zeitnahe Bearbeitung |
| `normal` | `#2563EB` | Normal — reguläre Bearbeitung |
| `done` | `#16A34A` | Erledigt — abgeschlossen |

### Status

| Token | Hex | Bedeutung |
| --- | --- | --- |
| `statusOpen` | `#2563EB` | Offen |
| `statusInProgress` | `#F59E0B` | In Bearbeitung |
| `statusDone` | `#16A34A` | Erledigt |

### Semantic

| Token | Hex |
| --- | --- |
| `error` | `#DC2626` |
| `success` | `#16A34A` |
| `warning` | `#F59E0B` |
| `info` | `#2563EB` |

### Brand

| Token | Hex |
| --- | --- |
| `brandDeep` | `#17343D` |
| `brandAccent` | `#2563EB` |

## Typography

| Rolle | Größe | Gewicht |
| --- | --- | --- |
| Caption | 12sp | Regular |
| Body | 14sp | Regular |
| Title | 16sp | Medium |
| Headline | 20sp | SemiBold |
| Display | 28sp | Bold |

## Spacing

| Token | Wert |
| --- | --- |
| `xs` | 4dp |
| `sm` | 8dp |
| `md` | 12dp |
| `lg` | 16dp |
| `xl` | 24dp |
| `2xl` | 32dp |

## Touch-Ziele

Alle interaktiven Elemente: **mindestens 48×48dp** (WCAG 2.5.5).

## Komponenten

### PriorityBadge
`lib/ui/priority_badge.dart` — Farbcodiertes Badge für Übergabe-Priorität.
- Props: `priority` (urgent/important/normal/done), `compact`, `label`
- Hintergrund: 12% Opazität der Prioritätsfarbe
- Rand: 50% Opazität
- Punkt-Indikator + Text

### StatusChip
`lib/ui/status_chip.dart` — Status-Anzeige für Übergaben.
- Props: `status` (open/in_progress/done), `label`
- Abgerundete Ecken (radiusMd)

### CopyIconButton
`lib/ui/copy_button.dart` — Einheitlicher Copy-Button.
- Props: `text`, `label`, `iconSize`
- Clipboard.setData + SnackBar-Feedback
- 48dp Minimum

## Themes

### Standard (Solar)
Automatischer Wechsel hell/dunkel nach Sonnenaufgang/-untergang.
Siehe `lib/theme/app_theme.dart` und `lib/theme/solar_theme.dart`.

### HighContrast (Emergency)
`lib/theme/high_contrast_theme.dart` — Schwarz/Weiß mit maximalem Kontrast.
- Light: Weißer Hintergrund, schwarzer Text
- Dark: Schwarzer Hintergrund, weißer Text
- Alle Buttons mit fetter Schrift
- Karten mit schwarzem Rand

Aktivierung über Settings → "Hoher Kontrast / Notfall-Modus".

## Barrierefreiheit

- **Kontrast**: Alle Text/Farb-Kombinationen erreichen mindestens 7:1 (WCAG AAA)
- **Touch-Ziele**: 48dp Minimum für alle interaktiven Elemente
- **Text-Skalierung**: Layouts bleiben bei 200% Skalierung stabil
- **Screenreader**: Semantische Labels auf allen Icons, `aria-live` auf Fehlermeldungen
- **Farb-Blindheit**: Priorität nicht nur durch Farbe, sondern auch durch Punkt-Indikator + Text-Label

## Rettungsdienst-spezifische Patterns

1. **Dringend-Badge in Navigation**: Zahl der dringenden Übergaben als rotes Badge
2. **Große Saldo-Anzeige**: Kaffeekasse-Saldo mit hoher Lesbarkeit
3. **Quick-Access Kacheln**: Dashboard-Module groß und gut tippbar
4. **Offline-Indikator**: Sichtbares Banner bei fehlender Verbindung
5. **Demo-Modus Banner**: Gelbes Band für Test-Instanzen
