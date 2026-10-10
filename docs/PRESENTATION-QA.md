# Separate Produktpräsentation — Abnahme

## Ausgeliefertes Artefakt
- HTTPS: https://wachbuch-preview.46-225-106-237.sslip.io/
- Eigener statischer Container `wachbuch-presentation-preview` auf Hetzner; nur `127.0.0.1:18091` veröffentlicht, HTTPS über bestehenden Caddy mit additivem Hot-Reload.
- Compose/Build: `deploy/presentation/`; gerenderter Django-Templateexport, lokale Schriftdateien, keine Datenbank und keine App-Session.
- CSP ohne unsafe-inline/unsafe-eval; connect-src und form-action auf none. Keine Browserpersistenz der fiktiven Beispieldaten.

## Tatsächlich ausgeführt
- Django: 304 Tests, OK, 1 Skip. Log: `/opt/data/cache/presentation-qa/django-tests.log`.
- Migrationsprüfung: keine Änderungen. JavaScript: node --check erfolgreich.
- Lokaler UND öffentlicher Chromium-Durchlauf: 1440, 768, 390 und 320 Pixel; drei Übergaben/Revisionen, Kenntnisnahme unabhängig von Aufgaben, Rücksetzen, Tastaturfokus, FAQ, reduzierte Bewegung, No-JS-Hinweis; keine JS-/Konsolen-/HTTP-Fehler, XHR oder Speicherung.
- Reproduzierbare Browserprüfung: `scripts/test_presentation_browser.py URL`; benötigt Playwright und Chromium, Pfade über PRESENTATION_QA_DIR und CHROMIUM_EXECUTABLE konfigurierbar.
- Öffentlicher Browserlog: `/opt/data/cache/presentation-qa/public-browser.log`. Screenshots und JSON im selben Verzeichnis.
- Öffentliche HTML-/CSS-/JS-Bytes identisch mit dem lokal getesteten Export (SHA-256 geprüft).

## Gefundene und behobene Fehler
- Zu breiter data-pw-rev-Selektor zerstörte Übergabekarten; Kenntnisnahme las Karteninhalt statt Revisionsnummer. Reale Browserregression für alle drei Karten ergänzt.
- Primäre Linkbuttons: korrekte Textfarbe; lesbarere Prioritäts-/Bestätigungsfarben und sichtbarer zweifarbiger Tastaturfokus.
- Originales Caddy-Image besitzt eine net_bind_service-Dateicapability. Sie verhindert exec bei nichtprivilegiertem Nutzer mit cap_drop ALL. Im separaten Image entfernt, da Port 8080 keine privilegierten Portrechte benötigt. Sicherheitsbeschränkungen nicht aufgeweicht.

## Geschützte Demo
- Alte URL weiterhin HTTP 200 mit bisheriger Hauptüberschrift.
- Container `wachbuch-public-demo`: Startzeit weiterhin 2026-10-08T14:21:29.186296216Z, Image weiterhin sha256:07eb4ddf09113e9b88d18205daaa6c5cd7a5aad7807b2d4f4c6dfdd9979346e3.
- Bestehende Caddy-Konfiguration bytegenau als Präfix erhalten; Backup `/opt/wachbuch-presentation-preview/Caddyfile.before-20261010T200328Z`. Reload HTTP 200; kein Neustart des öffentlichen Proxy-Containers.

## Grenzen
- Smartphone ist ausdrücklich eine interaktive Produktvorschau, kein realer Flutter-Client und keine Backend-Session.
- Keine Screenreader-/Hardwareabnahme und keine behauptete WCAG-Zertifizierung.
- check --deploy zeigte Warnungen der isolierten Dummy-Testkonfiguration: Testsecret, fehlender CRYPTO_MASTER_KEY, MFA aus und fehlende Audit-Aufbewahrungsfrist. Keine Produktionsfreigabe daraus abgeleitet. Der statische Vorschaucontainer betreibt Django und diese Testkonfiguration nicht.
- Kein main-Merge, Produktivdaten-Rollout oder Storepublishing.
