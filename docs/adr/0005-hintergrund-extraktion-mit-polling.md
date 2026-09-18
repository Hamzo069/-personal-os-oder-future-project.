# ADR 0005 – Belegextraktion als Hintergrundaufgabe mit Status-Polling

**Status:** akzeptiert · **Datum:** 2026-09-18

## Kontext
Ein Modellaufruf dauert Sekunden. Ein synchroner Upload würde die Verbindung blockieren und bei
Fehlern den Upload verlieren.

## Entscheidung
`POST /receipts` speichert die Datei, antwortet `202` und startet die Extraktion als FastAPI
`BackgroundTask` mit eigener DB-Session. Der Beleg trägt einen Status; das Frontend pollt alle
2 s, solange Belege in Bearbeitung sind. Fehlgeschlagene Extraktionen können erneut gestartet
oder manuell erfasst werden.

## Konsequenzen
- Einfach, ohne zusätzliche Infrastruktur – ausreichend für das MVP.
- Bei Prozessneustart bleiben Belege im Status `processing` hängen → Roadmap: Job-Queue mit
  Retry ([Issue #1](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/1)); ein Aufräum-Job für verwaiste Statusse ist die Zwischenlösung.
