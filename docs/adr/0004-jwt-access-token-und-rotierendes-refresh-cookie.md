# ADR 0004 – Kurzlebige JWTs im Speicher + rotierendes httpOnly-Refresh-Cookie

**Status:** akzeptiert · **Datum:** 2026-09-18

## Kontext
Auth soll ohne externen Dienst funktionieren, XSS-robust sein, Sitzungen widerrufbar machen und
horizontal skalieren.

## Entscheidung
Access-Token = JWT (15 min), nur im Speicher des Frontends. Refresh-Token = zufälliger String,
gehasht in der DB, als httpOnly/SameSite=Lax-Cookie mit Pfad `/api/v1/auth`, rotierend mit
Reuse-Erkennung.

## Konsequenzen
- Datenendpunkte sind CSRF-frei (nur Bearer-Header).
- Frontend und API müssen same-origin sein oder das Cookie muss auf `SameSite=None` umgestellt
  werden (siehe Deployment-Doku). Der nginx-Proxy im Web-Container sorgt für same-origin.
- Nach einem Reload ist ein stiller Refresh nötig (implementiert im `AuthProvider`).
