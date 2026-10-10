# Produktpräsentation: eine Schicht erleben statt eine Featureliste lesen

## Positionierung
Eine klare Arbeitsoberfläche für Wachorganisation, Übergaben und Tagesaufgaben. Keine erfundenen Kundenzahlen, Einsparquoten, Sicherheitszertifikate, Behördenfreigaben oder Wirksamkeitsversprechen. Die Website zeigt einen Ablauf und erklärt seine Grenzen.

## Dramaturgie
1. **Verstehen:** ein kurzer, konkreter Nutzen im Hero; prominenter Einstieg ohne Anmeldung.
2. **Erleben:** virtuelles Smartphone mit drei bedienbaren Ansichten: Überblick, Übergaben, Tagesaufgaben. Fiktive Musterinhalte; lokale Zustandsänderungen und expliziter Reset. Kenntnisnahme ist keine Erledigung.
3. **Einordnen:** wenige Funktionsblöcke statt einer vollständigen Modulliste; Browser/PWA, nativer Client und selbst betriebener Server sachlich voneinander unterscheiden.
4. **Vertiefen:** vorhandene echte Anwendung separat öffnen; diese Präsentationssimulation ersetzt keine Backend-, Kamera- oder Geräteabnahme.
5. **Vertrauen:** Quellcode und überprüfbare Produktgrenzen statt Logos erfundener Referenzkunden.

## Gestalterische Recherche und Transfer
Textuelle Referenzrecherche an https://linear.app, https://vercel.com und https://stripe.com: prägnante Produktbotschaft, Produkt im Mittelpunkt, progressive Information und klare Handlungsangebote. Keine behauptete vollständige visuelle Referenzabnahme, keine Kopie ihrer Assets.

Das bestehende OpenDesign-Transferpaket (v0.24.1, Commit `89e64d813bb1c7a11519b3f668f011f7017637d7`) und `docs/DESIGN-SYSTEM.md` dienen als Kontext für konsistente Tokens und Bedienbarkeit. Bestehende Integration ist im Bericht `wachbuch-modernisierung-berichte/design-integration-20261009/REPORT.md` dokumentiert. Kein neuer erfolgreicher Lauf der Upstream-OpenDesign-App behauptet.

## Qualitätsregeln
- Eigene CSS-/JS-Dateien, keine externen Tracker, Schrift-CDNs oder neue UI-Library.
- Responsive Layout, sichtbare Tastaturfokusse, native Buttons, beschriftete Navigation und reduzierte Bewegung.
- Ohne JavaScript bleiben Produktinformationen und der Weg zur echten Demo nutzbar; die Simulation muss ihren JS-Bedarf erklären.
- Keine patientenbezogenen Daten, kein Storage und keine Servermutation aus der Smartphone-Präsentation.
- Demo-Abläufe und Zustände mit echtem Browser prüfen, nicht nur mit HTML-Stringtests.

## Rolloutgrenze
Neue Präsentation auf dem eigenen Featurebranch entwickeln und als separate Vorschau veröffentlichen. Die bestehende öffentliche Demo, ihr Image, ihre Daten und ihre Startzeit unverändert erhalten. Backend-/Store-/Produktivrollout sind nicht Bestandteil dieser Arbeit.
