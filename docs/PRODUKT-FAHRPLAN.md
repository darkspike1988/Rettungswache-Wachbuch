# Produkt-Fahrplan: homogenes Wachbuch (Server + Client)

Stand: 2026-08. Dieser Fahrplan verzahnt den Django-Server
(`Rettungswache-Wachbuch`) mit dem Flutter-Client
(`Wachbuch-Client`) zu einem homogenen Produkt. Er wird Stueck fuer Stueck in
kleinen, getesteten PRs abgearbeitet.

Statuskonvention (wie `AGENTS.md`):

- `[ ]` offen
- `[~]` begonnen / nicht vollstaendig abgenommen
- `[x]` umgesetzt und durch Tests belegt
- `[!]` blockiert (Grund + naechste Aktion daneben)

## Produktgrenze (nicht verhandelbar)

Alle Phasen bleiben im Wachalltag/Organisations-Rahmen. **Keine** Patienten-,
Einsatz-, Alarmierungs-, Diagnose- oder Leistungsdaten. Karten dienen
Infrastruktur (Standorte, Hydranten, Sammelplaetze), nicht Einsatz-/Personen-
Tracking. Es gelten weiterhin alle Invarianten aus `AGENTS.md`
(Stationsbindung, Append-only-Audit, CSP ohne `unsafe-inline`, kein `|safe`,
E2EE-Vertrauensmodell).

## Ist-Stand (Ausgangspunkt)

- Server: Uebergaben, Maengel, Geraete/Statusboard, Inventar, Checklisten,
  Kalender, Kaffeekasse, Aufgaben/Wandtafel, Feeds, Team/Rollen, Audit,
  **oeffentlicher Chat (E2EE), privater 1:1-Chat (E2EE), Secure Mail (E2EE)** –
  Chat bisher nur im Web, keine Gruppen, keine Chat-API.
- Client: Uebergaben, Maengel, Geraete/Inventar, Checklisten, Kalender,
  Kaffeekasse, Auswertung, Konto, Demo-Profile – **kein Chat, keine Pinnwand**.
- Fehlt gesamthaft: **Pinnwand**, **Chatgruppen**, **Chat im Client**,
  Pruef-/Wartungsfristen mit Erinnerungen, Qualifikationsverwaltung, Karten.

## Phasen

### Phase 0 – Fundament (Dev-Umgebung) `[x]`

Cloud-Agent-Umgebung fuer Server + Client (venv/Django + Flutter-SDK,
`install`/`start`, Terminals fuer beide Dev-Server). Belegt durch gruenen
Environment-Build + Fresh-Agent-Verifikation.

### Phase 1 – Digitale Pinnwand (Aushaenge/Notizen) `[ ]`

Stationsinterne Pinnwand fuer kurze Aushaenge/Hinweise, getrennt von den
strukturierten Uebergaben.

- Server: Modell `PinboardNote` (station-gebunden, Autor, Titel, Text,
  angepinnt, archiviert), Service + Audit, Views/Templates, Modul-Toggle
  `Station.pinboard_enabled`, Negativ-/Scope-Tests.
- API: `/api/v1/pinnwand/` (Liste/Erstellen/Pin/Archiv), Scopes, `/me`-Modulflag.
- Client: `WachbuchApi`-Methoden + Modell + Screen + l10n + Demo-Parity + Tests.
- Abnahme: Server-Tests + `flutter test` + Browser-Demo.

### Phase 2 – Chat im Client (oeffentlich/privat/Secure Mail) `[ ]`

Vorhandenen Server-Chat mobil verfuegbar machen.

- API: versionierte Endpunkte fuer Wachenchat, private Threads und Secure Mail
  (Envelope-Weitergabe wie im Web, Server entschluesselt nie).
- Client: E2EE in Dart (ECDH P-256, AES-256-GCM, HKDF-SHA-256), Schluessel-
  Entsperrung mit Passphrase im Secure Storage, Chat-/Mail-Screens.
- Abnahme: Vertrags-Tests API, Krypto-Roundtrip-Tests im Client.

### Phase 3 – Chatgruppen `[ ]`

Mehrpersonen-Gruppenraeume zusaetzlich zu 1:1 und Wachenchat.

- Server: `ChatGroup` + Mitglieder + `GroupMessage` (E2EE, `key_wraps` je
  Mitglied), Rollen/Verwaltung, Web-UI, Scope-Tests.
- Client: Gruppen-UI + Gruppen-E2EE (Rewrap bei Mitgliederaenderung).

### Phase 4 – Pruef-/Wartungsfristen + QR-Geraetekarten + Erinnerungen `[ ]`

Groesster Pain Point (Haftung, DGUV). Baut auf `Geraete`/`Maengel`/
`Checklisten`/Web-Push auf.

- Server: Prueffristen/Intervalle je Asset/PSA, Ablauf-Erinnerungen (Push),
  QR-Code je Geraet → Geraetekarte/Pruefhistorie/Sofort-Mangelmeldung, API.
- Client: Geraetekarte per QR-Scan (Client hat bereits `mobile_scanner`),
  Prueflisten, Erinnerungsanzeige.

### Phase 5 – Qualifikations-/Tauglichkeitsverwaltung `[ ]`

Qualifikationen/Tauglichkeiten/Lehrgaenge (z. B. G26, Fuehrerschein,
Fortbildungen) mit Ablauf-Erinnerungen. Klar abgegrenzt von voller
tarif-/arbeitszeitrechtlicher Dienstplanung.

### Phase 6 – Karten (Leaflet/MapLibre) `[ ]`

Lokal gebuendelt, self-hostbare Tiles. Standorte Gerätehäuser/Wachen,
Hydranten/Loeschwasser, Sammelplaetze, Abfallkalender-Routen. CSP-konform via
`json_script`; Client via `flutter_map`/MapLibre. Innerhalb der Produktgrenze.

### Phase 7 – Homogenisierung `[ ]`

Einheitliche Navigation/Design-Paritaet Server↔Client, Modul-Toggles ueberall,
Barrierefreiheit, Doku (`README`, `docs/`), Aktualisierung der
Go-live-Checkliste.

## Arbeitsweise je Phase

1. Server: Modell/Migration → Service+Audit → Views/Templates → Modul-Toggle →
   Tests (inkl. Cross-Station-Negativtests).
2. API: versionierte Endpunkte + Vertrags-Tests, `/me`-Modulflag.
3. Client: `WachbuchApi` + Modell + Screen + l10n (de/en) + Demo-Parity + Tests.
4. Abnahme: Server-Tests, `flutter analyze` + `flutter test`, Browser-/Manuelltest.
5. Diesen Fahrplan-Status aktualisieren; PR mit Ursache/Risiko/Tests/Grenzen.
