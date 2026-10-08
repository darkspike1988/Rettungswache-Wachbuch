# Roadmap Server ↔ Client (Oktober 2026)

Stand: 2026-10-08. Erstellt nach der Modernisierungs-Research und dem unabhängigen
Large-4-Review. Dieser Plan ersetzt **nicht** `PRODUKT-FAHRPLAN.md` und
`REMEDIATION-ROADMAP-2026-08.md`, sondern ordnet die nächsten Arbeitsschritte
und verteilt sie auf die verfügbaren Coding-Agenten.

## 0. Verifizierter Ausgangsstand

| Gegenstand | Belegter Stand |
| --- | --- |
| Server-Repo | `darkspike1988/Rettungswache-Wachbuch`, Django 6.1, PostgreSQL, gunicorn |
| Server-Version | `core/version.py` → `APP_VERSION = "0.16.0"` |
| Öffentliche Demo | Branch `demo/wachleitung`, Commit `de6324b`, eingefroren, läuft (`local/wachbuch-public-demo:0.16.0`, healthy) |
| Modernisierung | Branch `develop/wachbuch-modernisierung`, Commit `49d2d4f` (MFA-Enforcement, R-021) |
| Schichtüberblick | Branch `feature/wachbuch-schichtueberblick`, Commit `2814788` (R-025) |
| Client-Repo | `darkspike1988/Wachbuch-Client`, Flutter, AGPL-3.0 |
| Client-Version | `pubspec.yaml` → `version: 1.0.0+12`, HEAD `2e044b93` (2026-08-20) |
| API-Vertrag | `/api/v1/`, OpenAPI **1.2.2** (`core/api/openapi_v1.yaml`) |
| Client-Tests | 55 Testdateien unter `test/` |

### 0.1 Belegte Abweichungen (vor der Planung zu klären)

1. **Client-Version ist veraltet dokumentiert.** Server-`docs/CLIENT.md` und
   Client-`docs/E2E-WACHALLTAG.md` sprechen von Client `0.6.x`. Tatsächlich
   steht der Client auf `1.0.0+12`. Die Versionspaarungstabelle ist zu
   korrigieren.
2. **OpenAPI-Vertrag ist unvollständig.** In `core/api/urls.py` implementiert,
   aber in OpenAPI 1.2.2 **nicht dokumentiert**:
   `chat/identity/`, `chat/keys/`, `chat/`, `chat/private/`,
   `chat/private/{id}/`, `post/`, `post/{id}/`, `chat/groups/`,
   `chat/groups/{id}/`, `chat/groups/{id}/members/`, `pinnwand/`.
   Der Client ruft diese Endpunkte bereits auf (`lib/api/client.dart`).
   Der veröffentlichte Vertrag hinkt der Implementierung nach.
3. **Phase-3-Merge-Status ist irreführend.** Server-PR #66 und #67 sowie
   Client-PR #44, #45 sind **gemergt**. Server-PR #68 und Client-PR #46
   (Chatgruppen) sind **geschlossen, nicht gemergt** – die Server-Modelle,
   Migration `0025_chatgroup_groupmessage_chatgroupmember.py`, die Endpunkte
   und `core/test_chat_groups_api.py` sind trotzdem im Branch vorhanden.
   Offen ist die Frage, über welchen Weg das landed und ob die Client-Gruppen-UI
   (`lib/screens/groups_screen.dart`) gegen den aktuellen Server getestet ist.
4. **Secure-Mail-Screens fehlen im Client.** Der Server hat `/api/v1/post/`, der
   Client hat die API-Methoden, aber keine Screens für Postfach/Thread.

## 1. Server-Roadmap

Reihenfolge nach Risiko und Nutzen. Jeder Schritt bleibt ein kleiner,
getesteter vertikaler Schnitt mit eigener Roadmap-ID.

### S1 – Vertrag nachziehen (Dokumentation, kein Feature)
- OpenAPI auf die real implementierten Endpunkte erweitern (Chat, Gruppen,
  Post, Pinnwand), Version auf `1.3.0` heben.
- `docs/API.md` und `docs/CLIENT.md` an `1.0.0+12` angleichen.
- Vertragstests, die die im Spec dokumentierten Pfade gegen `core/api/urls.py`
  prüfen, damit die Drift nicht zurückkommt.
- **Risiko:** keins (nur Doku + Test). **Nutzen:** hoch, Voraussetzung für alle
  weiteren Clientarbeiten.

### S2 – Quittierung im Web (`HandoverAck`)
- P0 aus der Research. Modell existiert bereits in
  `core/wachalltag_models.py`; API `/handovers/{id}/ack/` existiert.
- Fehlt: Web-POST-View, UI („Zur Kenntnis genommen“), Audit-Eintrag.
- **Wichtige Einschränkung aus der Vorprüfung:** Das bestehende Modell
  unterscheidet nicht, **welche Version** einer Übergabe quittiert wurde.
  Vor der Implementierung muss fachlich geklärt werden, ob eine Quittierung
  bei nachträglicher Änderung der Übergabe ungültig wird. Ohne diese Klärung
  keine Umsetzung.

### S3 – Restpunkte aus der laufenden Remediation
Offen laut `docs/ROADMAP.md`:
- Least-Privilege-Backuprolle
- gemeinsames Rate Limiting hinter explizit vertrautem Proxy
- externe ASVS-, Penetrations-, Last-, Restore- und Accessibility-Abnahme

### S4 – Vertragshärtung
- Der Review-Befund zur Rate-Limit-Umgehung wurde **nicht bestätigt** und ist
  nicht zu übernehmen.
- Die Axes-Absenkung (15 statt 60 Minuten) aus dem Modellvorschlag ist
  **abzulehnen** – sie würde den Brute-Force-Schutz verkürzen.
- Stattdessen: Proxy-/Client-IP-Kette endpunktbezogen prüfen (Hetzner-Baustelle
  w2 aus dem Sicherheitsauftrag).

### S5 – Produktfunktonen aus `PRODUKT-FAHRPLAN.md`
- Phase 4: Prüf-/Wartungsfristen, QR-Gerätekarten, Erinnerungen
- Phase 5: Qualifikations-/Tauglichkeitsverwaltung
- Phase 6: Karten (lokal gebündelt, CSP-konform)
- Phase 7: Homogenisierung Server ↔ Client

## 2. Client-Roadmap (Flutter)

- **C1 – Vertrag nachziehen:** Client gegen OpenAPI 1.3.0 abgleichen, Drift in
  `lib/api/client.dart` und `test/api_contract_regression_test.dart` feststellen.
- **C2 – Secure-Mail-Screens:** `post/`-Endpunkt nutzen, Postfach + Thread,
  E2EE wie im Web, Demo-Parität, l10n de/en.
- **C3 – Chatgruppen abnehmen:** `groups_screen.dart` gegen den tatsächlichen
  Server-Endpunkt prüfen; bei Nichtdeckung nachziehen oder UI zurücknehmen.
- **C4 – Version und Doku:** `docs/E2E-WACHALLTAG.md`, `docs/SERVER.md`,
  `ROADMAP.md` auf `1.0.x` und den echten API-Stand bringen.
- **C5 – QR-Gerätekarte:** `mobile_scanner` ist vorhanden, `qr_scan_screen.dart`
  existiert; Anbindung an die geplante Serverfunktion (Phase 4).

## 3. Kritischer Pfad

```
S1 (Vertrag) ──┬─► C1 (Client-Abgleich)
               ├─► C2 (Secure Mail)
               └─► C3 (Gruppen-Abnahme)
S2 (Quittierung, nach fachlicher Klärung) ──► C3/C4
S5 Phase 4 (Fristen + QR) ──► C5
S3/S4 (Betrieb & Sicherheit) laufen unabhängig parallel
```

**Regel:** Kein Client-Feature gegen einen Endpunkt bauen, der nicht in der
OpenAPI-Spezifikation steht. Deshalb steht S1 vor allem anderen.

## 4. Aufgabenverteilung: AGY und Mistral

### 4.1 Gemessene Fähigkeiten (Stand 2026-10-08)

**Mistral API – live abgefragt (`/v1/models` und Antwort-Header):**

| Modell | Kontext | Reasoning | Vision | Function Calling | FIM | Gemessenes Limit |
| --- | --- | --- | --- | --- | --- | --- |
| `mistral-large-4` | 1.048.576 | ja | **ja** | ja | nein | 1.000.000 Tok./min, 2.000 Req./min |
| `mistral-medium-3-5` | 262.144 | ja | ja | ja | nein | 1.000.000 Tok./min, 2.000 Req./min |
| `zai-glm-5-3` | 1.048.576 | ja | nein | ja | nein | nicht separat gemessen |
| `codestral-latest` | 256.000 | nein | nein | ja | **ja** | 2.000.000 Tok./min, 1.000 Req./min |
| `mistral-small-latest` | 262.144 | ja | ja | ja | nein | nicht separat gemessen |

- `mistral-large-latest` zeigt weiterhin auf `mistral-large-2512`, **nicht** auf
  Large 4. Large 4 immer explizit anfordern.
- `mistral-small-latest` hat im Dateilesetest **falsche Inhalte** behauptet →
  nicht für Arbeiten mit inhaltlicher Verantwortung einsetzen.
- Praktisch abgenommen mit echtem Werkzeugaufruf: Large 4, Medium 3.5,
  GLM 5.3, Codestral.

**Mistral-Kontingent:** Tarifstufen laut Hilfe: Tier 1 = Pay-as-you-go aktiv,
Tier 2 > 20 €, Tier 3 > 100 €, Tier 4 > 500 € Abrechnung. Rate Limits sind
organisationsweit und modellbezogen. **Nicht belegt:** ob Pro/Education
API-Aufrufe abdeckt. Kontostand und Stufe stehen im Admin-Panel unter
`admin.mistral.ai/organization/usage` bzw. `plateforme/limits`.

**Vibe CLI:** Version 2.26.0 (aktuell). Eingebaute Agenten: `ask`, `plan`,
`accept-edits`, `auto-approve`, `lean`. Steuerbar über `--max-turns`,
`--max-tokens`, `--max-price`, `--enabled-tools`, `--output json`.
**Bekannte Falle:** Bilder werden headless als Binärtext gelesen statt als
Bild angehängt; für visuelle Prüfungen die API mit `image_url`-Blöcken nutzen.

**AGY:** 18 Modelle verfügbar, u. a. `gemini-3.8-flash-*`, `gemini-3.1-pro-*`,
`claude-opus-5-5-*`, `claude-sonnet-5-5-*`, `gpt-oss-120b-medium`.
Steuerbar über `--model`, `--effort`, `--mode plan|accept-edits`, `--sandbox`.
**Nicht belegt:** Ein Verbrauchs- oder Kontingentzähler. Die Subkommandoliste
(`agent`, `models`, `changelog`, `install`, `mcp`, `plugin`, `remote-control`,
`update`) enthält **keinen** Usage-Befehl. Aussagen über AGY-Restkontingente
dürfen deshalb nur über das Web-Konto getroffen werden, nicht aus der CLI
abgeleitet.

### 4.2 Zuschnitt

| Aufgabe | Agent | Modell | Begründung |
| --- | --- | --- | --- |
| S1 OpenAPI nachziehen | Mistral | `mistral-large-4` | 1 Mio. Kontext: ganze `urls.py` + Spec + `docs/API.md` in einem Lauf prüfbar |
| S1 Vertragstest schreiben | Mistral | `codestral-latest` | FIM-Stärke für kleine, präzise Testdateien |
| S2 Quittierung (nach Klärung) | AGY | `gemini-3.1-pro-high` | Modelländerung + View + Template + Audit über mehrere Dateien |
| S2 unabhängige Gegenprüfung | Mistral | `mistral-large-4` | zweite, andere Modellfamilie als Prüfinstanz |
| S3 Backuprolle / Rate Limiting | AGY | `claude-opus-5-5-high` | sicherheitskritische Infrastruktur, sorgfältiges Abwägen |
| S4 Client-IP-Kette prüfen | AGY | `gemini-3.1-pro-high` | Analyse über Server-, Proxy- und Containerkonfiguration |
| S5 Phase 4/5 Servermodell | AGY | `gemini-3.1-pro-high` | neue Modelle + Migrationen + API + Web-UI |
| C1 Client-Vertragsabgleich | Mistral | `mistral-medium-3-5` | schnelle, günstige Analyse vieler Dart-Dateien |
| C2 Secure-Mail-Screens | Mistral | `mistral-medium-3-5` | UI-Arbeit, Vision hilft bei Screenshot-Abgleich |
| C3 Gruppen-Abnahme | AGY | `gemini-3.8-flash-high` | Abgleich Client-Aufrufe ↔ Server-Endpunkte |
| C4 Doku-Angleichung | Mistral | `mistral-medium-3-5` | Textarbeit, günstig |
| C5 QR-Gerätekarte | Mistral | `mistral-medium-3-5` | Scanner ist im Client vorhanden |
| Visuelle UI-Abnahme | Mistral | `mistral-large-4` | einziges praktisch bestätigtes Vision-Modell |
| Gegenprüfung jedes Schnitts | beide | jeweils andere Familie | Modellfehler wie der widerlegte Review-Befund sollen auffallen |

**Grundregel zur Verteilung:** Ein Agent entwickelt, der andere prüft – und zwar
immer aus einer **anderen Modellfamilie**. Genau so wurde der falsche
Kaffeekassen-Befund des ersten Reviews entdeckt.

### 4.3 Kontingent schonen

- Große Kontextläufe (ganzes Repo, Screenshots) nur bei `mistral-large-4`
  und `zai-glm-5-3` – beide haben 1 Mio. Kontext, aber Large 4 ist das teurere
  Modell. Für reine Textanalyse zuerst GLM 5.3 versuchen.
- Kurze, klar umrissene Änderungen mit `mistral-medium-3-5` (günstiger, schnell).
- `codestral-latest` nur für FIM-/Autocomplete-nahe Arbeit, nicht für
  Architekturentscheidungen (kein Reasoning).
- `mistral-small-latest` für nichts Inhaltliches einsetzen.
- Jeder programmatische Lauf bekommt `--max-price`, `--max-turns`,
  `--max-tokens` als Abbruchgrenze. Beim Large-4-Review hat genau das einen
  unkontrollierten Lauf verhindert.
- AGY-Läufe immer in einem isolierten Worktree; `--dangerously-skip-permissions`
  nur dort und nur lesend, wo es der Auftrag deckt.

### 4.4 Abnahmeregeln (für beide Agenten verbindlich)

1. Kein Agent gilt als fertig, weil sein Exit-Code 0 ist. Ergebnis lesen.
2. Jede Änderung wird unabhängig nachgetestet: `makemigrations --check`,
   vollständige Suite, `git diff --check`, JS-Syntax bei Frontendarbeit.
3. Kein Client-Feature gegen einen undokumentierten Endpunkt.
4. Keine Behauptung über Deployment, Restore oder Abnahme ohne echten Beleg.
5. Die öffentliche Demo (`de6324b`) bleibt unverändert, bis ausdrücklich
   anders beauftragt.

## 5. Offene Entscheidungen

1. **Quittierung:** Bleibt eine Quittierung gültig, wenn die Übergabe danach
   geändert wird? Erst danach S2 umsetzen.
2. **Chatgruppen:** Über welchen Weg sind die Server-Modelle gelandet, wenn
   PR #68 geschlossen ist? Vor C3 klären.
3. **Mistral-Kontingent:** Aktuelle Tarifstufe und Restbudget im Admin-Panel
   prüfen, bevor größere Läufe geplant werden.
4. **Hetzner-Baustellen w1/w2/w4/w5** aus dem Sicherheitsauftrag sind weiter
   offen und unabhängig von dieser Produktroadmap.
