# Wachbuch Client – historischer Server-Spiegel

> **Quelle der Wahrheit ist ausschließlich**
> https://github.com/darkspike1988/Wachbuch-Client
>
> Dieser Ordner ist ein historischer Entwicklungs-Spiegel. Er darf nicht zurück
> in das Standalone-Repository publiziert werden und kann hinter dem aktuellen
> Mobile-Client zurückliegen.

Der produktive Flutter-Client für iOS und Android wird im eigenständigen
`Wachbuch-Client`-Repository entwickelt, getestet und veröffentlicht. Server und
Client koppeln sich über den versionierten `/api/v1/`-Vertrag, nicht über einen
Datei-Mirror.

## Aktuelles Versionspaar

| Server | Client | Vertrag |
| --- | --- | --- |
| 0.16.x | 0.6.x | Realer Wachalltag: Mängel, Assets, Schlüssel/Pools, Übergabe-Quittierung, wiederkehrende Checklisten, authentifizierte Mängelfotos, Reports und Offline-Lesen |
| 0.15.x | 0.5.1+ | vorheriger Kernvertrag |
| 0.14.1 | 0.5.0+ | API v1, App-Tokens, MFA |

## Entwicklungsregel

1. Mobile-Änderungen direkt in `darkspike1988/Wachbuch-Client` umsetzen.
2. Dort `flutter analyze`, `flutter test`, Android-, iOS- und Security-CI bestehen lassen.
3. Serveränderungen gegen den dokumentierten API-Vertrag testen.
4. Diesen Spiegel niemals als neueren Clientstand behandeln.

Das frühere Skript `scripts/publish-mobile-client-repo.sh`, das diesen Ordner mit
`force-with-lease` auf das Standalone-Repository schreiben konnte, ist aus
Sicherheitsgründen deaktiviert. Damit kann ein veralteter Mirror keine neueren
Client-Commits mehr überschreiben.

## Produktgrenze

Der Mobile-Client unterstützt den Wachalltag einer Wache. Patienten-, Einsatz-,
Alarmierungs-, ePCR-, Personalakten- und vergleichbare sensible Fachdaten sind
nicht Teil dieses Vertrages.

## Rechtliches

AGPL-3.0-or-later – siehe `LICENSE` im kanonischen Client-Repository.
