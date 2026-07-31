# Server-Kopplung

Dieses Client-Repo gehört zu:

**https://github.com/darkspike1988/Rettungswache-Wachbuch**

| Client | Server |
| --- | --- |
| App 0.2.x | API `/api/v1/` ab Server **0.12.0** |
| Adresse / QR → Login | Discovery `GET /api/v1/` |
| User / Passwort | `POST /api/v1/token/` |
| MFA | App-Token unter `/konto/api/` |
| Station | nur aus `GET /api/v1/me/` |
| Übergaben | `GET /api/v1/handovers/` |

Header: `Authorization: Token <wb_…>`

Ausführlich: [docs/API.md im Server](https://github.com/darkspike1988/Rettungswache-Wachbuch/blob/main/docs/API.md)
