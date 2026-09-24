# Lernpfad – wie man dieses Projekt liest

Dieses Dokument ist für dich als Entwickler*in gedacht, der/die das Projekt übernimmt und
gleichzeitig Softwareentwicklung lernen will. Die Reihenfolge ist so gewählt, dass jedes Kapitel
auf dem vorherigen aufbaut.

## Woche 1 – Das System zum Laufen bringen und verstehen

1. README → "Quick start" durchführen. Registriere dich, lade `apps/web/e2e/receipt.png` hoch,
   buche den Beleg, stelle eine Frage im Dashboard.
2. Öffne `http://localhost:8000/docs` und probiere dieselben Schritte als API-Aufrufe.
3. Lies [`02-architektur.md`](02-architektur.md) und finde für jeden Kasten im Diagramm die
   entsprechende Datei.

**Übung:** Füge in `insights_service.summary` das Feld `max_single_expense` hinzu (Schema,
Service, Test, Dashboard-Kachel). Du berührst damit alle Schichten einmal.

## Woche 2 – Backend-Grundlagen

| Thema | Lies | Dann |
|---|---|---|
| Konfiguration | `app/core/config.py` | Warum verweigert Produktion SQLite? Probiere `APP_ENV=production` ohne `SECRET_KEY`. |
| ORM & Migrationen | `app/models/`, `03-datenmodell.md` | Ergänze eine Spalte `payment_method` an `Transaction`, erzeuge die Migration, schreibe einen Test. |
| Validierung | `app/schemas/transaction.py` | Warum ist `amount` ein `Decimal` und kein `float`? Teste `0.1 + 0.2` in Python. |
| Services vs. Router | `app/services/transaction_service.py`, `app/api/v1/transactions.py` | Verschiebe testweise Logik in den Router – und spüre, warum das die Tests erschwert. |
| Tests | `tests/conftest.py`, `tests/test_transactions.py` | Schreibe einen Test für einen Filter, der noch nicht abgedeckt ist. |

## Woche 3 – Authentifizierung und Sicherheit

1. [`04-authentifizierung.md`](04-authentifizierung.md) lesen, dann `tests/test_auth.py` Schritt
   für Schritt im Debugger ausführen.
2. Setze den Access-Token auf 1 Minute und beobachte im Browser-Netzwerk-Tab den automatischen
   Refresh.
3. [`07-security-review.md`](07-security-review.md): wähle ein Restrisiko und setze die Empfehlung
   um (z. B. CSP-Header).

## Woche 4 – Frontend

| Thema | Lies | Dann |
|---|---|---|
| API-Client | `src/lib/api.ts`, `src/lib/api.test.ts` | Simuliere im Test einen 500er und prüfe, dass kein Refresh ausgelöst wird. |
| Server-State | `src/api/hooks.ts` | Warum invalidiert eine Buchung auch `summary`? Entferne es und beobachte das Dashboard. |
| Formulare | `src/components/TransactionForm.tsx` | Ergänze ein Feld `payment_method` (siehe Woche 2). |
| Routing & Auth | `src/App.tsx`, `src/components/ProtectedRoute.tsx` | Was passiert bei einem Reload auf `/receipts`? |
| Responsive UI | `src/components/Layout.tsx` | Öffne die DevTools im Mobilmodus und prüfe jede Seite. |

## Woche 5 – KI

1. [`06-ki-integration.md`](06-ki-integration.md) lesen. Vergleiche `MockProvider` und
   `AnthropicProvider`: gleiche Schnittstelle, andere Implementierung.
2. Hole dir einen API-Key, setze `AI_PROVIDER=anthropic`, lade einen echten Kassenbon hoch.
3. Ändere den Systemprompt (z. B. Trinkgeld separat ausweisen) und beobachte die Auswirkung.
4. **Übung:** Implementiere einen dritten Provider (z. B. für ein lokales Modell) – nur
   `extract_receipt` und `plan_query`.

## Woche 6 – Betrieb

1. [`08-deployment.md`](08-deployment.md): `docker compose up --build`, dann PostgreSQL statt
   SQLite im Alltag nutzen.
2. Lies `.github/workflows/ci.yml` und provoziere absichtlich einen roten Build (Lint-Fehler).
3. Wähle ein Issue aus der [Roadmap](09-roadmap.md) und setze es komplett um: Branch, Tests, PR,
   CI grün, Merge.

## Begriffe kurz erklärt

| Begriff | Bedeutung im Projekt |
|---|---|
| **REST-API** | HTTP-Endpunkte, die Ressourcen (Buchungen, Belege) über GET/POST/PATCH/DELETE bereitstellen; Antworten als JSON |
| **ORM** | Object-Relational Mapper: Python-Klassen (`Transaction`) statt SQL-Strings; SQLAlchemy erzeugt das SQL |
| **Migration** | versionierte Schema-Änderung (Alembic), damit alle Umgebungen dieselbe Datenbankstruktur haben |
| **JWT** | signierter Token, den der Server ohne Datenbankzugriff prüfen kann |
| **Refresh-Token** | langlebiger Schlüssel, um neue kurzlebige JWTs zu holen; serverseitig widerrufbar |
| **Structured Outputs** | das LLM muss ein vorgegebenes JSON-Schema einhalten |
| **Human-in-the-loop** | ein Mensch bestätigt Ergebnisse der KI, bevor sie Wirkung haben |
| **Query-Invalidation** | TanStack Query lädt nach einer Mutation die betroffenen Daten neu |
| **ADR** | Architecture Decision Record – kurze Begründung einer Architekturentscheidung (siehe `adr/`) |
