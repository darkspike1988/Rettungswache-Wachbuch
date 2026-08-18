# Template-Evaluation: Wachbuch-Webapp

Stand: 14. August 2026. Anlass: Überprüfung der Architekturentscheidung in
`docs/DESIGN-SYSTEM.md`, die bewusst gegen fertige Admin-Templates entschieden
hat. Dieses Dokument bewertet fair, ob ein schlankes CSS-Framework die
harten Anforderungen des Projekts erfüllen kann.

## Harte Anforderungen (nicht verhandelbar)

Diese Anforderungen ergeben sich aus `AGENTS.md`, `docs/SECURITY-PRIVACY.md`,
`docs/DESIGN-SYSTEM.md`, `docs/COMPLIANCE.md` und dem BOS-/Behörden-Kontext:

| # | Anforderung | Quelle |
|---|---|---|
| 1 | Offline-fähig, keine CDN-Abhängigkeit zur Laufzeit | CSP `default-src 'self'`, PWA-Service-Worker |
| 2 | CSP ohne `unsafe-inline` / `unsafe-eval` | `AGENTS.md` Invariante |
| 3 | WCAG 2.2 AA, 48 px Touch-Ziele | `DESIGN-SYSTEM.md`, Client-Parität |
| 4 | BOS-/öffentlicher-Dienst-Ästhetik, feldlesbar, ruhig | `DESIGN-SYSTEM.md` |
| 5 | Kanonische Design-Tokens (Brand `#0D47A1` etc.) | `DESIGN-SYSTEM.md`, Client-Parität |
| 6 | Domänenspezifische Fachkomponenten erhalten | `.task-band`, `.week-board`, `.chat-bubble`, `.agenda-waste`, `.priority-*` |
| 7 | Keine gemeinsam genutzten Konten / kein Tracking | `README.md`, `SECURITY-PRIVACY.md` |
| 8 | Reproduzierbare, auditierte Lieferkette | `REMEDIATION-ROADMAP` R-012 |

## Kandidaten

### Pico.css v2 (MIT) – classless-Variante

- **Größe**: ~10 KB minifiziert (~3 KB gzip)
- **Offline**: Ja, self-hostbar als reine CSS-Datei, kein JS, keine Runtime-Abhängigkeit
- **CSP**: Kompatibel (kein Inline-JS, keine externen Ressourcen bei Self-Hosting)
- **WCAG**: v2 explizit mit Accessibility-Fokus; dunkles/helles Theme nativ
- **Tokens**: Eigene CSS-Variablen, überschreibbar mit den kanonischen Wachbuch-Tokens

**Bewertung**: Pico styled native HTML-Elemente (`<button>`, `<nav>`, `<article>`,
`<table>`, `<dialog>`). Für die generische Shell (Header, Formulare, Tabellen,
Buttons, Fehlerzusammenfassungen) geeignet. Die ~60 domänenspezifischen
Fachkomponenten müssten als eigene CSS-Schicht **zusätzlich** erhalten bleiben –
Pico ersetzt sie nicht.

### Water.css (MIT)

- **Größe**: ~2 KB gzip, eine Datei
- **Offline**: Ja, self-hostbar
- **CSP**: Kompatibel
- **WCAG**: Grundlegend; keine 48-px-Touch-Vorgabe, keine komplexeren Komponenten
- **Tokens**: Wenige Variablen, weniger anpassbar als Pico

**Bewertung**: Sehr minimal, deckt aber Rollen-, Fehler- und Audit-Prozesse
schlechter ab als der bestehende Code. Die bestehende `app.css` (1380 Zeilen)
ist bereits komponentenreicher als Water.css. Netto kein Gewinn.

### GDCSS (GOV.UK-Stil, MIT)

- **Größe**: klein, GOV.UK-Design-System orientiert
- **Offline**: Self-hostbar
- **WCAG**: Sehr stark (GOV.UK ist eine Accessibility-Referenz)
- **Tokens**: GOV.UK-Farben, nicht BOS-Blau

**Bewertung**: Design-System.md nennt GOV.UK bereits als *Muster-Referenz*
(Task-first, Fehlerzusammenfassung, Summary Lists), bindet es aber bewusst
nicht als Paket ein. GDCSS würde die BOS-Farbpalette nicht nativ liefern.

### Vollständige Admin-Templates (Tabler, Bootstrap-basiert)

Explizit ausgeschlossen in `DESIGN-SYSTEM.md`:
> „Tabler und vergleichbare Dashboard-Vorlagen bringen [...] zu viele Karten,
> Kennzahlen, Icons und Bootstrap-Abhängigkeiten mit."

Keine weitere Betrachtung – widerspricht der dokumentierten Entscheidung.

## Eigenschaften des bestehenden „Wachbuch Klar"-Systems

Die aktuelle `core/static/core/app.css` (1380 Zeilen, token-basiert) bietet
bereits:

- Komplette Token-Tabelle identisch zum Flutter-Client
- BOS-optimierte Fachkomponenten (`.task-band`, `.week-board`, `.agenda-waste`)
- 48-px-Touch-Standard via `--touch: 3rem`
- CSP-konform, offline-fähig, lokale Source Sans 3
- `prefers-reduced-motion`, Safe-Area, Skip-Link, Fokus-Indikator
- Append-only-/Audit-spezifische UI-Muster

## Fazit und Empfehlung

| Kriterium | Pico.css | Water.css | bestehendes System |
|---|---|---|---|
| Offline/CSP | ✓ | ✓ | ✓ |
| WCAG 2.2 AA | ✓ | ~ | ✓ (+48px) |
| BOS-Tokens nativ | überschreibbar | kaum | ✓ |
| Fachkomponenten | fehlen | fehlen | ✓ |
| Zusätzliche Abhängigkeit | ja | ja | nein |
| Migration nötig | ja (Shell-Templates) | ja | nein |

**Empfehlung: bestehendes System beibehalten, nicht durch ein Template ersetzen.**

Begründung:

1. Die harten Anforderungen (Offline, CSP, BOS-Ästhetik, 48 px, Token-Parität
   zum Client) werden vom bestehenden System **bereits voll erfüllt**.
2. Kein schlankes Template liefert die domänenspezifischen Fachkomponenten
   (Wochenwand, Aufgabenbänder, Kaffeekassen-Ledger, E2EE-Chat). Diese müssten
   in jedem Fall als eigene Schicht erhalten bleiben.
3. Ein Template würde eine **zusätzliche** Abhängigkeit einführen und eine
   Shell-Migration auslösen, ohne den BOS-Fachanteil zu berühren. Netto
   entstünde Mehrarbeit ohne Qualitätszuwachs.
4. Die dokumentierte Entscheidung in `DESIGN-SYSTEM.md` bleibt damit stimmig.

## Stattdessen empfohlene Design-Arbeiten

Anstatt ein Template einzuführen, die bestehende Implementierung konsistenter
und reifer machen:

1. **Token-Audit**: prüfen, ob alle Templates die kanonischen Tokens nutzen und
   keine hartkodierten Farben enthalten.
2. **Komponentenkonsistenz**: z. B. einheitliche Card-/Button-Varianten über alle
   Templates hinweg.
3. **Dark-Mode**: Client hat bereits `app_theme.dart` + `solar_theme.dart`;
   Webapp hat bisher nur Light. Prüfen, ob ein Dark-Schema für
   Wachenterminals/AMP wertvoll ist.
4. **PR #48 (Landingpage-Redesign) abschließen**: der offene Entwurf wendet das
   „Wachbuch Klar"-System konsequent an (hell & ruhig) und sollte
   reviewt/merged werden.
5. **Barrierefreiheits-Abnahme R-018**: die Code-Basis ist vorbereitet; die
   manuelle 400-%-Zoom-/Screenreader-Abnahme steht laut Roadmap noch aus.

## Entscheidung

Dieses Dokument dokumentiert die Evaluation. Die architektonische Entscheidung
in `docs/DESIGN-SYSTEM.md` bleibt bestehen, da die Evaluation sie bestätigt.
