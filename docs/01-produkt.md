# 01 – Produktdefinition

## Vision

> LedgerLens macht aus einem Foto eines Kassenbons in Sekunden eine geprüfte, kategorisierte
> Buchung – und beantwortet Fragen zu den eigenen Ausgaben in natürlicher Sprache.

## Zielgruppe

| Segment | Situation | Schmerzpunkt |
|---|---|---|
| **Freelancer / Solo-Selbstständige** | 20–80 Belege im Monat, Umsatzsteuer-Voranmeldung | Belege sammeln sich, manuelle Erfassung kostet Stunden, Kategorien sind inkonsistent |
| **Kleinunternehmer (Kleinunternehmerregelung)** | wenige Belege, kein Steuerberater | wollen wissen, wohin das Geld geht, ohne Buchhaltungssoftware zu lernen |
| **Studierende / Werkstudenten** | private Ausgaben, Nebenjob, Studienkosten | wollen ein einfaches, kostenloses Tool mit Überblick |

Primärpersona für das MVP: **"Lena, 27, freiberufliche UX-Designerin"** – nutzt drei
SaaS-Abos, kauft Hardware, reist zu Kunden, muss quartalsweise USt melden und hasst Excel.

## Problem

1. Belege liegen als Foto, PDF-Anhang oder Papier herum – die Erfassung ist der Engpass.
2. Kategorisierung ist inkonsistent → Auswertungen sind wertlos.
3. Bestehende Tools sind entweder zu teuer/komplex (Buchhaltungssuiten) oder zu simpel
   (Tabellen).
4. "Wie viel habe ich letztes Quartal für Software ausgegeben?" erfordert Filter-Klicks statt einer
   Frage.

## Lösung (MVP-Umfang)

| Funktion | Beschreibung | Status |
|---|---|---|
| Konto & Login | E-Mail/Passwort, sichere Sessions, Konto-Löschung | ✅ |
| Belege hochladen | JPEG/PNG/WebP/PDF per Drag & Drop, bis 10 MB | ✅ |
| KI-Extraktion | Händler, Datum, Betrag, Währung, USt-Satz/-Betrag, Kategorie, Positionen, Konfidenz | ✅ |
| Review & Buchung | Vorschlag prüfen/korrigieren → Buchung anlegen (Human-in-the-loop) | ✅ |
| Lernschleife | Händler→Kategorie-Zuordnungen fließen in spätere Vorschläge | ✅ |
| Buchungen | manuell anlegen, bearbeiten, löschen, filtern, sortieren, CSV-Export | ✅ |
| Kategorien | Standardset + eigene Kategorien mit Farben | ✅ |
| Dashboard | Summe, Vergleich zur Vorperiode, USt, Monatsverlauf, Kategorien, Top-Händler | ✅ |
| Fragen in natürlicher Sprache | "Wie viel für Software im August?" → validierter Abfrageplan → Antwort | ✅ |
| KI-Kostenkontrolle | Token-Verbrauch pro Nutzer sichtbar | ✅ |
| Responsive UI | Desktop-Sidebar, mobile Navigation | ✅ |

## Nicht im MVP

Mehrbenutzer-/Team-Konten, Bank-Import, Rechnungserstellung, DATEV-Export, Wiederkehrende
Buchungen, Budgets/Warnungen, mehrsprachige UI, Mobile App. → siehe [Roadmap](09-roadmap.md).

## Erfolgskriterien für das MVP

- Ein Beleg ist in < 30 Sekunden vom Upload bis zur bestätigten Buchung erfasst.
- Kategorievorschlag trifft bei wiederkehrenden Händlern nach der ersten Korrektur zu 100 %.
- Die App läuft ohne API-Key (Mock) und ohne Docker lokal in < 5 Minuten (siehe README).
- Alle Kernflows sind automatisiert getestet (API-Tests, Unit-Tests, E2E-Smoke-Test).

## Geschäftsmodell (Ausblick)

| Stufe | Preis | Enthalten |
|---|---|---|
| Free | 0 € | 20 Belege/Monat, Mock- oder eigener API-Key |
| Solo | ~6 €/Monat | unbegrenzte Belege, KI inklusive, CSV/DATEV-Export |
| Team | ~15 €/Monat | mehrere Nutzer, Freigabe-Workflow, Steuerberater-Zugang |

Kostentreiber ist der KI-Aufruf pro Beleg (Cent-Bereich); der Rest skaliert nahezu kostenlos
(PostgreSQL, Objektspeicher, ein Container).
