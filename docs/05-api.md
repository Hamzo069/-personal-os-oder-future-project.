# 05 – API-Referenz

Basis-URL: `/api/v1`. Interaktive Dokumentation (Swagger UI) im Development unter
`http://localhost:8000/docs` – in Produktion ist sie deaktiviert.

## Konventionen

- **Auth:** alle Endpunkte außer `auth/*` und `/health` erwarten `Authorization: Bearer <jwt>`.
- **Fehler** haben immer dieselbe Form:
  ```json
  { "error": { "code": "not_found", "message": "Transaction not found", "details": null } }
  ```
  Codes: `validation_error` (422), `unauthorized` (401), `forbidden` (403), `not_found` (404),
  `conflict` (409), `rate_limited` (429, `details.retry_after`), `ai_service_error` (502),
  `internal_error` (500).
- **Geld** wird als String mit zwei Nachkommastellen übertragen (`"12.34"`), nie als Float.
- **Daten** als ISO 8601 (`2026-09-18`).
- **Pagination:** `page` (ab 1), `page_size` (1–200); Antwort `{items, total, page, page_size}`.

## Endpunkte

### Auth
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/auth/register` | `{email, password, name}` → `201 {access_token, expires_in}` + Refresh-Cookie |
| POST | `/auth/login` | `{email, password}` → `200 {access_token, expires_in}` + Refresh-Cookie |
| POST | `/auth/refresh` | Cookie → neues Access-Token, Cookie rotiert |
| POST | `/auth/logout` | widerruft das Refresh-Token, löscht das Cookie |
| GET | `/auth/me` | aktueller Nutzer |

### Users
| Methode | Pfad | Beschreibung |
|---|---|---|
| PATCH | `/users/me` | `{name?, default_currency?}` |
| DELETE | `/users/me` | `{password}` → `204`, löscht alle Daten und Dateien |

### Categories
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/categories` | Liste (alphabetisch) |
| POST | `/categories` | `{name, color?}` → `201` |
| PATCH | `/categories/{id}` | `{name?, color?}` |
| DELETE | `/categories/{id}` | `204`; Buchungen werden unkategorisiert |

### Transactions
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/transactions` | Filter: `date_from, date_to, category_id, q, min_amount, max_amount, source, sort (date_desc\|date_asc\|amount_desc\|amount_asc), page, page_size` |
| GET | `/transactions/export` | CSV (`;`-getrennt, UTF-8 mit BOM), gleiche Filter |
| POST | `/transactions` | `TransactionCreate` → `201` |
| GET | `/transactions/{id}` | |
| PATCH | `/transactions/{id}` | Teil-Update |
| DELETE | `/transactions/{id}` | `204` |

`TransactionCreate`:
```json
{
  "date": "2026-09-12", "merchant": "Bäckerei Müller", "amount": "4.80", "currency": "EUR",
  "vat_rate": "7", "vat_amount": null, "category_id": "…", "description": null, "notes": null
}
```
Fehlt `vat_amount`, wird es aus `vat_rate` berechnet.

### Receipts
| Methode | Pfad | Beschreibung |
|---|---|---|
| POST | `/receipts` | `multipart/form-data` mit `file` → `202` Beleg (Status `uploaded`), Extraktion läuft im Hintergrund |
| GET | `/receipts` | Liste, optional `?status=extracted` |
| GET | `/receipts/{id}` | inkl. `extracted` und `suggested_category_id` |
| GET | `/receipts/{id}/file` | Originaldatei (inline) |
| POST | `/receipts/{id}/extract` | Extraktion erneut anstoßen (`202`) |
| POST | `/receipts/{id}/confirm` | `TransactionCreate` → `{receipt, transaction_id}`; speichert Händler→Kategorie-Feedback |
| DELETE | `/receipts/{id}` | `204`, löscht Datei |

Statusübergänge: `uploaded → processing → extracted → confirmed`, bei Fehler `failed`
(erneut extrahieren oder manuell buchen möglich).

### Insights & AI
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/insights/summary` | `date_from`, `date_to` (Standard: letzte 6 Monate) → Summen, Vorperiode, Kategorien, Monate, Top-Händler, offene Belege |
| POST | `/ai/query` | `{question}` → `{answer, plan, result}` |
| GET | `/ai/usage` | Anzahl Aufrufe und Tokens pro Nutzer |

### Meta
| Methode | Pfad | Beschreibung |
|---|---|---|
| GET | `/health` | `{status, version}` |

## Beispiel mit curl

```bash
TOKEN=$(curl -s -c cookies.txt -X POST localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"lena@example.com","password":"correct-horse-battery-9","name":"Lena"}' | jq -r .access_token)

curl -s localhost:8000/api/v1/categories -H "Authorization: Bearer $TOKEN" | jq '.[0]'

curl -s -X POST localhost:8000/api/v1/receipts -H "Authorization: Bearer $TOKEN" \
  -F file=@bon.jpg | jq .status          # "uploaded"

curl -s -X POST localhost:8000/api/v1/ai/query -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"question":"How much did I spend this month?"}' | jq .answer
```
