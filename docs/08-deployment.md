# 08 – Deployment

## Option A: Eigener Server mit Docker Compose (empfohlen, ~4–6 €/Monat)

Ein kleiner Linux-Server reicht, zum Beispiel Hetzner CX22 oder netcup mit Ubuntu 24.04.
Der Stack besteht aus PostgreSQL, API, nginx für das Frontend und Caddy für HTTPS. Caddy
holt das Let's-Encrypt-Zertifikat automatisch und leitet HTTP auf HTTPS um.

Dieser Weg ist mit `deploy/smoke-test.sh` getestet: Registrierung, Beleg-Upload, Extraktion,
Buchung, Dashboard und Refresh-Cookie über HTTPS. Die CI startet den Stack bei jedem Push und
führt denselben Test aus.

### 1. Server und Domain

1. Server mit Ubuntu anlegen und beim Anlegen deinen SSH-Schlüssel hinterlegen.
   Unter Windows erzeugst du ihn in PowerShell mit `ssh-keygen` und kopierst den Inhalt von
   `$HOME\.ssh\id_ed25519.pub`.
2. Bei deinem Domain-Anbieter einen **A-Record** anlegen, z. B. `ledger.example.com`, der auf
   die IPv4-Adresse des Servers zeigt. Die Änderung braucht oft einige Minuten.
3. In der Firewall des Anbieters die Ports **22, 80 und 443** freigeben.

### 2. Auf dem Server einrichten

Verbinden, unter Windows direkt aus PowerShell:

```bash
ssh root@<SERVER-IP>
```

Dann auf dem Server:

```bash
curl -fsSL https://get.docker.com | sh
apt-get install -y git
git clone https://github.com/Hamzo069/LedgerLens.git
cd LedgerLens
cp .env.example .env
nano .env
```

In `.env` diese Werte setzen:

```
SECRET_KEY=<Ausgabe von: openssl rand -base64 48>
POSTGRES_PASSWORD=<Ausgabe von: openssl rand -hex 24>
DOMAIN=ledger.example.com
CORS_ORIGINS=https://ledger.example.com
COOKIE_SECURE=true
AI_PROVIDER=mock                 # oder anthropic
ANTHROPIC_API_KEY=               # nur bei AI_PROVIDER=anthropic
```

Setze `POSTGRES_PASSWORD` vor dem ersten Start. PostgreSQL übernimmt es nur beim Anlegen
des Datenbank-Volumes. Verwende nur Buchstaben und Ziffern, deshalb `-hex`. Das Passwort
wird Teil der Datenbank-URL, und Zeichen wie `/` würden sie zerbrechen. Die übrigen Einträge
der Datei betreffen nur die lokale Entwicklung ohne Docker und werden hier ignoriert.

### 3. Starten

```bash
docker compose --profile https up --build -d
docker compose ps          # alle Dienste "Up", api "healthy"
```

Nach ein bis zwei Minuten ist die App unter `https://ledger.example.com` erreichbar.
Prüfen lässt sich der Stack mit demselben Test wie in der CI:

```bash
BASE_URL=https://ledger.example.com sh deploy/smoke-test.sh
```

Das Skript legt dabei ein Testkonto `smoke-…@example.com` an. Du kannst es danach unter
Settings → Danger zone löschen.

### Was die Konfiguration absichert

- Nur Caddy ist von außen erreichbar. nginx lauscht ausschließlich auf `127.0.0.1:8080`,
  API und Datenbank sind nur im internen Docker-Netz erreichbar.
- Die API vertraut `X-Forwarded-For` nur aus privaten Netzen. Caddy verwirft gefälschte
  Header von außen, deshalb greifen die Rate-Limits pro echter Client-Adresse.
- `COOKIE_SECURE=true` sorgt dafür, dass das Refresh-Cookie nur über HTTPS gesendet wird.
- Die API startet in Produktion nur mit ausreichend langem `SECRET_KEY`, mit PostgreSQL und
  mit aktuellem Datenbankschema. Die Migrationen laufen vor dem Start automatisch.

### Updates, Logs und Backups

```bash
git pull && docker compose --profile https up --build -d     # Update, Migrationen laufen automatisch
docker compose logs -f api                                   # Logs
docker compose exec db pg_dump -U ledgerlens ledgerlens > backup-$(date +%F).sql
```

Belege liegen im Volume `uploads`, die Datenbank im Volume `db-data`. Beide gehören ins
Backup.

### Lokal testen, ohne Domain

Ohne `--profile https` startet der Stack ohne Caddy unter `http://localhost:8080`. Das
funktioniert auch unter Windows mit Docker Desktop. Setze dafür `COOKIE_SECURE=false` und
`CORS_ORIGINS=http://localhost:8080`.

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
