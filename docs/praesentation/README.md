# Wachbuch-Vorführung

Eigenständige Folien für Nutzer- und Dienststellenvorführungen. **Nicht** Teil der produktiven Web-PWA (eigenes HTML, kein Django-Template).

## Live zeigen

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
