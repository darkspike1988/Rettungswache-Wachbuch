# Roadmap

## Phase 0 - technische Basis

- Docker-Deployment mit lokalem Login oder Tailscale
- Rollen, Uebergaben, Kalender, Geburtstage, Kaffeekasse und Behoerdenfeeds
- automatisierte Fach- und Zugriffstests

## Phase 1 - geschlossener Test

- reale Arbeitsablaeufe mit Testdaten durchspielen
- Rollenmatrix und Formulare mit dem Team vereinfachen
- Loeschfristen technisch umsetzen, sobald sie freigegeben sind
- Backup/Restore, Monitoring, Updates und Incident-Ablauf testen

## Phase 2 - formaler betrieblicher Pilot

- Datenschutz-/Mitbestimmungsunterlagen abschliessen
- verwaltete Benutzer und MFA-/Passkey-Strategie festlegen
- barrierearme Nutzung und gemeinsame Wachenterminals pruefen
- Audit-Export und automatisierte Restore-Tests ergaenzen

## Phase 3 - Produktion

- ASVS-L2-Sicherheitspruefung und Lasttest
- finalen Betriebs-, Support- und Notfallprozess abnehmen
- erst nach schriftlichem Go-live einen oeffentlichen DNS-Namen anbinden

Spaetere Optionen sind eine installierbare PWA, CalDAV-Export und weitere
offizielle Verkehrsdaten. Chat, Patientendaten, Dienstplanung und Uploads bleiben
ausserhalb des Wachbuchs, solange kein eigener freigegebener Zweck besteht.

## Mobiler Client (iOS und Android)

Ergaenzend zur server-gerenderten Oberflaeche entsteht ein plattformuebergreifender
Client (Repository `Wachbuch-Client`, Expo/React Native). Er greift ueber eine
schmale JSON-API auf denselben Server zu. Leitplanken aus der Recherche gelten
unveraendert: keine Patienten-, Gesundheits- oder Einsatzdaten, dokumentierte
Rechtsgrundlage je Zweck, stationsbezogene Rollen, unveraenderliche Audit- und
Kassenbuchungen sowie Datensparsamkeit (nur Tag und Monat bei Geburtstagen).

### Phase M0 - Lese-API und Verbindungsnachweis (umgesetzt)

- versionierte, read-only API unter `/api/v1/` (`status`, `uebersicht`)
- gleiche stationsbezogene Zugriffsregeln wie die HTML-Ansichten; Auditoren und
  Nutzer ohne Mitgliedschaft erhalten JSON-Fehler statt Inhalten
- Client zeigt Serverstatus und API-Version an
- Details siehe [`docs/API.md`](API.md)

### Phase M1 - Lesefunktionen

- Uebergabeliste und -detail, naechste Termine, eigener Kaffeekassenstand
- konsequente Rollen- und Modulpruefung je Endpunkt
- Paginierung und schlanke, cachefreundliche Antworten

### Phase M2 - Authentifizierung fuer native Apps und Schreibpfade (teilweise umgesetzt)

- Token-Anmeldung (`POST /api/v1/anmeldung/`) und Bearer-Auth umgesetzt; ein
  widerrufbarer Token-Speicher und eine MFA-/Passkey-Abstimmung stehen noch aus
- Schreibpfade umgesetzt: Uebergabe anlegen, Status aendern und Kaffeekasse buchen
  jeweils nur per Bearer-Token, mit Rollencheck, Validierung und Audit-Ereignis;
  Uebergaben werden versioniert. Idempotenz-/Replay-Schutz folgt noch
- CORS ausschliesslich fuer freigegebene Urspruenge; native Apps benoetigen es
  nicht (nur der Web-Build im Browser unterliegt CORS)

### Phase M3 - Haerte und Reichweite

- ASVS-L2-Pruefung der API zusaetzlich zur Weboberflaeche
- optionaler Offline-Cache ohne dauerhafte lokale Kopien sensibler Daten
- installierbare PWA als Alternative zum nativen Build pruefen

iOS-Builds erfordern macOS/Xcode; Android ist unter Linux baubar. Push-Dienste,
Uploads und personenbezogene Auswertungen bleiben ausserhalb des Wachbuchs, solange
kein eigener freigegebener Zweck und keine Mitbestimmung vorliegen.
