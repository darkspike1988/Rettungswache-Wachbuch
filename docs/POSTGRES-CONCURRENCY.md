# Research R1 — PostgreSQL-Konkurrenznachweis

## Zweck und Grenze

Die schnelle SQLite-Suite beweist keine PostgreSQL-Zeilensperren. R1 ergänzt
reproduzierbare Tests des vorhandenen Quittierungs-/Revisionsvertrags, ohne
Produktcode, Datenmodell oder öffentliche Demo zu verändern.

Der Schnitt wird gegen `develop/wachbuch-modernisierung` geprüft, nicht gegen
`main` ausgerollt. Keine Migration, Storeveröffentlichung oder Produktionsfreigabe.
AGY/Gemini lieferte einen Ausgangsentwurf; Parentprüfung und Mistral-Gegenreview
führten zu einem gehärteten, unabhängig ausgeführten Testharness. Claude war
wegen erschöpfter Quote nicht beteiligt. Modellbewertungen ersetzen keine Tests.

## Testfälle

`core/test_r1_postgres_concurrency.py` enthält acht TransactionTestCase-Tests:

- gleiche Quittierung parallel: eine Quittungszeile, ein Audit, gleiche ID und
  genau einmal `created=True`;
- Inhaltsänderung/Quittierung in beiden kontrollierten Reihenfolgen;
- echtes Inhaltsänderung/Quittierung-Rennen: Erfolg oder definierter
  Versionskonflikt, Quittung und Audit exakt zum Resultat passend;
- fremde Wache darf keine Quittierung erzeugen;
- echte Zeilensperre: NOWAIT muss PostgreSQL-SQLSTATE `55P03` liefern;
- zwei Inhaltsänderungen: beide Revisionen und Audits bleiben erhalten;
- zwei Statusänderungen: beide Revisionen und Audits bleiben erhalten;
- zwei Nutzer quittieren dieselbe Revision unabhängig.

Eigene PostgreSQL-Backend-PIDs werden geprüft. Barrier/Event statt Schlafen zur
Rennsteuerung; Event-Timeouts, Threads, SQL-Sperrzeit und Verbindungsaufbau sind
begrenzt. Kein allgemeiner Schreibcache oder automatischer Konflikt-Retry.

`config/r1_test_runner.py` verweigert SQLite, leere Evidenzsuiten und übersprungene
Pflichttests. Vier isolierte Unit-Tests prüfen diesen Guard, nicht PostgreSQL.
Die normale SQLite-Suite überspringt die acht PostgreSQL-Fälle ausdrücklich.
Das ist kein Konkurrenznachweis, sondern hält die beiden Prüfpfade getrennt.

## Lokaler isolierter Lauf

Python 3.13, hashgeprüfte `requirements.lock` und `requirements-ci.lock` verwenden.
Die lokale QA darf weder eine vorhandene Datenbank noch die Demo verwenden.

```bash
uv venv --python 3.13 .venv-r1
uv pip install --python .venv-r1/bin/python --require-hashes \
  -r requirements.lock -r requirements-ci.lock
R1_PYTHON="$PWD/.venv-r1/bin/python" bash scripts/r1-postgres-runner.sh --noinput
R1_PYTHON="$PWD/.venv-r1/bin/python" bash scripts/r1-postgres-runner.sh \
  core.test_r1_postgres_concurrency core.test_handover_ack_revision \
  core.test_handover_ack_s2_verify core.test_handover_ack_parent \
  --noinput --verbosity=2
```

Der Runner benötigt Docker und das lokal vorhandene digest-gepinnte
PostgreSQL-17.10-Image. Er zieht keine Images automatisch. Der Standardbetrieb
ist für eine Docker-basierte Entwicklungsshell ausgelegt: die eigene PG-Instanz
teilt deren Netzwerk-Namespace und lauscht nur auf Loopback mit zufälligem Port.
`R1_NETNS_CONTAINER` muss gegebenenfalls die eigene Entwicklungsshell bezeichnen.
Keinen Produktivcontainer als Netz-Namespace auswählen.

Der Runner erzeugt nur eigene flüchtige Ressourcen, begrenzt CPU/RAM und entfernt
seinen eigenen Container im Exit-Trap. Die Containerbereitschaft wird separat
geprüft; dortiges Polling ist keine Rennsteuerung der fachlichen Tests.

Die Settings verlangen `R1_DISPOSABLE_DB=1` und Loopback. Diese Schutzbedingungen
sind keine Autorisierungsbarriere gegen absichtlichen Missbrauch; ausschließlich
neu erzeugte Testinstanzen verwenden. SQL-/Locktimeout 10/8 Sekunden,
Connecttimeout 5 Sekunden. Keine echten Secrets oder Produktivdaten übernehmen.

## CI

Der Job `postgres-concurrency` in `.github/workflows/ci.yml` erzeugt eine eigene
PostgreSQL-Serviceinstanz mit digest-gepinntem Image, zufälligem Port und
öffentlichem, ausschließlich für diesen flüchtigen Testdienst gedachten Passwort.
Keine gespeicherten Produktions-Credentials. Der Job installiert dieselben
hashgeprüften Abhängigkeiten, führt Konkurrenz- und Vertragstests aus und
wiederholt das Konkurrenzmodul zweimal. Timeout: zehn Minuten.

Der Job erweitert die vorhandene PR-CI. Der lokale Runner ist kein Ersatz für
diesen Remote-Nachweis und setzt dessen GitHub-Kontext nicht voraus.

## Lokale Parent-Abnahme

- Python 3.13.5 / Django 6.1 / psycopg 3.3.4 / PostgreSQL 17.10.
- 34 PostgreSQL-Tests (8 Konkurrenz + 26 Vertrags-/Web-/APItests): OK ohne Skips.
- Zwei zusätzliche Durchläufe mit jeweils 8 Konkurrenztests: OK ohne Skips.
- SQLite-Gesamtsuite: 360 Tests, OK (9 Skips: 8 PG-Fälle und 1 bestehender Skip).
- Ruff-Baseline, Migrationcheck, Django-Check, Python-Compile, Bashsyntax,
  Actionlint und Git-Diffprüfung bestanden.
- Zusätzliche isolierte Mutation-Negativkontrolle: per Mock wird
  `QuerySet.select_for_update` deaktiviert. Der NOWAIT-Test wird erwartungsgemäß
  rot (`OperationalError not raised`, ein Failure). Die normale positive Suite
  besteht danach erneut. Kein produktiver Code wird dafür verändert.

Die Mutationprobe bleibt außerhalb des Repository-Testbaums. Sie ist ein
Beleg der Nachweiskraft dieses Tests, keine zu ignorierende rote Produkt-CI.

## Verbleibende Grenzen

- Gleichzeitige HTTP-Requests und Produktionsrollen/DB-Privilegien sind nicht
  gleichbedeutend mit den hier geprüften Service-Rennen. Das Bundle prüft den
  HTTP-Vertrag, nicht parallel ausgelieferte HTTP-Requests.
- Zwei Threads plus Wiederholungen ersetzen weder Last-/Chaos- noch lange
  Zuverlässigkeitstests. Aussage gilt für die ausgeführten Szenarien/Versionen.
- Lokaler Mock-Negativtest ist kein vollständiger Mutationstest aller Services.
- Keine Geräte-, Nutzer-, Screenreader-, Backup-/Restore- oder Rolloutabnahme.
