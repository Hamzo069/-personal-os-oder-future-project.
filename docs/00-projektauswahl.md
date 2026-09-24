# 00 – Projektauswahl und Entscheidung

> Ziel dieses Dokuments: nachvollziehbar machen, **warum** LedgerLens gebaut wurde und welche
> Alternativen verworfen wurden. Die Kriterien stammen aus der Aufgabenstellung
> (Lernwert, Portfolio-Wert, technische Tiefe, wirtschaftliches Potenzial, langfristiger Nutzen,
> Erweiterbarkeit, Aufwand, Differenzierung).

## 1. Was Arbeitgeber und Hochschulen aktuell sehen wollen

Aus Stellenausschreibungen für Werkstudenten-/Praktikumsstellen im Bereich
Wirtschaftsinformatik / Software Engineering (Stand 2026) lassen sich wiederkehrende Anforderungen
ableleiten:

| Kompetenz | Typische Formulierung in Ausschreibungen | Wie ein Portfolio-Projekt sie zeigt |
|---|---|---|
| Full-Stack-Entwicklung | "REST-APIs mit Python/TypeScript", "React" | getrennte Frontend-/Backend-Codebasis mit klarer API |
| Datenmodellierung & SQL | "relationale Datenbanken, Migrationen" | normalisiertes Schema, Migrations-Tooling |
| KI-Integration | "LLM-APIs sinnvoll einsetzen", "Structured Outputs" | KI als Baustein im Prozess, nicht als Chat-Fenster |
| Security & Datenschutz | "Auth, DSGVO-Bewusstsein" | Auth-Flow, Threat Model, Löschkonzept |
| Software-Qualität | "Tests, CI/CD, Code Reviews" | Test-Suite, GitHub Actions, Lint/Typecheck |
| Betriebswirtschaftlicher Bezug | "Prozesse digitalisieren", "Rechnungswesen" | fachliche Domäne mit echten Geschäftsregeln (USt, Belege) |
| Produktdenken | "Anforderungen verstehen", "MVP" | Produktdefinition, Zielgruppe, Roadmap |

Projekte, die nur ein Chat-Interface um ein LLM legen, sind 2026 austauschbar. Differenzierend sind
Projekte, in denen **KI einen fachlichen Prozess beschleunigt**, das Ergebnis **validiert und
nachvollziehbar** bleibt und ein **Mensch die Kontrolle behält** (Human-in-the-loop).

## 2. Kandidaten

| # | Projekt | Kurzbeschreibung |
|---|---|---|
| A | **Belegerfassung & Ausgabenanalyse (LedgerLens)** | Belege fotografieren/hochladen, KI extrahiert strukturierte Daten, Nutzer bestätigt, Dashboard + natürliche Sprache über eigene Daten |
| B | Bewerbungs-Tracker mit KI-Matching | Stellenanzeigen speichern, Skills vergleichen, Lücken aufzeigen |
| C | Persönliche Wissensdatenbank mit RAG | Notizen/PDFs, semantische Suche, Fragen an die eigenen Dokumente |
| D | Kundenfeedback-Analyse (Review Mining) | Reviews importieren, Themen clustern, Sentiment-Dashboard |
| E | Lern-OS mit KI-Karteikarten | Vorlesungs-PDFs → Karteikarten, Spaced Repetition, Lernstatistik |

## 3. Bewertung (1 = schwach, 5 = stark)

| Kriterium | A LedgerLens | B Bewerbungen | C RAG-Wissen | D Feedback | E Lern-OS |
|---|:-:|:-:|:-:|:-:|:-:|
| Lernwert (Breite des Stacks) | **5** | 3 | 4 | 4 | 4 |
| Portfolio-Wert für WI-Stellen | **5** | 3 | 3 | 4 | 3 |
| Technische Tiefe | 4 | 2 | **5** | 4 | 3 |
| Wirtschaftliches Potenzial (SaaS) | **5** | 2 | 2 | 4 | 3 |
| Langfristiger Eigennutzen | **5** | 3 | 4 | 1 | 4 |
| Erweiterbarkeit | **5** | 3 | 4 | 4 | 4 |
| Aufwand für ein MVP (5 = gering) | 3 | **5** | 3 | 3 | 3 |
| Differenzierung | 4 | 2 | 1 | 3 | 3 |
| **Summe** | **36** | 23 | 26 | 27 | 27 |

Begründung der wichtigsten Wertungen:

- **A** verbindet Rechnungswesen (Kern der Wirtschaftsinformatik), einen echten Geschäftsprozess
  (Beleg → Buchung → Auswertung) und einen sinnvollen KI-Einsatz (Dokumentenextraktion mit
  Structured Outputs, Lernschleife aus Nutzerkorrekturen, Planung von Abfragen statt Text-zu-SQL).
  Der Eigennutzen ist dauerhaft: Ausgaben fallen jeden Monat an, auch als Student.
- **C** ist technisch am tiefsten (Embeddings, Vektorsuche, Chunking), aber der Markt ist mit
  Notion AI, Obsidian-Plugins usw. gesättigt; die Differenzierung ist minimal.
- **D** ist gut für B2B, aber es fehlen eigene Daten – das Projekt bleibt eine Demo.
- **B** ist schnell gebaut, zeigt aber vor allem CRUD.

## 4. Entscheidung

**LedgerLens** – AI-gestützte Belegerfassung und Ausgabenanalyse für Freelancer, Kleinunternehmer
und Studierende.

Was das Projekt gegenüber Standardlösungen abgrenzt:

1. **KI als Prozessschritt, nicht als Chat:** Structured Outputs erzwingen ein Schema, die
   Anwendung validiert jeden Wert erneut, und **nichts wird gebucht, bevor der Nutzer bestätigt**.
2. **Lernschleife:** bestätigte Zuordnungen (Händler → Kategorie) fließen als Few-Shot-Beispiele in
   spätere Extraktionen ein – die Vorschläge werden besser, ohne ein Modell zu trainieren.
3. **Natürliche Sprache ohne Text-zu-SQL:** das Modell erzeugt nur einen validierten Abfrageplan;
   SQL schreibt ausschließlich die Anwendung. Das ist sicher, günstig und erklärbar.
4. **Kostenbewusstsein:** jeder Modellaufruf wird mit Token-Verbrauch protokolliert; ohne API-Key
   läuft die App mit einem Mock-Provider vollständig lokal.
5. **Datenschutz von Anfang an:** lokale Dateiablage, Löschkonzept (Account-Löschung entfernt alle
   Daten und Dateien), keine Weitergabe von Daten außer an den konfigurierten KI-Anbieter.

## 5. Bewusst ausgeklammert (siehe Roadmap)

Banking-Anbindung (PSD2/FinTS), Rechnungs*erstellung*, Mandantenfähigkeit, mobile App,
Vektor-Suche über Belege. Alles sinnvolle Erweiterungen – aber nicht für ein MVP an einem Tag.
