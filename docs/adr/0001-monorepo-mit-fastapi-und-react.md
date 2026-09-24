# ADR 0001 – Monorepo mit getrenntem FastAPI-Backend und React-Frontend

**Status:** akzeptiert · **Datum:** 2026-09-18

## Kontext
Das Projekt soll Full-Stack-Kompetenz zeigen, lernbar bleiben und langfristig zu einem SaaS
ausbaubar sein.

## Entscheidung
Ein Repository mit `apps/api` (Python/FastAPI) und `apps/web` (React/TypeScript), die über eine
versionierte JSON-API (`/api/v1`) kommunizieren.

## Begründung
- Zwei Sprachen decken die zwei größten Stellenmärkte (Python/KI und TypeScript/Web) ab.
- Klare Trennung macht die Kommunikation explizit (API-Vertrag) und ermöglicht getrenntes
  Deployment/Skalieren.
- Ein Repo hält Änderungen an Vertrag und Konsumenten in einem Commit/PR zusammen.

## Alternativen
- Next.js-Fullstack: weniger Sprachwechsel, aber Server-Rendering ist für eine App hinter Login
  unnötig und das KI-Ökosystem ist in Python reicher.
- Django + Templates: schnell, aber kein modernes SPA-Frontend im Portfolio.

## Konsequenzen
Zwei Toolchains (uv/pytest, npm/vitest), zwei CI-Jobs; Typen werden vorerst manuell gespiegelt
(Roadmap: Generierung aus OpenAPI).
