# JSON-API (v1)

Schmale, ausschliesslich lesende JSON-Schnittstelle fuer den mobilen Client
(`Wachbuch-Client`). Sie spiegelt die stationsbezogenen Zugriffsregeln der
Weboberflaeche und gibt nur Daten zurueck, die die angemeldete Person ohnehin im
Interface sehen darf. Es gibt keine Schreibpfade und keine Patienten-,
Gesundheits- oder Einsatzdaten.

Basis-Pfad: `/api/v1/`. Authentifizierung wahlweise ueber die bestehende
Django-Session (Login unter `/anmelden/`) oder ueber einen Bearer-Token aus
`POST /api/v1/anmeldung/`. Bis auf den Login akzeptieren alle Endpunkte nur `GET`.

## Authentifizierung fuer native Apps

`POST /api/v1/anmeldung/` mit JSON `{ "username": "...", "password": "..." }`
liefert bei gueltigen Zugangsdaten einen zeitlich begrenzten, signierten Token
(kein serverseitiger Speicher noetig). Fehlversuche sind ueber django-axes
begrenzt (`429` bei Sperre).

```json
{ "token": "…", "expires_in": 43200, "has_membership": true,
  "station": "Rettungswache", "role": "member" }
```

Folgeaufrufe senden `Authorization: Bearer <token>`. Native Apps benoetigen so
weder Cookies noch CSRF. Einzelne Tokens sind vor Ablauf nicht widerrufbar; ein
echter Token-Speicher folgt in Roadmap-Phase M2.

## Fehlerformat

Fehler antworten mit passendem HTTP-Status und `{ "error": "..." }`:

- `400` - fehlerhafter Koerper (nur Login)
- `401` - nicht angemeldet oder Anmeldung fehlgeschlagen
- `403` - keine aktive Wachenmitgliedschaft oder Rolle nicht freigegeben
- `404` - Objekt nicht gefunden oder Modul nicht aktiviert
- `405` - Methode nicht erlaubt
- `429` - zu viele Fehlversuche (Login)

## GET /api/v1/status/

Auth-optional. Erlaubt dem Client, Server- und Anmeldezustand zu pruefen, ohne
eine Mitgliedschaft zu benoetigen.

```json
{
  "api_version": "1.0",
  "authenticated": true,
  "has_membership": true,
  "station": "Rettungswache",
  "role": "member"
}
```

`station` und `role` fehlen, wenn keine aktive Mitgliedschaft besteht.

## GET /api/v1/uebersicht/

Erfordert eine aktive Mitgliedschaft mit Inhaltsrolle (Mitglied, Schichtleitung,
Kassenwart oder Admin). Auditoren erhalten `403`. Liefert die Dashboard-Zusammen-
fassung der eigenen Wache.

```json
{
  "station": { "name": "Rettungswache", "slug": "rettungswache" },
  "role": "member",
  "role_label": "Mitglied",
  "modules": { "calendar": true, "birthdays": true, "coffee": true, "feeds": false },
  "handovers": {
    "open_count": 2,
    "urgent_count": 1,
    "items": [
      {
        "id": 12,
        "title": "Tor pruefen",
        "category": "station",
        "category_label": "Wache",
        "priority": "urgent",
        "priority_label": "Dringend",
        "status": "open",
        "status_label": "Offen",
        "updated_at": "2026-07-31T14:10:00+00:00"
      }
    ]
  },
  "events": [
    { "id": 3, "title": "Geraetepruefung", "starts_at": "...", "ends_at": "..." }
  ],
  "coffee": { "own_balance_euros": 5.0, "can_book": false }
}
```

Hinweise:

- `events` erscheint nur bei aktiviertem Kalendermodul (bis zu drei kommende
  Termine).
- `coffee` erscheint nur bei aktivierter Kaffeekasse. `total_balance_euros` wird
  ausschliesslich fuer buchungsberechtigte Rollen (Kassenwart, Admin) ergaenzt;
  Mitglieder sehen nur ihren eigenen Stand.
- Alle Werte sind auf die Wache der aufrufenden Mitgliedschaft beschraenkt.

## GET /api/v1/uebergaben/

Paginierte Uebergabeliste. Query `ansicht=aktiv` (Standard, nach Dringlichkeit
sortiert), `dringend` oder `archiv`; Seite ueber `seite`.

```json
{
  "scope": "aktiv",
  "count": 2,
  "page": 1,
  "num_pages": 1,
  "results": [ { "id": 12, "title": "Tor pruefen", "priority": "urgent",
                 "priority_label": "Dringend", "status": "open", ... } ]
}
```

## GET /api/v1/uebergaben/&lt;id&gt;/

Detail einer Uebergabe der eigenen Wache (`404` bei fremder Wache). Enthaelt
zusaetzlich `details`, `author`, `version`, Zeitstempel und die
Revisionsuebersicht (`version`, `changed_by`, `created_at`).

## GET /api/v1/kalender/

Nur bei aktiviertem Kalendermodul (sonst `404`). Paginierte kommende Termine mit
`title`, `description`, `starts_at`, `ends_at`, `created_by`.

## GET /api/v1/kaffeekasse/

Nur bei aktivierter Kaffeekasse (sonst `404`). Enthaelt `balances` (wie oben) und
paginierte Buchungen. Mitglieder sehen nur ihre eigenen Buchungen, Kassenwart und
Admin die gesamte Kasse. Buchungen enthalten `member`, `amount_euros`, `reason`,
`created_at` und `is_correction`.

## Schreibende Endpunkte

Schreibpfade akzeptieren **ausschliesslich** die Bearer-Token-Anmeldung (kein
Session-Cookie). Da keine Cookie-Autoritaet genutzt wird, sind sie ohne
CSRF-Token sicher; Session-Nutzer schreiben weiterhin ueber die Weboberflaeche.
Ungueltige Eingaben antworten mit `422` und `{ "error": ..., "fields": {...} }`.
Jede Aenderung erzeugt ein Audit-Ereignis; Uebergaben werden versioniert.

### POST /api/v1/uebergaben/

Legt eine Uebergabe an (Inhaltsrollen: Mitglied, Schichtleitung, Kassenwart,
Admin). Body `{ "category", "priority", "title", "details" }`. Antwort `201` mit
dem Detailobjekt (inkl. erster Revision).

### POST /api/v1/uebergaben/&lt;id&gt;/status/

Aendert den Status einer Uebergabe der eigenen Wache (nur Schichtleitung oder
Admin). Body `{ "status": "open" | "in_progress" | "done" }`. Erhoeht die Version
und schreibt eine Revision. Antwort `200` mit der aktualisierten Zusammenfassung.

### POST /api/v1/kaffeekasse/

Bucht in die Kaffeekasse (nur Kassenwart oder Admin, Modul aktiv). Body
`{ "member", "direction": "credit"|"debit", "amount_eur", "reason" }`. Antwort
`201` mit der neuen Buchung. Buchungen sind append-only und unveraenderlich;
Korrekturen erfolgen als Gegenbuchung ueber die Weboberflaeche.
