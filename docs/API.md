# JSON-API (v1)

Schmale, ausschliesslich lesende JSON-Schnittstelle fuer den mobilen Client
(`Wachbuch-Client`). Sie spiegelt die stationsbezogenen Zugriffsregeln der
Weboberflaeche und gibt nur Daten zurueck, die die angemeldete Person ohnehin im
Interface sehen darf. Es gibt keine Schreibpfade und keine Patienten-,
Gesundheits- oder Einsatzdaten.

Basis-Pfad: `/api/v1/`. Authentifizierung ueber die bestehende Django-Session
(Login unter `/anmelden/`). Alle Endpunkte akzeptieren nur `GET`.

## Fehlerformat

Fehler antworten mit passendem HTTP-Status und `{ "error": "..." }`:

- `401` - nicht angemeldet
- `403` - keine aktive Wachenmitgliedschaft oder Rolle nicht freigegeben
- `405` - Methode nicht erlaubt (nur `GET`)

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
