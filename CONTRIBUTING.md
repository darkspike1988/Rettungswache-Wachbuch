# Mitwirken am Rettungswache-Wachbuch

*Letzte Aktualisierung: August 2026 | Version: 0.15.0*

---

**Danke für dein Interesse am Rettungswache-Wachbuch!** 🎉

Beiträge sind **herzlich willkommen** – egal ob du Code beisteuern, Dokumentation verbessern, Bugs melden oder Feature-Ideen einbringen möchtest. Dieser Guide hilft dir, den besten Weg zu finden, um mitzuwirken.

---

## 📋 **Inhaltsverzeichnis**

1. [Wie du helfen kannst](#-wie-du-helfen-kannst)
2. [Vor dem Start](#-vor-dem-start)
3. [Entwicklungsumgebung einrichten](#-entwicklungsumgebung-einrichten)
4. [Code-Standards](#-code-standards)
5. [Pull Request Prozess](#-pull-request-prozess)
6. [Code Review](#-code-review)
7. [Sicherheitsmeldungen](#-sicherheitsmeldungen)
8. [Lizenz](#-lizenz)

---

## 🤝 **Wie du helfen kannst**

### **🐛 Bugs melden**

- **Issue erstellen**: [GitHub Issues](https://github.com/darkspike1988/Rettungswache-Wachbuch/issues/new/choose)
- **Vorlage verwenden**: Nutze die Bug-Report-Vorlage
- **Reproduktionsschritte**: Klare Anleitung, wie der Bug ausgelöst wird
- **Umgebung**: Server-Version, Browser, Betriebssystem
- **Logs**: Relevante Log-Auszüge (ohne sensible Daten!)

### **💡 Feature-Ideen einreichen**

- **Issue erstellen**: [Feature Request](https://github.com/darkspike1988/Rettungswache-Wachbuch/issues/new?template=feature_request.md)
- **Use Case beschreiben**: Welches Problem löst das Feature?
- **Akzeptanzkriterien**: Was muss das Feature können?
- **Alternativen**: Gibt es andere Lösungen?

### **📝 Dokumentation verbessern**

- **Typos korrigieren**: Pull Request mit Fixes
- **Anleitungen ergänzen**: Fehlende Schritte hinzufügen
- **Übersetzungen**: Dokumentation in andere Sprachen übersetzen
- **Beispiele hinzufügen**: Code-Snippets, Screenshots

### **💻 Code beisteuern**

- **Issues kommentieren**: Vor dem Entwickeln ein Issue auswählen
- **Fork erstellen**: Eigene Kopie des Repositories
- **Branch erstellen**: `feature/xxx` oder `fix/xxx`
- **Pull Request**: Mit klarer Beschreibung und Tests

### **🔍 Code Review**

- **Pull Requests kommentieren**: Konstruktives Feedback geben
- **Tests prüfen**: Funktionieren die Änderungen wie erwartet?
- **Sicherheit prüfen**: Gibt es potenzielle Sicherheitslücken?

### **📢 Community unterstützen**

- **Fragen beantworten**: In [Discussions](https://github.com/darkspike1988/Rettungswache-Wachbuch/discussions)
- **Anfänger helfen**: Bei den ersten Schritten unterstützen
- **Erfahrungen teilen**: Wie du das Projekt einsetzt

---

## 🚀 **Vor dem Start**

### **1. Projekt verstehen**

- **README lesen**: [README.md](README.md)
- **Architektur kennenlernen**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API verstehen**: [docs/API.md](docs/API.md)
- **Sicherheitskonzept**: [docs/SECURITY-PRIVACY.md](docs/SECURITY-PRIVACY.md)

### **2. Issue auswählen oder erstellen**

- **Existing Issues**: [GitHub Issues](https://github.com/darkspike1988/Rettungswache-Wachbuch/issues)
- **Labels prüfen**: `good first issue`, `help wanted`, `bug`, `enhancement`
- **Priorität**: Issues mit `P0`, `P1`, `P2` haben höhere Priorität

### **3. Issue zuweisen lassen**

- **Kommentieren**: "Ich arbeite daran"
- **Warten auf Bestätigung**: Maintainer weisen das Issue zu
- **Fragen klären**: Bei Unklarheiten nachfragen

---

## 🛠️ **Entwicklungsumgebung einrichten**

### **Server (Django/PostgreSQL)**

#### **Voraussetzungen**

- Docker Engine (mit Compose v2)
- Docker Compose
- Git
- Texteditor (VS Code, PyCharm, etc.)

#### **Schritt-für-Schritt**

```bash
# 1. Repository klonen
git clone https://github.com/darkspike1988/Rettungswache-Wachbuch.git
cd Rettungswache-Wachbuch

# 2. Branch erstellen (z.B. für ein Feature)
git checkout -b feature/mein-feature

# 3. Umgebungsvariablen vorbereiten
cp .env.example .env

# 4. Zufällige Geheimnisse generieren (für alle PLATZHALTER in .env)
openssl rand -hex 32  # Für DJANGO_SECRET_KEY
openssl rand -hex 32  # Für DB_PASSWORD
openssl rand -hex 32  # Für POSTGRES_PASSWORD
# ... (alle PLATZHALTER in .env ersetzen)

# 5. Backup-Verzeichnis vorbereiten
sudo chown 70:70 backups

# 6. Container starten
docker compose up --build -d

# 7. Datenbank migrieren
docker compose exec web python manage.py migrate

# 8. Admin-Benutzer erstellen
docker compose exec web python manage.py createsuperuser

# 9. Admin als Stations-Admin festlegen
docker compose exec web python manage.py grant_station_admin BENUTZERNAME

# 10. Server testen
curl http://127.0.0.1:8090/healthz/
```

#### **Nützliche Befehle**

```bash
# Logs anzeigen
docker compose logs -f web

# Datenbank-Shell
docker compose exec db psql -U rwsth_owner -d rwsth

# Django-Shell
docker compose exec web python manage.py shell

# Tests ausführen
docker compose exec web python manage.py test --settings=config.test_settings

# Linting
pip install pre-commit
pre-commit run --all-files

# Container stoppen
docker compose down
```

### **Client (Flutter)**

#### **Voraussetzungen**

- [Flutter SDK](https://flutter.dev/docs/get-started/install) (Stable Channel)
- [Android Studio](https://developer.android.com/studio) (für Android)
- [Xcode](https://developer.apple.com/xcode/) (für iOS, nur macOS)
- Java 17+ (für Android-Builds)

#### **Schritt-für-Schritt**

```bash
# 1. Repository klonen
git clone https://github.com/darkspike1988/Wachbuch-Client.git
cd Wachbuch-Client

# 2. Branch erstellen
git checkout -b feature/mein-feature

# 3. Abhängigkeiten installieren
flutter pub get

# 4. Code-Qualität prüfen
flutter analyze

# 5. Tests ausführen
flutter test

# 6. App starten (für Entwicklung)
flutter run
```

#### **Nützliche Befehle**

```bash
# Geräte auflisten
flutter devices

# App auf spezifischem Gerät starten
flutter run -d <device-id>

# Build für Android
flutter build apk --release --flavor internal

# Build für iOS (Simulator)
flutter build ios --simulator --debug

# Abhängigkeiten aktualisieren
flutter pub upgrade

# Code formatieren
dart format .
```

---

## 📜 **Code-Standards**

### **Python (Server)**

#### **Formatierung**

- **Black**: Code-Formatierung
  ```bash
  black config core
  ```
- **isort**: Import-Sortierung
  ```bash
  isort config core
  ```

#### **Linting**

- **flake8**: PEP 8 Compliance
  ```bash
  flake8 config core
  ```
- **Konfiguration**: Siehe `.pre-commit-config.yaml`

#### **Type Hints**

- **Pflicht**: Alle öffentlichen Funktionen müssen Type Hints haben
- **Empfohlen**: Auch für private Funktionen
- **Beispiel**:
  ```python
  def get_handover(handover_id: int, request: HttpRequest) -> HttpResponse:
      ...
  ```

#### **Dokumentation**

- **Docstrings**: Für alle öffentlichen Funktionen und Klassen
- **Format**: Google-Style Docstrings
- **Beispiel**:
  ```python
  def calculate_coffee_balance(user: User) -> int:
      """Calculate the current coffee balance for a user.
      
      Args:
          user: The user to calculate the balance for.
          
      Returns:
          The current balance in cents.
      """
      ...
  ```

### **Dart (Client)**

#### **Formatierung**

- **dart format**: Automatische Formatierung
  ```bash
  dart format .
  ```

#### **Linting**

- **flutter_lints**: Standard-Lint-Regeln
- **very_good_analysis**: Strengere Regeln
- **Konfiguration**: Siehe `analysis_options.yaml`

#### **Type Safety**

- **Vermeide `dynamic`**: Immer spezifische Typen verwenden
- **Null Safety**: `?` für nullable Typen
- **Final Variables**: `final` für unveränderliche Variablen

#### **Dokumentation**

- **Doc Comments**: Für alle öffentlichen Mitglieder
- **Format**: Dartdoc-Format
- **Beispiel**:
  ```dart
  /// Fetches the list of handovers from the server.
  ///
  /// Returns a [List] of [Handover] objects.
  /// Throws [ApiException] if the request fails.
  Future<List<Handover>> fetchHandovers() async {
    ...
  }
  ```

---

## 🔄 **Pull Request Prozess**

### **1. Vor dem Commit**

- [ ] **Code formatieren**: `black`, `isort`, `dart format`
- [ ] **Linting prüfen**: `flake8`, `flutter analyze`
- [ ] **Tests ausführen**: `python manage.py test`, `flutter test`
- [ ] **Dokumentation aktualisieren** (falls nötig)
- [ ] **Changelog aktualisieren** (falls nötig)

### **2. Commit-Nachricht**

Verwende **[Conventional Commits](https://www.conventionalcommits.org/)**:

```text
<type>([<scope>]): <description>

[body]

[footer]
```

**Beispiele:**

```bash
# Feature
git commit -m "feat(api): add handover status endpoint"

# Bugfix
git commit -m "fix(models): prevent duplicate coffee entries"

# Dokumentation
git commit -m "docs: update README with installation instructions"

# Refactoring
git commit -m "refactor(views): extract handover logic into service"

# Chore (Maintenance)
git commit -m "chore: update dependencies"
```

**Typen:**
- `feat`: Neue Funktion
- `fix`: Bugfix
- `docs`: Dokumentationsänderung
- `style`: Formatierung, fehlende Semikolons
- `refactor`: Code-Refactoring (keine Funktionsänderung)
- `perf`: Performance-Verbesserung
- `test`: Tests hinzufügen/korrigieren
- `chore`: Maintenance (Dependencies, Build-Konfiguration)
- `revert`: Revert eines Commits

### **3. Pull Request erstellen**

1. **Branch pushen**:
   ```bash
   git push origin feature/mein-feature
   ```

2. **Pull Request erstellen**: [GitHub PR](https://github.com/darkspike1988/Rettungswache-Wachbuch/compare)

3. **Vorlage ausfüllen**:
   - **Titel**: Klar und präzise
   - **Beschreibung**: Was ändert sich? Warum?
   - **Verknüpftes Issue**: `#123` (automatisches Closing mit `Closes #123`)
   - **Screenshots**: Bei UI-Änderungen
   - **Checkliste**: Alle Punkte abhaken

### **4. CI prüfen**

- **GitHub Actions**: Alle Checks müssen grün sein
- **Tests**: Alle Tests müssen durchlaufen
- **Linting**: Keine Lint-Fehler
- **Build**: Docker-Build muss erfolgreich sein

---

## 👀 **Code Review**

### **Was Reviewer prüfen**

1. **Funktionalität**: Macht der Code das, was er soll?
2. **Sicherheit**: Gibt es potenzielle Sicherheitslücken?
3. **Performance**: Gibt es Performance-Probleme?
4. **Code-Qualität**: Ist der Code lesbar und wartbar?
5. **Tests**: Sind die Änderungen ausreichend getestet?
6. **Dokumentation**: Ist die Dokumentation aktualisiert?

### **Feedback geben**

- **Konstruktiv**: "Könnten wir das so machen, weil..." statt "Das ist falsch"
- **Spezifisch**: Konkrete Vorschläge machen
- **Begründet**: Warum ist die Änderung nötig?
- **Freundlich**: Respektvoller Ton

### **Auf Feedback reagieren**

- **Dankbar sein**: "Danke für das Feedback!"
- **Fragen klären**: Bei Unklarheiten nachfragen
- **Änderungen vornehmen**: Feedback umsetzen oder begründen
- **Neu commiten**: Änderungen als neuen Commit pushen

---

## 🔒 **Sicherheitsmeldungen**

⚠️ **WICHTIG**: Sicherheitslücken **nicht** in öffentlichen Issues oder Pull Requests melden!

### **Verantwortliche Offenlegung**

1. **E-Mail**: Sende eine E-Mail an die Maintainer
2. **GitHub Security Advisory**: Erstelle einen [Security Advisory](https://github.com/darkspike1988/Rettungswache-Wachbuch/security/advisories/new)
3. **Warten**: Gib dem Team Zeit zur Reaktion (mind. 72 Stunden)

### **Was als Sicherheitslücke gilt**

- **SQL Injection**
- **XSS (Cross-Site Scripting)**
- **CSRF (Cross-Site Request Forgery)**
- **Authentifizierungsumgehung**
- **Datenlecks** (sensible Daten in Logs, etc.)
- **Denial of Service**
- **Privilege Escalation**

### **Was NICHT als Sicherheitslücke gilt**

- **Feature Requests**
- **Bugs ohne Sicherheitsauswirkung**
- **Performance-Probleme**
- **UI/UX-Verbesserungen**

---

## 📄 **Lizenz**

Alle Beiträge unterliegen der **GNU Affero General Public License v3.0 oder später**.

### **Was das bedeutet**

- **Du behältst das Copyright** an deinem Code
- **Du gewährst eine Lizenz** für die Nutzung unter AGPL
- **Änderungen müssen offen** sein, wenn sie als Netzwerkdienst betrieben werden

### **DCA (Developer Certificate of Origin)**

Durch das Einreichen von Code bestätigst du:

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

### **Sign-Off**

Füge am Ende deiner Commit-Nachricht hinzu:

```bash
git commit -m "feat: add new feature" -s
```

Dies fügt automatisch deinen Sign-Off hinzu:
```text
Signed-off-by: Dein Name <deine@email.com>
```

---

## 🙏 **Danke!**

Vielen Dank, dass du zum Rettungswache-Wachbuch beiträgst! 🎉

Deine Beiträge helfen, das Projekt besser zu machen und Rettungswachen bei ihrer wichtigen Arbeit zu unterstützen.

---

*Letzte Aktualisierung: August 2026 | [GitHub](https://github.com/darkspike1988/Rettungswache-Wachbuch)*