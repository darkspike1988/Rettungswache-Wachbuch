# API v1 – REST-API für Mobile Clients

*Letzte Aktualisierung: August 2026 | Version: 0.15.0 | Status: Stabil*

---

## 📋 **Inhaltsverzeichnis**

1. [Übersicht](#-übersicht)
2. [Authentifizierung](#-authentifizierung)
3. [Endpunkte](#-endpunkte)
4. [Fehlerbehandlung](#-fehlerbehandlung)
5. [Rate Limiting](#-rate-limiting)
6. [Beispiele](#-beispiele)
7. [Sicherheit](#-sicherheit)
8. [Changelog](#-changelog)

---

## 🎯 **Übersicht**

Die **Rettungswache-Wachbuch API v1** ist eine **versionierte REST-API** für Mobile Clients (Android, iOS) und Drittanwendungen. Die API folgt den **Paperless-ngx- und Nextcloud-Konventionen** und ist **vollständig dokumentiert** durch OpenAPI 3.0.

### **Base URL**

```
https://deine-wache.example.org/api/v1/
```

### **API-Version**

- **Aktuelle Version**: `v1`
- **Status**: Stabil
- **Unterstützte Server-Versionen**: ≥ 0.14.1
- **Unterstützte Client-Versionen**: ≥ 0.5.0

### **Content-Type**

- **Request**: `application/json` (außer bei Formular-Daten)
- **Response**: `application/json`

### **Zeitformat**

Alle Zeitstempel folgen dem **ISO 8601-Format**:

```
2026-08-05T14:30:45.123456+02:00
```

---

## 🔐 **Authentifizierung**

### **1. Token-basierte Authentifizierung**

Die API verwendet **Bearer-Tokens** (auch als `Token`-Header unterstützt):

```http
Authorization: Bearer wb_abc123def456...
```

oder:

```http
Authorization: Token wb_abc123def456...
```

### **2. Token erzeugen**

#### **Methode 1: Über Web-UI (empfohlen bei MFA)**

1. Im Web-UI unter **Mein Konto → App-Tokens** (`/konto/api/`) ein neues Token erstellen
2. Token **kopieren** (wird nur einmal angezeigt!)
3. Token in der App speichern

#### **Methode 2: Über API (nur ohne MFA)**

```http
POST /api/v1/token/ HTTP/1.1
Content-Type: application/json

{
  "username": "dein-benutzername",
  "password": "dein-passwort",
  "label": "Meine Android App"
}
```

**Response:**

```json
{
  "ok": true,
  "token": "wb_abc123def456...",
  "expires_at": "2026-11-05T14:30:45Z",
  "expires_in": 7776000
}
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `username` | string | ✅ | Benutzername |
| `password` | string | ✅ | Passwort |
| `label` | string | ❌ | Beschreibung des Tokens (Default: "Mobile App") |

**Hinweise:**
- Tokens sind **standardmäßig 90 Tage gültig**
- Bei **aktiviertem MFA** muss Methode 1 verwendet werden
- **Passwortänderung widerruft alle Tokens** des Benutzers

### **3. Token widerrufen**

Tokes können auf zwei Wegen widerrufen werden:

1. **Über Web-UI**: Unter **Mein Konto → App-Tokens**
2. **Durch Passwortänderung**: Alle Tokens werden automatisch widerrufen

### **4. Token-Scopes**

Alle Tokens erhalten **standardmäßig** folgende Scopes:

| Scope | Beschreibung |
|-------|--------------|
| `read:me` | Benutzerprofil lesen |
| `read:handovers` | Übergaben lesen |
| `write:handovers` | Übergaben erstellen/bearbeiten |
| `read:calendar` | Kalender lesen |
| `write:calendar` | Kalender bearbeiten |
| `read:coffee` | Kaffeekasse lesen |
| `write:coffee` | Kaffeekasse bearbeiten |
| `read:checklists` | Checklisten lesen |
| `write:checklists` | Checklisten bearbeiten |

> ⚠️ **Wichtig**: Zusätzlich gelten **stationsbezogene Rollen** (Member, Shift Lead, Admin, etc.)

---

## 📡 **Endpunkte**

### **🔍 Discovery & Status**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/` | API-Info und Version | ❌ | 120/min |
| `GET` | `/api/v1/openapi.yaml` | OpenAPI 3.0 Spezifikation | ❌ | 120/min |
| `GET` | `/api/v1/status/` | Auth- und Mitgliedschaftsstatus | ⚠️ | 120/min |

#### **GET /api/v1/**

**Beschreibung:** Gibt Informationen über die API zurück.

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "server_version": "0.15.0",
  "app_name": "Wachbuch",
  "documentation": "/api/v1/docs/"
}
```

#### **GET /api/v1/status/**

**Beschreibung:** Gibt den Authentifizierungs- und Mitgliedschaftsstatus zurück.

**Response (ohne Auth):**

```json
{
  "ok": true,
  "authenticated": false,
  "api_version": "v1"
}
```

**Response (mit Auth):**

```json
{
  "ok": true,
  "authenticated": true,
  "has_membership": true,
  "station_id": 1,
  "station_name": "Rettungswache Musterstadt",
  "role": "admin",
  "api_version": "v1"
}
```

---

### **👤 Benutzer & Mitgliedschaft**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/me/` | Benutzerprofil und Mitgliedschaft | ✅ | 60/min |

#### **GET /api/v1/me/**

**Beschreibung:** Gibt das Benutzerprofil und die Mitgliedschaftsinformationen zurück.

**Scopes:** `read:me`

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "user": {
    "id": 1,
    "username": "max.mustermann",
    "first_name": "Max",
    "last_name": "Mustermann"
  },
  "membership": {
    "id": 1,
    "station": {
      "id": 1,
      "name": "Rettungswache Musterstadt",
      "slug": "rettungswache-musterstadt"
    },
    "role": "admin",
    "role_label": "Master-Admin",
    "is_active": true,
    "created_at": "2026-01-01T10:00:00Z"
  },
  "modules": {
    "calendar": true,
    "chat": true,
    "tasks": true,
    "coffee": true,
    "feeds": false,
    "birthdays": true,
    "holidays": true,
    "checklists": false
  }
}
```

---

### **📋 Übergaben (Handovers)**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/handovers/` | Liste aktiver Übergaben | ✅ | 100/min |
| `POST` | `/api/v1/handovers/` | Neue Übergabe erstellen | ✅ | 30/min |
| `GET` | `/api/v1/handovers/{id}/` | Übergabe-Details | ✅ | 100/min |
| `POST` | `/api/v1/handovers/{id}/status/` | Status ändern | ✅ | 30/min |

**Deutsche Aliase:**
- `/api/v1/uebergaben/` ↔ `/api/v1/handovers/`
- `/api/v1/uebergaben/{id}/` ↔ `/api/v1/handovers/{id}/`
- `/api/v1/uebergaben/{id}/status/` ↔ `/api/v1/handovers/{id}/status/`

#### **GET /api/v1/handovers/**

**Beschreibung:** Gibt eine Liste aller aktiven (nicht erledigten) Übergaben für die Station des Benutzers zurück.

**Scopes:** `read:handovers`

**Query Parameter:**

| Parameter | Typ | Beschreibung | Default |
|-----------|-----|--------------|---------|
| `status` | string | Filter nach Status (`open`, `in_progress`) | Alle |
| `priority` | string | Filter nach Priorität (`normal`, `important`, `urgent`) | Alle |
| `category` | string | Filter nach Kategorie (`station`, `vehicle`, `material`, `task`, `safety`) | Alle |
| `limit` | integer | Maximale Anzahl Ergebnisse | 50 |
| `offset` | integer | Offset für Pagination | 0 |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "station": 1,
      "category": "station",
      "category_label": "Wache",
      "priority": "urgent",
      "priority_label": "Dringend",
      "status": "open",
      "status_label": "Offen",
      "title": "Defektes Funkgerät",
      "details": "Das Funkgerät im Einsatzfahrzeug 1 funktioniert nicht mehr.",
      "author": {
        "id": 2,
        "username": "peter.parker",
        "display_name": "Peter Parker"
      },
      "version": 1,
      "created_at": "2026-08-05T10:00:00Z",
      "updated_at": "2026-08-05T10:00:00Z",
      "completed_at": null
    }
  ]
}
```

#### **POST /api/v1/handovers/**

**Beschreibung:** Erstellt eine neue Übergabe.

**Scopes:** `write:handovers`

**Request:**

```json
{
  "category": "station",
  "priority": "normal",
  "title": "Neue Übergabe",
  "details": "Hier steht der Text der Übergabe."
}
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `category` | string | ✅ | Kategorie (`station`, `vehicle`, `material`, `task`, `safety`) |
| `priority` | string | ✅ | Priorität (`normal`, `important`, `urgent`) |
| `title` | string | ✅ | Titel (max. 160 Zeichen) |
| `details` | string | ❌ | Details (max. 3000 Zeichen) |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "id": 2,
  "version": 1,
  "created_at": "2026-08-05T14:30:00Z"
}
```

#### **GET /api/v1/handovers/{id}/**

**Beschreibung:** Gibt die Details einer bestimmten Übergabe zurück.

**Scopes:** `read:handovers`

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "id": 1,
  "station": 1,
  "category": "station",
  "category_label": "Wache",
  "priority": "urgent",
  "priority_label": "Dringend",
  "status": "open",
  "status_label": "Offen",
  "title": "Defektes Funkgerät",
  "details": "Das Funkgerät im Einsatzfahrzeug 1 funktioniert nicht mehr.",
  "author": {
    "id": 2,
    "username": "peter.parker",
    "display_name": "Peter Parker"
  },
  "version": 1,
  "created_at": "2026-08-05T10:00:00Z",
  "updated_at": "2026-08-05T10:00:00Z",
  "completed_at": null,
  "revisions": []
}
```

#### **POST /api/v1/handovers/{id}/status/**

**Beschreibung:** Ändert den Status einer Übergabe.

**Scopes:** `write:handovers`

**Request:**

```json
{
  "status": "in_progress"
}
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `status` | string | ✅ | Neuer Status (`open`, `in_progress`, `done`) |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "id": 1,
  "status": "in_progress",
  "updated_at": "2026-08-05T14:30:00Z"
}
```

---

### **📅 Kalender**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/kalender/` | Kalenderereignisse | ✅ | 100/min |
| `POST` | `/api/v1/kalender/` | Neues Ereignis erstellen | ✅ | 30/min |

**Deutsche Aliase:**
- `/api/v1/kalender/` ↔ `/api/v1/calendar/`

#### **GET /api/v1/kalender/**

**Beschreibung:** Gibt eine Liste aller Kalenderereignisse für die Station des Benutzers zurück.

**Scopes:** `read:calendar`

**Query Parameter:**

| Parameter | Typ | Beschreibung | Default |
|-----------|-----|--------------|---------|
| `start` | date | Startdatum (YYYY-MM-DD) | Heute |
| `end` | date | Enddatum (YYYY-MM-DD) | Heute + 30 Tage |
| `limit` | integer | Maximale Anzahl Ergebnisse | 50 |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "count": 2,
  "results": [
    {
      "id": 1,
      "station": 1,
      "title": "Wachenputz",
      "description": "Gemeinsamer Putz der Wache",
      "starts_at": "2026-08-10T09:00:00Z",
      "ends_at": "2026-08-10T12:00:00Z",
      "created_by": {
        "id": 1,
        "username": "max.mustermann",
        "display_name": "Max Mustermann"
      },
      "created_at": "2026-08-01T10:00:00Z"
    }
  ]
}
```

---

### **☕ Kaffeekasse**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/kaffeekasse/` | Kassenbuchungen | ✅ | 100/min |
| `POST` | `/api/v1/kaffeekasse/` | Neue Buchung erstellen | ✅ | 30/min |

**Deutsche Aliase:**
- `/api/v1/kaffeekasse/` ↔ `/api/v1/coffee/`

#### **GET /api/v1/kaffeekasse/**

**Beschreibung:** Gibt die Kassenbuchungen für die Station des Benutzers zurück.

**Scopes:** `read:coffee`

**Query Parameter:**

| Parameter | Typ | Beschreibung | Default |
|-----------|-----|--------------|---------|
| `limit` | integer | Maximale Anzahl Ergebnisse | 50 |
| `offset` | integer | Offset für Pagination | 0 |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "count": 10,
  "balance_cents": 1500,
  "balance_euros": 15.00,
  "results": [
    {
      "id": 1,
      "station": 1,
      "member": {
        "id": 1,
        "username": "max.mustermann",
        "display_name": "Max Mustermann"
      },
      "amount_cents": 100,
      "amount_euros": 1.00,
      "reason": "Kaffee",
      "created_by": {
        "id": 1,
        "username": "max.mustermann",
        "display_name": "Max Mustermann"
      },
      "created_at": "2026-08-05T10:00:00Z"
    }
  ]
}
```

#### **POST /api/v1/kaffeekasse/**

**Beschreibung:** Erstellt eine neue Kassenbuchung.

**Scopes:** `write:coffee`

**Request:**

```json
{
  "member_id": 1,
  "amount_cents": 100,
  "reason": "Kaffee"
}
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `member_id` | integer | ✅ | Benutzer-ID, für die gebucht wird |
| `amount_cents` | integer | ✅ | Betrag in Cent (positiv oder negativ) |
| `reason` | string | ✅ | Grund der Buchung (max. 200 Zeichen) |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "id": 11,
  "balance_cents": 1600,
  "balance_euros": 16.00,
  "created_at": "2026-08-05T14:30:00Z"
}
```

---

### **✅ Checklisten**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/checklisten/` | Checklisten | ✅ | 100/min |
| `POST` | `/api/v1/checklisten/{id}/erledigt/` | Checkliste abschließen | ✅ | 30/min |

**Deutsche Aliase:**
- `/api/v1/checklisten/` ↔ `/api/v1/checklists/`
- `/api/v1/checklisten/{id}/erledigt/` ↔ `/api/v1/checklists/{id}/complete/`
- `/api/v1/checklisten/{id}/abschluss/` ↔ `/api/v1/checklists/{id}/complete/` (Alias)

#### **GET /api/v1/checklisten/**

**Beschreibung:** Gibt alle Checklisten für die Station des Benutzers zurück.

**Scopes:** `read:checklists`

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "count": 3,
  "results": [
    {
      "id": 1,
      "station": 1,
      "title": "Schichtbeginn",
      "description": "Checkliste für den Schichtbeginn",
      "items": [
        {
          "id": 1,
          "title": "Funkgerät prüfen",
          "is_completed": false,
          "completed_at": null,
          "completed_by": null
        }
      ],
      "is_active": true,
      "created_at": "2026-01-01T10:00:00Z"
    }
  ]
}
```

#### **POST /api/v1/checklisten/{id}/erledigt/**

**Beschreibung:** Markiert eine Checkliste als erledigt.

**Scopes:** `write:checklists`

**Request:**

```json
{
  "note": "Alles geprüft"
}
```

**Parameter:**

| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| `note` | string | ❌ | Notiz zur Checkliste (max. 160 Zeichen) |

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "id": 1,
  "completed_at": "2026-08-05T14:30:00Z",
  "completed_by": {
    "id": 1,
    "username": "max.mustermann",
    "display_name": "Max Mustermann"
  }
}
```

---

### **📊 Dashboard / Übersicht**

| Methode | Endpunkt | Beschreibung | Auth | Rate Limit |
|---------|----------|--------------|------|------------|
| `GET` | `/api/v1/uebersicht/` | Dashboard-Zusammenfassung | ✅ | 60/min |

**Deutsche Aliase:**
- `/api/v1/uebersicht/` ↔ `/api/v1/overview/`

#### **GET /api/v1/uebersicht/**

**Beschreibung:** Gibt eine Zusammenfassung für das Dashboard zurück.

**Scopes:** `read:me`, `read:handovers`

**Response:**

```json
{
  "ok": true,
  "api_version": "v1",
  "station": {
    "id": 1,
    "name": "Rettungswache Musterstadt",
    "slug": "rettungswache-musterstadt"
  },
  "role": "admin",
  "role_label": "Master-Admin",
  "modules": {
    "calendar": true,
    "chat": true,
    "tasks": true,
    "coffee": true,
    "feeds": false,
    "birthdays": true,
    "holidays": true,
    "checklists": false
  },
  "handovers": {
    "open_count": 3,
    "urgent_count": 1,
    "items": [
      {
        "id": 1,
        "title": "Defektes Funkgerät",
        "priority": "urgent",
        "priority_label": "Dringend",
        "status": "open",
        "status_label": "Offen",
        "author": "Peter Parker",
        "created_at": "2026-08-05T10:00:00Z"
      }
    ]
  }
}
```

---

## ❌ **Fehlerbehandlung**

### **Fehlercodes**

| Code | HTTP Status | Beschreibung |
|------|-------------|--------------|
| `auth_required` | 401 | Authentifizierung erforderlich |
| `forbidden` | 403 | Keine Berechtigung |
| `not_found` | 404 | Ressource nicht gefunden |
| `validation_error` | 400 | Ungültige Anfragedaten |
| `rate_limit` | 429 | Rate Limit überschritten |
| `server_error` | 500 | Interner Serverfehler |

### **Fehler-Response-Format**

```json
{
  "ok": false,
  "error": {
    "code": "auth_required",
    "message": "Authentifizierung erforderlich. Bitte melden Sie sich an.",
    "details": {}
  }
}
```

### **Häufige Fehler**

#### **401 Unauthorized**

```json
{
  "ok": false,
  "error": {
    "code": "auth_required",
    "message": "Authentifizierung erforderlich. Bitte melden Sie sich an."
  }
}
```

**Lösung:** Token im `Authorization`-Header senden.

#### **403 Forbidden**

```json
{
  "ok": false,
  "error": {
    "code": "forbidden",
    "message": "Scope read:handovers fehlt."
  }
}
```

**Lösung:** Token mit den richtigen Scopes verwenden oder Rollen prüfen.

#### **429 Too Many Requests**

```json
{
  "ok": false,
  "error": {
    "code": "rate_limit",
    "message": "Rate limit exceeded. Please try again later."
  }
}
```

**Lösung:** Warten und später erneut versuchen.

---

## ⏱️ **Rate Limiting**

### **Standard-Limits**

| Endpunkt | Limit | Fenster |
|----------|-------|---------|
| `/api/v1/token/` | 10 | 1 Minute |
| `/api/v1/me/` | 60 | 1 Minute |
| `/api/v1/uebersicht/` | 60 | 1 Minute |
| `/api/v1/handovers/` (GET) | 100 | 1 Minute |
| `/api/v1/handovers/` (POST) | 30 | 1 Minute |
| `/api/v1/handovers/{id}/status/` | 30 | 1 Minute |
| `/api/v1/kalender/` (GET) | 100 | 1 Minute |
| `/api/v1/kalender/` (POST) | 30 | 1 Minute |
| `/api/v1/kaffeekasse/` (GET) | 100 | 1 Minute |
| `/api/v1/kaffeekasse/` (POST) | 30 | 1 Minute |
| `/api/v1/checklisten/` | 100 | 1 Minute |
| Alle anderen | 120 | 1 Minute |

### **Rate Limit Header**

Die API sendet folgende Header mit Rate Limit Informationen:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 30
```

---

## 📋 **Beispiele**

### **Beispiel 1: Kompletter Authentifizierungsflow**

```bash
# 1. Discovery
curl -i https://wache.example.org/api/v1/

# 2. Token erhalten
curl -i -X POST https://wache.example.org/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max.mustermann", "password": "geheim123", "label": "Meine App"}'

# 3. Benutzerprofil abrufen
TOKEN=$(curl -s -X POST https://wache.example.org/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "max.mustermann", "password": "geheim123"}' | jq -r '.token')

curl -i https://wache.example.org/api/v1/me/ \
  -H "Authorization: Bearer $TOKEN"

# 4. Übergaben abrufen
curl -i https://wache.example.org/api/v1/handovers/ \
  -H "Authorization: Bearer $TOKEN"
```

### **Beispiel 2: Übergabe erstellen**

```bash
curl -i -X POST https://wache.example.org/api/v1/handovers/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category": "station", "priority": "urgent", "title": "Defektes Gerät", "details": "Das Gerät funktioniert nicht."}'
```

### **Beispiel 3: Kalenderereignisse abrufen**

```bash
curl -i "https://wache.example.org/api/v1/kalender/?start=2026-08-01&end=2026-08-31" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔒 **Sicherheit**

### **TLS**

- **Erzwungen**: Alle Verbindungen müssen über **HTTPS** erfolgen
- **Zertifikate**: Gültige, vertrauenswürdige Zertifikate erforderlich
- **Protokolle**: TLS 1.2 oder höher

### **Authentifizierung**

- **Token-Länge**: 64 Zeichen (Prefix + 48 Zufallszeichen)
- **Token-Format**: `wb_<48 zufällige Zeichen>`
- **Token-Speicherung**: **Hash nur** in der Datenbank (SHA-256)
- **Token-Widerruf**: Jederzeit möglich

### **Daten**

- **Keine sensiblen Daten**: Keine Patienten-, Einsatz-, Gesundheitsdaten
- **Minimale Datenerfassung**: Nur technisch notwendige Daten
- **E2EE**: Chat-Nachrichten sind End-to-End-verschlüsselt

### **Rate Limiting**

- **IP-basiert**: Standardmäßig nach Client-IP
- **Benutzer-basiert**: Für authentifizierte Anfragen nach Benutzer
- **Endpoint-spezifisch**: Unterschiedliche Limits für verschiedene Endpunkte

---

## 📅 **Changelog**

| Version | Datum | Änderungen |
|---------|-------|-----------|
| **v1** | 01.08.2026 | Erste stabile Version |
| | | Token-Authentifizierung |
| | | Alle Kern-Endpunkte (Handovers, Calendar, Coffee, Checklists) |
| | | Deutsche Alias-Pfade |
| | | Rate Limiting |
| | | OpenAPI-Spezifikation |

---

## 📚 **Weiterführende Dokumentation**

- [Architektur](ARCHITECTURE.md) – Technische Architektur und Vertrauensgrenzen
- [Client-Integration](CLIENT.md) – Anleitung für Mobile-Client-Entwicklung
- [Sicherheit & Datenschutz](SECURITY-PRIVACY.md) – Sicherheitskonzept
- [Betrieb](OPERATIONS.md) – Backup, Updates, Monitoring

---

*Letzte Aktualisierung: August 2026 | API-Version: v1 | Server-Version: 0.15.0+*