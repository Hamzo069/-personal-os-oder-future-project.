# 07 – Security Review

Stand: MVP (September 2026). Methode: Threat-Modelling entlang der Datenflüsse, Code-Review der
Schichten, automatisierte Tests für die sicherheitsrelevanten Pfade.

## Assets und Angreifermodell

| Asset | Schutzbedarf |
|---|---|
| Passwörter | sehr hoch – Wiederverwendung auf anderen Diensten wahrscheinlich |
| Belege (Fotos/PDFs) | hoch – enthalten Namen, Adressen, teils Zahlungsdaten |
| Buchungsdaten | hoch – finanzielle Privatsphäre |
| API-Key des KI-Anbieters | hoch – Missbrauch verursacht Kosten |

Angreifer: anonyme Internetnutzer, andere registrierte Nutzer (horizontale Rechteausweitung),
XSS-Payloads in Nutzereingaben, manipulierte Uploads.

## Maßnahmen (umgesetzt)

| Bereich | Maßnahme | Nachweis |
|---|---|---|
| Passwörter | Argon2id; Mindestlänge 10, Buchstaben + Ziffern/Symbole; Re-Hash bei Parameteränderung | `core/security.py`, `test_register_rejects_weak_passwords` |
| Sitzungen | JWT 15 min; Refresh-Token gehasht, rotierend, widerrufbar; Reuse-Erkennung widerruft alle Tokens | `test_refresh_rotates_token_and_detects_reuse` |
| Cookies | `httpOnly`, `SameSite=Lax`, `Secure` in Produktion, Pfad auf `/api/v1/auth` begrenzt | `api/v1/auth.py`, `test_register_returns_token_and_sets_refresh_cookie` |
| CSRF | Datenendpunkte akzeptieren nur Bearer-Header (kein Cookie) → kein CSRF-Vektor; Refresh-Cookie kann nur ein neues Access-Token erzeugen, das der Angreifer nicht lesen kann | Design |
| XSS | Access-Token nur im Speicher; React escaped Ausgaben; keine `dangerouslySetInnerHTML` | Frontend |
| Autorisierung | jede Abfrage user-scoped; fremde IDs → 404 | `test_*_are_isolated_per_user` (Kategorien, Buchungen, Belege) |
| Brute Force | Rate-Limit 10/min/IP auf Auth, 20/min/Nutzer auf KI-Endpunkte | `test_auth_rate_limit`, `test_ai_rate_limit_applies_to_uploads` |
| User Enumeration | identische Fehlermeldung + Argon2-Dummy-Vergleich bei unbekannter E-Mail | `authenticate()` |
| Uploads | Typ per Magic Bytes (nicht Header/Endung), max. 10 MB (Lesen bricht bei Limit+1 ab), servergenerierte Dateinamen, Pfad-Traversal-Check im Storage | `test_rejects_unsupported_and_oversized_files` |
| Datei-Auslieferung | `X-Content-Type-Options: nosniff`, `Content-Disposition: inline` mit ID statt Originalname, private Cache-Control | `get_receipt_file` |
| Injection | ausschließlich ORM mit Parametern; LLM erzeugt nie SQL | `ai_service.execute_plan` |
| KI-Output | Pydantic-Schema + Normalisierung; unbekannte Kategorien verworfen; Datumsformate geprüft | `test_validate_plan_sanitises_model_output`, `test_normalise_extraction_cleans_model_output` |
| Prompt Injection | Dokumentinhalte können den Prompt beeinflussen, aber die Antwort ist auf das Schema beschränkt und wird nie ausgeführt; der Nutzer bestätigt jeden Wert | Design |
| Secrets | keine im Code; `.env` in `.gitignore`; Produktion verweigert Start ohne `SECRET_KEY` ≥ 32 Zeichen und mit SQLite | `Settings.validate_for_environment` |
| HTTP-Header | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, HSTS in Produktion | `main.py`, `test_security_headers_present` |
| CORS | explizite Origin-Allowlist, Methoden- und Header-Allowlist | `main.py` |
| Fehler | einheitliche Hülle ohne Stacktraces; Validierungsdetails ohne interne Objekte | `core/errors.py` |
| Docs | Swagger/OpenAPI in Produktion abgeschaltet | `main.py` |
| Container | Non-Root-User, Multi-Stage-Build, keine Dev-Abhängigkeiten im Runtime-Image | `apps/api/Dockerfile` |
| Abhängigkeiten | Lockfiles (`uv.lock`, `package-lock.json`), Versionsbereiche mit Obergrenzen | – |
| Datenschutz | Konto-Löschung entfernt alle Daten und Dateien; Datenminimierung gegenüber dem KI-Anbieter | `test_delete_account_requires_password_and_removes_everything` |

## Während Entwicklung und Review aufgefallen und behoben

1. **Validierungsfehler enthielten nicht serialisierbare Objekte** (`ValueError` in den
   Pydantic-Details) → der Handler nutzt jetzt `jsonable_encoder`; vorher hätte eine ungültige
   Eingabe einen 500er ausgelöst.
2. **Standard-Kategoriefarben** waren für Menschen mit Farbfehlsichtigkeit nicht unterscheidbar
   (kein Security-, aber ein Accessibility-Befund) → CVD-sichere Palette, zusätzlich immer
   Textlabels neben Farben.
3. **Mehrdeutige Formularfelder** (Filter-Select und Dialog-Select hießen beide "Category") wurden
   im E2E-Test sichtbar → Test scoped auf den Dialog; im UI bleiben beide Felder per `aria-label`
   erreichbar.

## Bekannte Restrisiken / Empfehlungen (Roadmap)

| Risiko | Bewertung | Empfehlung |
|---|---|---|
| Rate-Limit ist prozesslokal | mittel bei mehreren Replikas | Redis-Store ([Issue #3](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/3)); zusätzlich Limits am Reverse-Proxy |
| Kein E-Mail-Verifizierungs-/Passwort-Reset-Flow | mittel | [Issue #4](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/4) |
| Keine Content-Security-Policy im SPA | niedrig (kein Inline-Script), aber empfehlenswert | CSP-Header in nginx setzen ([Issue #14](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/14)) |
| Uploads liegen unverschlüsselt auf Disk | niedrig–mittel | Verschlüsselung at rest (S3 SSE oder Dateisystem) |
| Refresh-Token-Diebstahl per XSS ausgeschlossen, per Malware nicht | inhärent | Gerätebindung/Sitzungsübersicht als Feature |
| Prompt Injection über Belegbilder | niedrig (Schema-Grenze, Human-in-the-loop) | Konfidenz-Schwelle + Warnhinweis im UI ausbauen |
| Abhängigkeits-Schwachstellen | laufend | Dependabot/`pip-audit`/`npm audit` in CI aktivieren ([Issue #13](https://github.com/Hamzo069/-personal-os-oder-future-project./issues/13)) |
| Kein Audit-Log für Logins | niedrig | `login_events`-Tabelle (IP, UA, Zeit) |

## Wie man das Review wiederholt

```bash
make check                          # Lint, Typen, Tests (inkl. Security-Tests)
cd apps/api && uv run pip-audit     # Python-Abhängigkeiten (optional installieren)
cd apps/web && npm audit --omit=dev # Frontend-Abhängigkeiten
```
