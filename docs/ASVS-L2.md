# ASVS 5.0 Level 2 – Abdeckungsmatrix (Wachbuch)

Stand: 31. Juli 2026. Interne technische Selbsteinschaetzung, kein Zertifikat und
keine Ersatzpruefung durch unabhaengige Stelle.

Referenz: [OWASP ASVS 5.0](https://owasp.org/www-project-application-security-verification-standard/).

Legende: **OK** umgesetzt / **Teil** teilweise / **Offen** geplant / **n/a** nicht anwendbar.

## V1 Architektur und Design

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Vertrauensgrenzen dokumentiert | OK | `docs/ARCHITECTURE.md` |
| Keine Patienten-/Einsatzdaten | OK | Produktgrenze, Privacy-by-Design |
| Threat-Model formal | Teil | Audit + RESEARCH, kein vollstaendiges STRIDE |

## V2 Authentifizierung

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Persoenliche Konten | OK | kein Gemeinschaftskonto |
| Passwort-Login + Lockout | OK | django-axes |
| MFA (TOTP) | OK | optional / erzwingbar |
| Passkeys (WebAuthn) | OK | wenn `WEBAUTHN_RP_ID`/`ORIGIN` gesetzt |
| Passwort-Recovery-Flow | Offen | bewusst nicht oeffentlich; Admin-Reset |
| Credential Stuffing Monitoring | Teil | Axes-Zaehler, kein zentrales SIEM |

## V3 Session Management

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Sichere Session-Cookies | OK | HttpOnly, Secure (Prod), SameSite=Lax |
| CSRF | OK | Token + HttpOnly CSRF-Cookie; SPA-Token im Meta-Tag |
| Session-Timeout | OK | 12h |
| Logout invalidiert Session | OK | Django Logout |

## V4 Access Control

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Rollenmodell stationsbezogen | OK | Membership + Decorator |
| Objektbindung an Station | OK | Query-Filter in Views |
| Auditor ohne Fachinhalt | OK | 403 auf Content-Rollen |
| Kalender-Abo-Token widerrufbar | OK | `CalendarFeedToken` |

## V5 Validation / V7 Error Handling

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Server-seitige Validierung | OK | Forms/Model.clean |
| Keine Stacktraces an Clients | OK | Prod DEBUG=false |
| Einheitliche Fehlerseiten | Teil | Django-Defaults |

## V8 Data Protection

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| TLS am Proxy | OK | dokumentiert |
| HSTS | OK | Django-Setting (Proxy) |
| Append-only Audit/Kasse | OK | ORM + DB-Rechte |
| Retention | Teil | Feeds ja; Audit nur nach Freigabe |
| Geheimnisse in Env | OK | `.env`, keine Secrets im Image |

## V9 Communication

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| CSP | OK | streng; `connect-src` erlaubt HTTPS fuer Push |
| Permissions-Policy | OK | WebAuthn self; Sensoren denied |
| Clickjacking | OK | frame-ancestors/XFO |

## V10 Malicious Code / V12 Files

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Keine User-Uploads | OK | bewusst ausgeschlossen |
| Feed-SSRF-Haertung | OK | Allowlist, keine Redirects |

## V13 API / PWA

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| JSON-Endpunkte CSRF-geschuetzt | OK | Passkey/Push POST |
| Service Worker ohne Write-Queue | OK | Read-only Cache |
| Web-Push opt-in | OK | nur bei VAPID + Nutzeraktion |

## V14 Configuration

| Kontrolle | Status | Hinweis |
| --- | --- | --- |
| Least-privilege DB-Rollen | OK | grant_database_access |
| Healthcheck ohne Secrets | OK | `/healthz/` |
| Dependency-Scanning in CI | Teil | Image-Scan in Workflows/Doku |

## Offene L2-Luecken vor oeffentlichem DNS

1. Unabhaengige ASVS-L2-Pruefung und Lasttest
2. Zentrales Monitoring/Alerting und Incident-Runbook-Probe
3. Passwort-Reset-Prozess organisatorisch festziehen
4. Audit-Export / Offline-Archiv
5. Optional: Secrets-Encryption at rest fuer TOTP/VAPID in der DB

Siehe auch [`GO-LIVE-CHECKLIST.md`](GO-LIVE-CHECKLIST.md) und [`SECURITY-PRIVACY.md`](SECURITY-PRIVACY.md).
