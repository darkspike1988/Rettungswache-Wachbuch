# Sicherheitsrichtlinie

## Unterstützte Versionen

Sicherheitskorrekturen werden für den aktuellen Stand des `main`-Branches bereitgestellt. Es gibt derzeit keine langfristig unterstützten Releases.

## Schwachstellen melden

Bitte Sicherheitsprobleme nicht als öffentliches Issue mit Exploitdetails oder echten Daten melden. Nutze stattdessen GitHub Private Vulnerability Reporting im Bereich `Security` dieses Repositorys. Falls diese Funktion nicht erreichbar ist, eröffne ein Issue ohne technische Details und bitte um einen privaten Kontaktkanal.

Eine Meldung sollte betroffene Version, Auswirkung, reproduzierbare Schritte und mögliche Abhilfe enthalten. Niemals fremde Systeme oder Produktivdaten testen.

## Produktions-Sicherheitsprofil

Wachbuch ist so ausgelegt, dass Betreiber einen gehärteten DSGVO-/BSI-orientierten Betrieb konfigurieren können. Daraus folgt **keine BSI-Zertifizierung und keine pauschale DSGVO-Konformitätsgarantie**.

Verbindliche Betreiberunterlagen:

- `docs/DSGVO-BSI-COMPLIANCE.md`
- `docs/DSGVO-TOM.md`
- `docs/DATENSCHUTZ-INFORMATION-ART13.md`
- `docs/LOESCHKONZEPT.md`
- `docs/VVT-TEMPLATE.md`
- `docs/DSFA-VORPRUEFUNG.md`
- `docs/MOBILE-DEVICE-BETRIEB.md`

Vor Produktivbetrieb mindestens:

- separaten zufälligen `CRYPTO_MASTER_KEY` verwenden,
- `MFA_REQUIRED=true` setzen,
- `SECURE_COOKIES=true` setzen,
- konkrete Audit-/Log-/Backup-Aufbewahrungsfristen konfigurieren,
- TLS am Reverse Proxy nach aktuellem freigegebenem Sicherheitsprofil härten,
- Datenbank- und Backupmedien verschlüsseln,
- Restore-, Patch-, Incident- und Geräte-/MDM-Prozesse dokumentieren,
- Verantwortlichen, Datenschutzbeauftragte/n (falls erforderlich), Rechtsgrundlagen, VVT, TOMs und DSFA-Entscheidung organisatorisch freigeben.

`python manage.py check --deploy` enthält zusätzliche Wachbuch-Warnungen (`wachbuch.W101`–`W104`) für wesentliche fehlende Produktions-Härtung. Ungeklärte Warnungen gelten im dokumentierten Produktionsprofil als Release-Blocker.

## Kryptografie

Ausgewählte serverseitige Geheimnisse werden mit AES-256-GCM geschützt. Für Produktion muss der Master-Key vom Django-Secret getrennt und sicher verwahrt werden. Die technischen Empfehlungen orientieren sich an den im Compliance-Dokument referenzierten BSI-Richtlinien; konkrete TLS-/Schlüsselparameter müssen bei jeder Freigabe gegen deren aktuellen Stand geprüft werden.

Mobile App-Tokens und Offline-Snapshots liegen im Betriebssystem-Secure-Storage. Produktive App-Verbindungen verwenden HTTPS.

## Mängelfotos

Mängelfotos sind kein allgemeines Dateiarchiv. Der Server validiert Format und Größe und re-encodiert neu gespeicherte Bilder als frisches JPEG aus den decodierten Pixeln. Quell-Metadaten wie EXIF/GPS/XMP/Text/ICC werden dabei nicht übernommen. Patienten-, Einsatz- oder andere sachfremde sensible Inhalte dürfen organisatorisch nicht in Wachbuch gespeichert werden.

## Änderungen an Sicherheitsmechanismen

Änderungen an Kryptografie, Authentication, Secure Storage, TLS, Berechtigungen, Retention oder Backup/Restore benötigen:

1. eigenen nachvollziehbaren Change,
2. Tests/Migrationsplan,
3. Dependency-/Vulnerability-Prüfung,
4. Review der Dokumentation/TOMs,
5. bei mobilen Storage-Migrationen einen echten Geräte-Upgrade-Test vor breitem Rollout.
