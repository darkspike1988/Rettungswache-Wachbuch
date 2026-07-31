# Mitwirken am Wachbuch-Client

1. Fork oder Branch anlegen.
2. Keine echten Wach-, Mitarbeiter- oder Zugangsdaten in Issues/Commits.
3. Gegen einen lokalen oder Test-Wachbuch-Server mit `/api/v1/` entwickeln.
4. Vor dem PR:

```bash
flutter pub get
flutter analyze
flutter test
```

API-Vertrag und Server: https://github.com/darkspike1988/Rettungswache-Wachbuch  
Client-Doku im Server-Repo: `docs/CLIENT.md` / `docs/API.md`

Lizenz: AGPL-3.0-or-later (siehe `LICENSE`).
