# 08 – Deployment

## Option A: Docker Compose (ein Server, ~5 €/Monat)

Geeignet für einen kleinen VPS (Hetzner, netcup, …) oder einen Heimserver.

```bash
git clone <repo> && cd <repo>
cp .env.example .env
# .env anpassen:
#   SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
#   POSTGRES_PASSWORD=<zufällig>
#   CORS_ORIGINS=https://ledger.example.com
#   COOKIE_SECURE=true
#   AI_PROVIDER=anthropic  ANTHROPIC_API_KEY=sk-ant-…   (optional, sonst Mock)
docker compose up --build -d
```

- `web` (nginx) lauscht auf Port 8080 und proxyt `/api` zum `api`-Container.
- Davor gehört ein TLS-Terminator (Caddy, Traefik oder nginx mit Let's Encrypt). Beispiel Caddy:
  ```
  ledger.example.com {
      reverse_proxy localhost:8080
  }
  ```
- Der API-Container führt beim Start `alembic upgrade head` aus.
- Persistente Daten: Volumes `db-data` (PostgreSQL) und `uploads` (Belege). **Backups:**
  `docker compose exec db pg_dump -U ledgerlens ledgerlens > backup.sql` und das Upload-Volume
  sichern.

## Option B: Managed Plattformen (kostenlos bis wenige Euro)

| Komponente | Anbieter (Beispiele) | Hinweise |
|---|---|---|
| API | Render, Railway, Fly.io | Dockerfile in `apps/api` verwenden; Health-Check `/health`; persistentes Volume für `UPLOAD_DIR` **oder** S3-Backend (Roadmap) |
| Datenbank | Neon, Supabase, Render Postgres | `DATABASE_URL=postgresql+psycopg://…` |
| Frontend | Vercel, Netlify, Cloudflare Pages | `apps/web` bauen (`npm run build`, Output `dist`) |

Bei getrennten Domains (z. B. `app.example.com` + `api.example.com`) gilt:

1. `VITE_API_BASE_URL=https://api.example.com` beim Frontend-Build setzen.
2. `CORS_ORIGINS=https://app.example.com` in der API.
3. Das Refresh-Cookie ist `SameSite=Lax` – **Cross-Site-Requests senden es nicht mit.**
   Entweder beide unter einer Domain betreiben (Sub-Pfad-Proxy wie in nginx.conf, empfohlen) oder
   das Cookie auf `SameSite=None; Secure` umstellen (dann CSRF-Schutz für `/auth/refresh`
   ergänzen, z. B. Double-Submit-Token).

Die Ein-Origin-Variante ist der Grund, warum der Frontend-Container nginx als Proxy enthält.

## Umgebungsvariablen

Siehe [`.env.example`](../.env.example). Pflicht in Produktion: `APP_ENV=production`,
`SECRET_KEY`, `DATABASE_URL` (PostgreSQL), `CORS_ORIGINS`. Die App verweigert den Start, wenn
`SECRET_KEY` fehlt/zu kurz ist oder in Produktion SQLite konfiguriert ist.

## Betrieb

| Thema | Empfehlung |
|---|---|
| Logs | stdout/stderr der Container (`docker compose logs -f api`) |
| Monitoring | `/health` per Uptime-Check; Roadmap: strukturierte Logs + Metriken |
| Updates | `git pull && docker compose up --build -d` – Migrationen laufen automatisch |
| Skalierung | API ist stateless (JWT + DB-Refresh-Tokens) → mehrere Replikas möglich, sobald Rate-Limit (Redis) und Storage (S3) extern sind |
| Kosten | VPS 4–6 €, Postgres inklusive, KI je nach Belegvolumen (Cent pro Beleg) |

## Lokale Entwicklung ohne Docker

Siehe README ("Quick start"): SQLite + Mock-Provider, keine externen Dienste nötig.
