# 03 – Datenmodell

Alle Tabellen verwenden **UUIDs als String(36)** (portabel zwischen SQLite und PostgreSQL),
Zeitstempel mit Zeitzone und Geldbeträge als `Numeric(12, 2)`.

```
users 1 ──── n refresh_tokens
  │
  ├──── n categories 1 ──── n transactions n ──── 1 receipts (optional)
  │                 │
  │                 └──── n category_feedback
  │
  └──── n ai_calls
```

## Tabellen

### `users`
| Spalte | Typ | Bemerkung |
|---|---|---|
| id | String(36) PK | |
| email | String(255) unique | kleingeschrieben gespeichert |
| password_hash | String(255) | Argon2id |
| name | String(120) | |
| is_active | Boolean | Sperren ohne Löschen |
| default_currency | String(3) | ISO 4217, Standard `EUR` |
| created_at / updated_at | DateTime(tz) | |

### `refresh_tokens`
| Spalte | Typ | Bemerkung |
|---|---|---|
| user_id | FK users (CASCADE) | |
| token_hash | String(64) unique | SHA-256 des Tokens – der Klartext wird nie gespeichert |
| expires_at | DateTime(tz) | 30 Tage |
| revoked_at | DateTime(tz) null | gesetzt bei Rotation, Logout oder Missbrauchsverdacht |
| user_agent | String(255) | für spätere "aktive Sitzungen"-Ansicht |

### `categories`
| Spalte | Typ | Bemerkung |
|---|---|---|
| user_id | FK users (CASCADE) | jede*r Nutzer*in hat eigene Kategorien |
| name | String(80) | unique pro Nutzer (`uq_category_user_name`) |
| color | String(7) | Hex-Farbe, CVD-sichere Standardpalette |
| is_default | Boolean | beim Registrieren angelegt |

### `transactions`
| Spalte | Typ | Bemerkung |
|---|---|---|
| user_id | FK users (CASCADE) | Index `(user_id, date)` und `(user_id, category_id)` |
| category_id | FK categories (SET NULL) | Löschen einer Kategorie macht Buchungen "unkategorisiert" |
| receipt_id | FK receipts (SET NULL) | Herkunft, falls aus Beleg gebucht |
| date | Date | Belegdatum |
| merchant | String(200) | |
| description / notes | Text null | |
| amount | Numeric(12,2) | Bruttobetrag, > 0 |
| currency | String(3) | |
| vat_rate | Numeric(5,2) null | Prozent |
| vat_amount | Numeric(12,2) null | wird aus `vat_rate` abgeleitet, wenn nicht angegeben |
| source | String(20) | `manual` oder `receipt` |

### `receipts`
| Spalte | Typ | Bemerkung |
|---|---|---|
| original_filename | String(255) | nur zur Anzeige |
| storage_path | String(500) | `<user_id>/<uuid>.<ext>` – vom Server erzeugt |
| media_type | String(100) | aus Magic Bytes ermittelt |
| size_bytes | Integer | |
| status | String(20) | `uploaded → processing → extracted → confirmed` bzw. `failed` |
| extracted | JSON null | validierter Entwurf (Schema `ReceiptExtraction`) |
| confidence | Float null | 0..1 |
| error_message | Text null | |

### `category_feedback`  (Lernschleife)
| Spalte | Typ | Bemerkung |
|---|---|---|
| merchant_key | String(200) | normalisiert (kleingeschrieben, Whitespace reduziert), unique pro Nutzer |
| merchant_display | String(200) | Originalschreibweise für den Prompt |
| category_id | FK categories (CASCADE) | |
| times_confirmed | Integer | Sortierkriterium für die Hints im Prompt |

### `ai_calls`  (Audit & Kosten)
| Spalte | Typ | Bemerkung |
|---|---|---|
| kind | String(40) | `receipt_extraction` / `query_plan` |
| provider / model | String | z. B. `anthropic` / `claude-opus-5` |
| input_tokens / output_tokens | Integer | für Kostenschätzung |
| duration_ms | Integer | |
| success | Boolean | |

## Lösch- und Datenschutzkonzept

- Auf PostgreSQL ist Row Level Security für alle Tabellen eingeschaltet, ohne Policies. Nur der
  Besitzer, also die API, kann lesen und schreiben (siehe Migration `enable_row_level_security`).

- `DELETE /users/me` löscht den Nutzer; **alle** abhängigen Zeilen fallen per `ON DELETE CASCADE`,
  Dateien werden vom Storage entfernt.
- Beleg löschen entfernt Datei + Zeile; verknüpfte Buchungen bleiben (receipt_id → NULL).
- Es werden keine Rohantworten des KI-Modells gespeichert, nur das validierte Schema.

## Migrationen

```bash
cd apps/api
uv run alembic revision --autogenerate -m "beschreibung"   # nach Modell-Änderung
uv run alembic upgrade head
uv run alembic check                                       # Modell und DB synchron?
```

Beim Start prüft die API die Alembic-Revision (`app/core/migrations.py`). In der Entwicklung
führt sie fehlende Migrationen automatisch aus. In Produktion verweigert sie den Start mit einem
klaren Hinweis, weil Deployments `alembic upgrade head` ausdrücklich ausführen (siehe Dockerfile).

`tests/test_migrations.py` stellt sicher, dass die Migrationen exakt die Tabellen der Modelle
erzeugen.
