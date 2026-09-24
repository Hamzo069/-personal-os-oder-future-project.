# 04 – Authentifizierung

## Ziele

- Kein Passwort im Klartext, keine Session-Tabelle für jeden Request, kein Token im
  `localStorage` (XSS-Schutz), Sitzungen serverseitig widerrufbar.

## Bausteine

| Baustein | Umsetzung | Datei |
|---|---|---|
| Passwort-Hash | **Argon2id** (`argon2-cffi`), automatisches Re-Hashing bei Parameteränderung | `core/security.py` |
| Access-Token | **JWT (HS256)**, 15 Minuten gültig, enthält nur `sub` (User-ID), `type=access`, `jti` | `core/security.py` |
| Refresh-Token | 48 Byte Zufall, als **SHA-256-Hash** in `refresh_tokens` gespeichert, 30 Tage | `services/auth_service.py` |
| Transport | Access-Token im JSON-Body → Frontend hält ihn **nur im Speicher**; Refresh-Token als **httpOnly, SameSite=Lax, Secure** Cookie, Pfad `/api/v1/auth` | `api/v1/auth.py` |
| Rotation | jeder Refresh macht das alte Token ungültig und gibt ein neues aus | `rotate_refresh_token` |
| Reuse-Erkennung | wird ein bereits rotiertes Token erneut benutzt (Diebstahlsignal), werden **alle** Tokens des Nutzers widerrufen | `rotate_refresh_token` |
| Rate-Limit | 10 Requests/Minute/IP auf `register`, `login`, `refresh` | `core/rate_limit.py` |
| Timing | bei unbekannter E-Mail wird trotzdem ein Argon2-Vergleich ausgeführt (kein User-Enumeration über Antwortzeit) | `authenticate` |

## Ablauf

```
Browser                                  API
  │  POST /auth/login {email, password}    │
  │ ───────────────────────────────────▶   │  Argon2-Verify, JWT erzeugen, Refresh-Token speichern (Hash)
  │  200 {access_token}  + Set-Cookie      │
  │ ◀───────────────────────────────────   │
  │  GET /transactions  Authorization: Bearer <jwt>
  │ ───────────────────────────────────▶   │  JWT prüfen (Signatur, Ablauf, type) → User laden
  │  …15 Minuten später: 401               │
  │ ◀───────────────────────────────────   │
  │  POST /auth/refresh  (Cookie automatisch)
  │ ───────────────────────────────────▶   │  Hash suchen, nicht widerrufen, nicht abgelaufen
  │  200 {access_token} + neues Cookie     │  → altes Token revoked_at setzen, neues ausstellen
  │ ◀───────────────────────────────────   │
  │  ursprünglichen Request wiederholen    │
```

Im Frontend passiert das transparent in `src/lib/api.ts`: bei 401 wird **einmal** ein Refresh
versucht; parallele Requests teilen sich denselben Refresh-Promise. Schlägt der Refresh fehl, wird
der `sessionExpired`-Handler ausgelöst, der den Nutzer ausloggt.

Beim Laden der App versucht `AuthProvider` zuerst still einen Refresh – so bleibt man nach einem
Reload eingeloggt, obwohl der Access-Token nur im Speicher lag.

## Warum nicht …?

- **… Session-Cookies für alles?** Möglich, aber ein stateless Access-Token skaliert horizontal
  ohne Session-Store und ist das Muster, das man in API-first-Systemen am häufigsten trifft.
- **… Access-Token im Cookie?** Dann bräuchte jeder Request CSRF-Schutz. Ein Bearer-Header in
  Kombination mit einem eng gescopten Refresh-Cookie (nur `/api/v1/auth`, SameSite=Lax) vermeidet
  CSRF für alle Datenendpunkte.
- **… OAuth/Social-Login?** Steht auf der Roadmap; die Token-Ausgabe ist bereits so gekapselt,
  dass ein weiterer Login-Weg nur `issue_*`-Funktionen wiederverwendet.

## Konto-Löschung

`DELETE /users/me` verlangt das Passwort erneut, löscht alle Dateien des Nutzers und den
Datensatz (Kaskade), löscht das Cookie und beendet damit alle Sitzungen.
