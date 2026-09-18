# ADR 0002 – SQLite in Entwicklung/Tests, PostgreSQL in Produktion

**Status:** akzeptiert · **Datum:** 2026-09-18

## Kontext
Die Einstiegshürde soll minimal sein (kein Docker, kein Datenbankserver), Produktion braucht
jedoch Nebenläufigkeit, Backups und Managed-Hosting.

## Entscheidung
`DATABASE_URL` entscheidet. Modelle verwenden nur portable Typen (String(36)-UUIDs, Numeric,
DateTime(timezone=True), JSON). Alembic-Migrationen laufen mit `render_as_batch` auf SQLite.
Produktion verweigert SQLite.

## Konsequenzen
- Keine PostgreSQL-spezifischen Features (Arrays, JSONB-Operatoren, native UUID) im Modell.
- Monatsgruppierung erfolgt in Python statt per dialektspezifischem `date_trunc`.
- Tests laufen in Millisekunden ohne externen Dienst; ein Migrations-Test sichert die
  Schema-Parität.
