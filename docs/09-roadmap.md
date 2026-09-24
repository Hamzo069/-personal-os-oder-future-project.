# 09 – Roadmap (12 Monate)

Die Roadmap ist in Quartale gegliedert. Jede Position ist als GitHub-Issue angelegt (siehe
Verlinkung) und bewusst so geschnitten, dass sie in wenigen Tagen umsetzbar ist – ideal für
kontinuierliche Weiterentwicklung neben dem Studium.

## Q4 2026 – Produktionsreife & Qualität

| Thema | Warum | Issue |
|---|---|---|
| Job-Queue für die Belegextraktion | BackgroundTasks überleben keinen Prozess-Neustart; Retry/Backoff, Sichtbarkeit | [#1](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/1) |
| S3-kompatibler Storage | Voraussetzung für Managed Hosting und mehrere Replikas | [#2](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/2) |
| Redis-Rate-Limit | prozessübergreifend, sonst wirkungslos bei > 1 Instanz | [#3](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/3) |
| Abhängigkeits-Scans in CI | pip-audit, npm audit, Dependabot | [#13](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/13) |
| Content-Security-Policy | Defense in depth gegen XSS | [#14](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/14) |
| Extraktions-Evaluationsset | Prompt-Änderungen messbar machen (Golden Receipts) | [#15](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/15) |

## Q1 2027 – Vertrauen & Onboarding

| Thema | Warum | Issue |
|---|---|---|
| E-Mail-Verifizierung & Passwort-Reset | Pflicht für echte Nutzer | [#4](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/4) |
| Duplikat-Erkennung für Belege | doppelte Uploads sind der häufigste Datenfehler | [#12](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/12) |
| Deutsche UI (i18n) | Zielgruppe DACH | [#10](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/10) |
| API-Typen aus OpenAPI generieren | Vertrag zwischen Frontend und Backend automatisch synchron | [#9](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/9) |
| Dark Mode | häufigster UI-Wunsch, geringer Aufwand | [#16](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/16) |

## Q2 2027 – Fachliche Tiefe (Wirtschaftsinformatik-Kern)

| Thema | Warum | Issue |
|---|---|---|
| Budgets pro Kategorie mit Warnungen | vom Rückblick zur Steuerung | [#5](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/5) |
| Wiederkehrende Ausgaben erkennen | Abos sichtbar machen (Kündigungspotenzial) | [#6](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/6) |
| DATEV-/Steuerberater-Export | Anschluss an die reale Buchhaltung; USt-Voranmeldung vorbereiten | [#7](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/7) |
| Mehrwährungsfähigkeit | Reisen, internationale SaaS-Abos | [#8](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/8) |

## Q3 2027 – Wachstum & Produkt

| Thema | Warum | Issue |
|---|---|---|
| Bankumsatz-Import (CSV/CAMT) + Beleg-Matching | Vollständigkeitskontrolle: jeder Umsatz hat einen Beleg | [#11](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/11) |
| Team-Konten & Freigabe-Workflow | Weg zum bezahlten "Team"-Tarif | – |
| Öffentliche Demo mit Beispiel-Daten | Portfolio-Wirkung, Onboarding | – |
| Mobile PWA (Foto direkt aus der Kamera) | häufigster Erfassungsweg | – |

## Leitplanken für alle Erweiterungen

- Neue KI-Funktionen nur, wenn sie einen Prozessschritt sparen und validierbar sind.
- Jede Änderung am Datenmodell kommt mit Migration und Test.
- Erst messen (Evaluationsset, Nutzungsdaten), dann Prompts ändern.
- Kein Feature ohne Löschpfad (Datenschutz).
