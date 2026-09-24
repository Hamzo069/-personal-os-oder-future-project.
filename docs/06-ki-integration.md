# 06 – KI-Integration

## Grundsätze

1. **KI erzeugt Vorschläge, Code entscheidet.** Jede Modellantwort wird gegen ein Pydantic-Schema
   validiert und zusätzlich fachlich bereinigt (`_normalise`, `_validate_plan`), bevor sie in die
   Datenbank oder an den Nutzer geht.
2. **Human-in-the-loop.** Ein Beleg wird erst durch die Bestätigung des Nutzers zur Buchung.
3. **Keine Text-zu-SQL-Generierung.** Das Modell sieht nie die Datenbank und schreibt nie SQL.
4. **Austauschbar und offline lauffähig.** `AIProvider` ist ein Protokoll; der `MockProvider`
   macht die App ohne API-Key nutzbar und die Tests netzunabhängig.
5. **Kosten sichtbar.** Jeder Aufruf landet mit Token-Zahlen in `ai_calls`.

## Feature 1: Belegextraktion

```
Datei (JPEG/PNG/WebP/PDF)
   + Kategorienliste des Nutzers
   + Hints: "Rewe -> Food & Drinks" (aus category_feedback, sortiert nach Häufigkeit)
        │
        ▼  client.messages.parse(output_format=ReceiptExtraction)
ReceiptExtraction { merchant, date, total_amount, currency, vat_rate, vat_amount,
                    category, description, line_items[], confidence, notes }
        │
        ▼  _normalise(): Kategorie muss existieren, Datum ISO, Beträge positiv, Währung 3 Buchstaben
receipt.extracted (JSON) + receipt.status = "extracted"
```

- **Structured Outputs:** `client.messages.parse()` überträgt das JSON-Schema des Pydantic-Modells
  als `output_format`; der Provider erhält ein typisiertes Objekt oder eine Exception.
- **Bild vs. PDF:** Bilder werden als `image`-Block (base64), PDFs als `document`-Block gesendet.
- **Prompt-Caching:** der Systemprompt ist stabil und mit `cache_control: ephemeral` markiert; nur
  Kategorien/Hints/Dokument variieren pro Request.
- **Effort:** `ANTHROPIC_EFFORT` (`low|medium|high`) steuert, wie viel das Modell "nachdenkt" –
  Belege sind Routine, `medium` ist der Standard.
- **Lernschleife:** `POST /receipts/{id}/confirm` speichert `merchant_key → category_id` in
  `category_feedback` (Zähler `times_confirmed`). Die 30 häufigsten Zuordnungen wandern als
  Few-Shot-Hinweise in den nächsten Prompt. Effekt: wiederkehrende Händler werden nach der ersten
  Korrektur korrekt vorgeschlagen – ohne Training, ohne Vektor-DB.

## Feature 2: Fragen in natürlicher Sprache

```
"Wie viel habe ich im August für Software ausgegeben?"
        │  + Kategorienliste + heutiges Datum
        ▼  client.messages.parse(output_format=QueryPlan)
QueryPlan { intent: "sum", date_from: "2026-08-01", date_to: "2026-08-31",
            categories: ["Software & Subscriptions"], merchant_contains: null, ... }
        │
        ▼  _validate_plan(): nur eigene Kategorien, gültige Daten, Zeitraum sortiert
        ▼  execute_plan(): parametrisierte SQLAlchemy-Abfrage
        ▼  deterministischer Antwortsatz aus dem Ergebnis
"You spent 23.79 EUR between 2026-08-01 and 2026-08-31 in Software & Subscriptions across 1 expense(s)."
```

Warum ein Plan statt SQL?

| | Text-zu-SQL | Abfrageplan (LedgerLens) |
|---|---|---|
| Sicherheit | Injection- und Datenabfluss-Risiko, komplexes Allow-Listing nötig | Modell kann nur Felder setzen, die der Code kennt |
| Korrektheit | Zahlen kommen aus dem LLM-Text → Halluzinationsrisiko | Zahlen kommen aus der Datenbank |
| Kosten | Daten im Prompt (teuer, datenschutzkritisch) | nur Frage + Kategorienamen im Prompt |
| Erklärbarkeit | SQL für Nutzer schwer lesbar | `plan.explanation` + Filter werden angezeigt |

Unterstützte Intents: `sum`, `count`, `average`, `list`, `by_category`, `by_month`,
`top_merchants`.

## Provider-Interface

```python
class AIProvider(Protocol):
    name: str
    def extract_receipt(self, data: bytes, media_type: str, context: ExtractionContext) -> ExtractionResult: ...
    def plan_query(self, question: str, categories: list[str], today: date) -> QueryPlanResult: ...
```

| Provider | Datei | Wann |
|---|---|---|
| `AnthropicProvider` | `app/ai/anthropic_provider.py` | `AI_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` |
| `MockProvider` | `app/ai/mock_provider.py` | Standard; deterministische Extraktion, Keyword-Heuristiken für Fragen |

Ein weiterer Anbieter (OpenAI, lokales Modell via Ollama) ist eine neue Klasse mit denselben zwei
Methoden plus ein Eintrag in `app/ai/factory.py`.

## Fehlerbehandlung

| Situation | Verhalten |
|---|---|
| ungültiger API-Key | `AIServiceError("AI provider rejected the API key")` → Beleg `failed`, Meldung im UI |
| Rate-Limit des Anbieters | Beleg `failed` mit Hinweis, Nutzer kann "Retry" klicken |
| Netzwerkfehler | SDK versucht 2 Retries, danach `failed` |
| `stop_reason == "refusal"` | Beleg `failed` ("declined to process") |
| Antwort abgeschnitten (`max_tokens`) | `failed` mit "please retry" |
| Modell nennt unbekannte Kategorie | `_normalise` setzt Kategorie auf `null` (Nutzer wählt) |

## Kosten (Größenordnung)

Ein Bon als Foto entspricht ca. 1.500–2.500 Input-Tokens, die Antwort ca. 200–400 Tokens. Mit
`claude-opus-5` (5 $/25 $ pro Mio. Tokens) kostet eine Extraktion also etwa **1–2 Cent**; mit
`claude-sonnet-5` unter einem Cent. Prompt-Caching senkt die Kosten des Systemprompts weiter.
Die Zahlen pro Nutzer sind unter *Settings → AI usage* sichtbar.

## Datenschutz

- Belege werden nur an den konfigurierten Anbieter gesendet, wenn `AI_PROVIDER=anthropic` gesetzt
  ist. Es werden keine weiteren Nutzerdaten (Name, E-Mail, andere Buchungen) übertragen.
- Für die NL-Abfrage verlassen **nur** die Frage und die Kategorienamen den Server.
- Rohantworten des Modells werden nicht gespeichert.
- Hinweis für den Betrieb in der EU: Auftragsverarbeitungsvertrag mit dem Anbieter abschließen
  und Nutzer in der Datenschutzerklärung informieren.
