# Rettungswache-Wachbuch

[![CI](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml/badge.svg)](https://github.com/Darkspike1988/Rettungswache-Wachbuch/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License:AGPL_v3-blue.svg)](LICENSE)
[![Docker Image](https://img.shields.io/badge/Docker-GHCR-blue?logo=docker&logo=github)](https://github.com/Darkspike1988/Rettungswache-Wachbuch/pkgs/container/rettungswache-wachbuch)

---

## 📋 **Was ist das Rettungswache-Wachbuch?**

Das **Rettungswache-Wachbuch** ist eine **selbstgehostete, datenschutzfreundliche Webanwendung** für die **interne Organisation von Rettungswachen**. Es ermöglicht die digitale Verwaltung von Schichtübergaben, Wachenkalendern, Kaffeekassen und weiteren organisatorischen Aufgaben – **ohne Einsatzdaten, Patientendaten oder Alarmierungsinformationen** zu speichern.

### 🎯 **Zielgruppe**

- **Rettungswachen** (Feuerwehr, DRK, Malteser, etc.)
- **Wachen mit Schichtbetrieb** und Übergabeprozessen
- **Organisationen**, die eine einfache, sichere Lösung für interne Kommunikation benötigen

### ❌ **Was es NICHT ist**

- ❌ **Kein Einsatzleitsystem** (keine Einsatzdaten)
- ❌ **Kein Alarmierungssystem** (keine Alarmdaten)
- ❌ **Kein Dienstplanungssystem** (keine Dienstpläne)
- ❌ **Kein Patientendokumentationssystem** (keine Gesundheitsdaten)
- ❌ **Kein Chat-System** (nur einfache Wachenkommunikation)

---

## ✨ **Kernfunktionen**

| Funktion | Beschreibung | Modul |
|----------|--------------|-------|
| **Schichtübergaben** | Versionierte Übergaben mit Priorität (Normal/Wichtig/Dringend) und Status (Offen/In Bearbeitung/Erledigt) | ✅ Standard |
| **Wachenkalender** | Einfacher Kalender für Wachenereignisse (kein Dienstplan!) | ✅ Standard |
| **Geburtstagsanzeige** | Freiwillige Anzeige von Geburtstagen (nur Tag & Monat, kein Jahr) | ✅ Optional |
| **Kaffeekasse** | Unveränderliches Ledger mit Korrekturbuchungen | ✅ Optional |
| **Externe Meldungen** | RSS- und Verkehrsquellen (z.B. Straßenverkehr, Warnmeldungen) | ⚠️ Optional |
| **Tagesaufgaben** | Wandtafel-ähnliche Aufgabenverwaltung (täglich/Wochentag/zusätzlich) | ✅ Optional |
| **Checklisten** | Wiederkehrende Checklisten für die Wache | ⚠️ Optional |
| **Wachenchat** | Einfacher interner Chat (End-to-End-verschlüsselt) | ✅ Optional |
| **Müllkalender** | Integration externer Müllabfuhrkalender (ICS) | ⚠️ Optional |

---

## 🏗️ **Technischer Stack**

### **Backend (Server)**

| Komponente | Technologie | Version | Zweck |
|------------|-------------|---------|-------|
| **Web Framework** | Django | 6.0.7 | Hauptanwendung |
| **Datenbank** | PostgreSQL | 17.10 | Datenpersistenz |
| **Web Server** | Gunicorn | 26.0.0 | HTTP-Server |
| **Cache** | Redis | 7.4 | Performance-Optimierung |
| **Container** | Docker | - | Bereitstellung |
| **Orchestrierung** | Docker Compose | v2 | Service-Management |

### **Frontend (Web PWA)**

- **Framework**: Django Templates + Vanilla JavaScript
- **Design**: Material Design 3 (MD3) inspiriert
- **PWA**: Installierbar als App auf Handy/Tablet
- **Offline**: Lesen von gecachten Seiten möglich

### **Mobile Client (Optional)**

- **Framework**: Flutter (Dart)
- **Plattformen**: Android & iOS
- **Repository**: [Wachbuch-Client](https://github.com/darkspike1988/Wachbuch-Client)
- **API**: REST JSON API (v1) mit Token-Authentifizierung

---

## 🔒 **Sicherheit & Datenschutz**

### **Privacy by Design**

✅ **Keine sensiblen Daten**: Keine Patienten-, Einsatz-, Gesundheits- oder Alarmdaten
✅ **Minimale Datenerfassung**: Nur technisch notwendige Daten
✅ **Lokale Konten**: Keine externen Authentifizierungsdienste
✅ **End-to-End-Verschlüsselung**: Chat und private Notizen sind E2EE-verschlüsselt
✅ **Audit-Logging**: Nachvollziehbare Protokollierung aller Änderungen

### **Technische Sicherheitsmaßnahmen**

- **TLS**: Erzwungene Verschlüsselung (Reverse-Proxy)
- **Authentifizierung**: Lokale Konten mit Argon2id-Passwort-Hashing
- **MFA**: Optionale Zwei-Faktor-Authentifizierung (TOTP, WebAuthn/Passkeys)
- **Rate Limiting**: Schutz vor Brute-Force-Angriffen
- **CSP**: Content Security Policy für XSS-Schutz
- **CSRF**: Schutz vor Cross-Site-Request-Forgery
- **ASVS L2**: Orientierung an OWASP Application Security Verification Standard

### **Compliance**

- **Lizenz**: AGPL-3.0-or-later (Open Source)
- **DSGVO**: Konform durch Privacy-by-Design
- **AI Act**: Keine KI-Systeme im Einsatz
- **TDDDG**: Cookie-Hinweise implementiert

---

## 🚀 **Schnellstart mit Docker**

### **Voraussetzungen**

- Docker Engine (mit Compose v2)
- Docker Compose
- Ein freier Port (standardmäßig 8090)
- ca. 500 MB RAM, 1 GB Festplattenspeicher

### **Installation**

```bash
# Repository klonen
git clone https://github.com/Darkspike1988/Rettungswache-Wachbuch.git
cd Rettungswache-Wachbuch

# Umgebungsvariablen kopieren und anpassen
cp .env.example .env

# Zufällige Geheimnisse generieren (für alle PLATZHALTER in .env)
openssl rand -hex 32  # Für DJANGO_SECRET_KEY, DB_PASSWORD, etc.

# Backup-Verzeichnis vorbereiten
sudo chown 70:70 backups

# Container starten
docker compose up --build -d

# Admin-Benutzer erstellen
docker compose exec web python manage.py createsuperuser

# Admin als Stations-Admin festlegen
docker compose exec web python manage.py grant_station_admin BENUTZERNAME
```

### **Erster Zugriff**

- **Web-UI**: [http://127.0.0.1:8090/](http://127.0.0.1:8090/)
- **Login**: [http://127.0.0.1:8090/anmelden/](http://127.0.0.1:8090/anmelden/)

⚠️ **Wichtig**: Der Port bindet nur an **Loopback (127.0.0.1)**. Für externe Zugriffe ist ein Reverse-Proxy (z.B. Nginx, Traefik) mit TLS erforderlich.

---

## 📱 **Mobile Apps (Optional)**

### **Android APK installieren**

1. **Client-Repository klonen**:
   ```bash
   git clone https://github.com/darkspike1988/Wachbuch-Client.git
   cd Wachbuch-Client
   ```

2. **APK bauen (für Testzwecke)**:
   ```bash
   flutter pub get
   flutter build apk --release --flavor internal
   ```

3. **APK installieren**:
   ```bash
   adb install build/app/outputs/flutter-apk/app-internal-release.apk
   ```

### **Server-Adresse in App einrichten**

1. App öffnen
2. Server-Adresse eingeben: `https://deine-wache.example.org`
3. Mit Benutzername und Passwort anmelden
4. **QR-Code-Option**: Im Web-UI unter "Mein Konto → App-Tokens" einen QR-Code generieren

---

## 📚 **Dokumentation**

| Dokument | Beschreibung |
|----------|--------------|
| [Architektur](docs/ARCHITECTURE.md) | Technische Architektur und Vertrauensgrenzen |
| [API v1](docs/API.md) | REST-API für Mobile Clients |
| [Client-Integration](docs/CLIENT.md) | Anleitung für Mobile-Client-Entwicklung |
| [Sicherheit & Datenschutz](docs/SECURITY-PRIVACY.md) | Sicherheitskonzept und Datenschutz |
| [Compliance](docs/COMPLIANCE.md) | DSGVO, TDDDG, AI Act, NRW |
| [Betrieb](docs/OPERATIONS.md) | Backup, Updates, Monitoring |
| [Go-Live-Checkliste](docs/GO-LIVE-CHECKLIST.md) | Vorbereitung für Produktivbetrieb |
| [Roadmap](docs/ROADMAP.md) | Geplante Funktionen und Meilensteine |
| [Design-System](docs/DESIGN-SYSTEM.md) | UI/UX-Richtlinien |

---

## 🤝 **Mitwirken**

Beiträge sind herzlich willkommen! Bitte beachte:

1. **Issue erstellen**: Vor dem Entwickeln ein Issue erstellen oder kommentieren
2. **Fork erstellen**: Eigene Kopie des Repositories erstellen
3. **Branch-Naming**: `feature/xxx`, `fix/xxx`, `docs/xxx`
4. **Pull Request**: Klare Beschreibung und Referenz zum Issue

### **Entwicklungsumgebung**

```bash
# Server
git clone https://github.com/Darkspike1988/Rettungswache-Wachbuch.git
cd Rettungswache-Wachbuch
docker compose up --build -d

# Client
git clone https://github.com/darkspike1988/Wachbuch-Client.git
cd Wachbuch-Client
flutter pub get
flutter run
```

### **Code-Standards**

- **Python**: Black, isort, flake8
- **Dart**: flutter_lints, very_good_analysis
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)

---

## 📄 **Lizenz**

**Copyright (C) 2026 Darkspike1988**

Veröffentlicht unter der **GNU Affero General Public License v3.0 oder später**.

> ⚠️ **Wichtig**: Wer eine geänderte Fassung als Netzwerkdienst betreibt, muss den Benutzern den zugehörigen Quellcode anbieten (AGPL §13).

---

## 🆘 **Support & Community**

- **Issues**: [GitHub Issues](https://github.com/darkspike1988/Rettungswache-Wachbuch/issues)
- **Dokumentation**: [Docs-Verzeichnis](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/darkspike1988/Rettungswache-Wachbuch/discussions)

---

## 🔗 **Verwandte Projekte**

- **[Wachbuch-Client](https://github.com/darkspike1988/Wachbuch-Client)** – Offizielle Flutter-App für Android/iOS
- **[Docker Image](https://github.com/darkspike1988/Rettungswache-Wachbuch/pkgs/container/rettungswache-wachbuch)** – Vorgebaute Container-Images

---

*Letzte Aktualisierung: August 2026 | Version: 0.15.0*