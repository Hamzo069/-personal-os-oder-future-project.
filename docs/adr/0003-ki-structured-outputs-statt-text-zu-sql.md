# ADR 0003 – KI liefert validierte Strukturen, nie SQL und nie Buchungen

**Status:** akzeptiert · **Datum:** 2026-09-18

## Kontext
Zwei KI-Funktionen: Belegextraktion und Fragen in natürlicher Sprache. Beide könnten "einfach"
per Chat gelöst werden – mit Risiken für Korrektheit, Sicherheit und Kosten.

## Entscheidung
1. Das Modell antwortet ausschließlich über Structured Outputs in Pydantic-Schemas
   (`ReceiptExtraction`, `QueryPlan`).
2. Die Anwendung validiert und normalisiert jede Antwort erneut.
3. Fragen werden in einen deklarativen Abfrageplan übersetzt, den die Anwendung per ORM ausführt;
   die Antwort wird deterministisch aus dem Ergebnis formuliert.
4. Buchungen entstehen nur durch explizite Bestätigung des Nutzers.
5. Ein Provider-Interface mit Mock-Implementierung hält App und Tests unabhängig vom Anbieter.

## Konsequenzen
- Weniger "magisch", aber erklärbar, testbar und günstig (keine Daten im Prompt).
- Neue Auswertungen erfordern einen neuen Intent im Plan + Executor (bewusste Grenze).
