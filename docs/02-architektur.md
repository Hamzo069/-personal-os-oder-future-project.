# 02 – Architektur

## Überblick

LedgerLens ist ein Monorepo mit zwei eigenständig deploybaren Anwendungen:

```
┌──────────────────────────┐        HTTPS / JSON         ┌──────────────────────────────┐
│  apps/web  (React SPA)   │ ──────────────────────────▶ │  apps/api  (FastAPI)          │
│  Vite · TypeScript ·     │ ◀────────────────────────── │  SQLAlchemy 2 · Pydantic v2   │
│  TanStack Query ·        │   Bearer-Token + httpOnly   │  Alembic · Argon2 · PyJWT     │
│  Tailwind 4 · Recharts   │   Refresh-Cookie            │                               │
└──────────────────────────┘                             │   ┌───────────┐  ┌──────────┐ │
                                                         │   │ Services  │  │ AI Layer │ │
                                                         │   └─────┬─────┘  └────┬─────┘ │
                                                         └─────────┼─────────────┼───────┘
                                                                   │             │
                                                     ┌─────────────▼──┐   ┌──────▼─────────────┐
                                                     │ PostgreSQL /   │   │ Claude API         │
                                                     │ SQLite (dev)   │   │ (oder Mock-Provider)│
                                                     └────────────────┘   └────────────────────┘
                                                     ┌────────────────┐
                                                     │ Dateiablage    │  (lokal, S3-fähig)
                                                     └────────────────┘
```

## Warum dieser Tech-Stack?

| Baustein | Wahl | Begründung | Alternativen |
|---|---|---|---|
| Backend | **FastAPI (Python 3.11+)** | Typisierte Endpunkte, automatische OpenAPI-Doku, Pydantic-Validierung; Python ist die Lingua franca der KI-Welt | Django (schwerer), Node/NestJS (ein Sprach-Stack, aber weniger KI-Ökosystem) |
| ORM / Migrationen | **SQLAlchemy 2.0 + Alembic** | Industriestandard, typisierte Modelle, explizite Migrationen | SQLModel (dünner, weniger Kontrolle), Prisma (Node) |
| Datenbank | **SQLite (dev) / PostgreSQL (prod)** | Null Setup lokal, produktionsreif in der Cloud; nur portable Spaltentypen | nur Postgres (höhere Einstiegshürde) |
| Auth | **Argon2id + JWT + rotierende Refresh-Tokens** | lehrreich, ohne Vendor-Lock-in, alle Security-Konzepte sichtbar | Auth-as-a-Service (Clerk, Supabase) – schneller, aber Blackbox |
| KI | **Anthropic Claude via Structured Outputs** | Schema-garantierte JSON-Antworten, Bild- und PDF-Eingabe, Prompt-Caching | OpenAI, lokale Modelle (Ollama) – über das Provider-Interface nachrüstbar |
| Frontend | **React 19 + Vite + TypeScript** | größte Verbreitung, schnellste Toolchain, typsichere API-Anbindung | Next.js (SSR unnötig für eine App hinter Login), Vue/Svelte |
| Datenabruf | **TanStack Query** | Caching, Polling (Extraktionsstatus), Invalidation nach Mutationen | SWR, eigenes Fetch-Handling |
| Styling | **Tailwind CSS 4** | schnelle, konsistente UI ohne CSS-Architektur-Overhead | CSS Modules, Component-Library (MUI) |
| Tests | **pytest + httpx / Vitest + Testing Library / Playwright** | API-Tests ohne Netzwerk, Komponententests, ein echter Browser-Flow | – |
| Betrieb | **Docker Compose, GitHub Actions** | reproduzierbar, kostenlos | – |

Leitprinzip: **modern, aber verständlich**. Keine Microservices, kein Message-Broker, keine
Event-Sourcing-Architektur – ein klar geschichteter Monolith, der sich später aufteilen lässt.

## Schichten im Backend

```
app/
├── main.py            # App-Factory, Middleware (CORS, Security-Header), Router-Registrierung
├── core/              # Querschnitt: Konfiguration, DB-Engine, Fehler, Security, Rate-Limit
├── models/            # SQLAlchemy-Tabellen (Persistenz)
├── schemas/           # Pydantic-Modelle (API-Verträge: Request/Response)
├── api/v1/            # Router = dünne HTTP-Schicht: parst, ruft Service, formt Antwort
├── services/          # Geschäftslogik, transaktional, unabhängig von HTTP
├── ai/                # Provider-Interface, Prompts, Structured-Output-Schemas, Mock
└── storage/           # Dateiablage (lokal; S3 über gleiches Interface möglich)
```

Regeln:

- Router enthalten **keine** Geschäftslogik. Sie validieren Eingaben (Pydantic), rufen genau einen
  Service auf und geben ein Schema zurück.
- Services kennen **kein** HTTP. Fehler werden als `AppError`-Subklassen geworfen, die der
  zentrale Exception-Handler in das einheitliche JSON-Format übersetzt.
- Alle Ressourcen sind **user-scoped**: jede Abfrage filtert nach `user_id`; fremde IDs führen zu
  404 (nicht 403, um keine Existenz zu verraten).
- Geldbeträge sind `Decimal`, niemals `float`.

## Wie Frontend und Backend kommunizieren

1. Das Frontend spricht ausschließlich über `/api/v1/*` mit JSON (Ausnahme: Datei-Upload als
   `multipart/form-data`, Datei-Download und CSV-Export als Binär-/Text-Response).
2. Im Development proxyt der Vite-Dev-Server `/api` auf `localhost:8000`; in Produktion übernimmt
   nginx dieselbe Rolle. Dadurch sind Frontend und API **same-origin** – das Refresh-Cookie
   funktioniert ohne Cross-Site-Konfiguration.
3. `src/lib/api.ts` ist der einzige Ort, der `fetch` aufruft. Er hängt den Access-Token an,
   erneuert ihn bei 401 automatisch (ein gemeinsamer In-flight-Refresh für parallele Requests) und
   übersetzt die Fehlerhülle in `ApiError`.
4. `src/api/hooks.ts` kapselt jede Ressource als TanStack-Query-Hook. Mutationen invalidieren die
   betroffenen Queries (z. B. `transactions` und `summary` nach einer Buchung).
5. Typen in `src/types.ts` spiegeln die Pydantic-Schemas 1:1 – bei Änderungen an der API ist das
   die Stelle, die mitgezogen wird (Roadmap: Generierung aus OpenAPI).

## Der Beleg-Prozess (Kern-Use-Case)

```
Upload ──▶ Validierung ──▶ Speichern ──▶ [Hintergrund] KI-Extraktion ──▶ Review ──▶ Buchung
 (202)     Magic Bytes,    uuid-Name      Status: processing → extracted     Nutzer     Transaction
           Größe           pro Nutzer     Kontext: Kategorien + Hints       korrigiert  + Feedback
```

- Der Upload antwortet sofort mit `202 Accepted`; die Extraktion läuft als `BackgroundTask`.
- Das Frontend pollt `GET /receipts` alle 2 s, solange ein Beleg `uploaded`/`processing` ist.
- Bei Fehlern (Netz, Rate-Limit, unlesbar) bleibt der Beleg mit Fehlermeldung erhalten; der Nutzer
  kann erneut extrahieren oder manuell erfassen.
- Erst `POST /receipts/{id}/confirm` legt eine Transaktion an – die KI bucht nie selbst.

## Skalierungspfad

| Heute (MVP) | Bei Wachstum |
|---|---|
| In-Memory-Rate-Limit | Redis-basiertes Limit (gleiches Interface) |
| BackgroundTasks im API-Prozess | Job-Queue (z. B. Redis + RQ/Celery, oder DB-basierte Queue) |
| Lokale Dateiablage | S3/MinIO über `Storage`-Interface |
| Ein API-Container | mehrere Replikas hinter Load-Balancer (stateless durch JWT + DB-Refresh-Tokens) |
| SQLite lokal | PostgreSQL (bereits vorgesehen), Read-Replica bei Bedarf |

Siehe auch die Architecture Decision Records unter [`adr/`](adr/).
