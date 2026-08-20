# Wachbuch-Vorführung

Die produktive Vorführung liegt in der Web-PWA unter **`/vorfuehrung/`**
(CSP-konform, Design-Tokens der App, Musik nur nach Klick).

Dieses Verzeichnis bleibt die eigenständige Folienfassung für Video-Export
und Vorführungen ohne laufenden Django-Prozess. **Nicht** über die PWA
ausgeliefert.

## Live zeigen (ohne Django)

Vom Repository-Root:

```bash
python3 -m http.server 8765
```

Dann im Browser:

`http://127.0.0.1:8765/docs/praesentation/index.html`

- Pfeiltasten oder **Weiter** / **Zurück**
- `?autoplay=1` blättert automatisch
- **Musik** startet eine kurze, eigens erzeugte Ambient-Figur (keine fremden Aufnahmen, keine GEMA-pflichtigen Titel)

## Video erzeugen

```bash
python3 docs/praesentation/render_video.py
```

schreibt `docs/praesentation/wachbuch-vorfuehrung.mp4` (lokal, nicht für Git vorgesehen).

## Inhaltliche Grenze

Die Folien nennen ausdrücklich: internes Wachenbuch, kein Einsatz-, Alarm- oder Patientensystem.
