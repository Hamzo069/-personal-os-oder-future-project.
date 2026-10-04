# ADR 0006 – Windows-Programm mit eingebettetem Server und WebView2-Fenster

**Status:** akzeptiert · **Datum:** 2026-10-04

## Kontext
LedgerLens soll sich wie ein normales PC-Programm installieren und starten lassen, ohne
Python, Node, Docker oder PowerShell. Die vorhandene Architektur besteht aus einer FastAPI-API
und einer React-Oberfläche.

## Entscheidung
Ein Prozess startet die API auf `127.0.0.1`, liefert die gebaute Oberfläche über denselben Port
aus (`FRONTEND_DIST`) und zeigt sie in einem pywebview-Fenster, das unter Windows Edge WebView2
nutzt. PyInstaller friert alles zu einem Ordner ein, Inno Setup baut daraus den Installer. Die
Daten liegen in SQLite unter `%APPDATA%\LedgerLens`. Der Server akzeptiert nur Host-Header
`127.0.0.1` und `localhost`.

## Begründung
- Wiederverwendung: dieselbe API, dieselbe Oberfläche, dieselben Tests. Es gibt keinen zweiten
  Codepfad für das Programm, nur eine andere Umgebung (`APP_ENV=desktop`).
- Klein: etwa 90 MB statt über 200 MB bei Electron, weil WebView2 zu Windows gehört.
- Ein Port und ein Ursprung für Oberfläche und API, deshalb funktionieren das Refresh-Cookie und
  die Rate-Limits ohne Zusatzkonfiguration.

## Alternativen
- **Electron** mit Python-Prozess nebenher: größer, zwei Laufzeiten, mehr Verpackungsaufwand.
- **Tauri**: klein, aber die Rust-Toolchain und ein Sidecar-Prozess für Python kommen dazu.
- **Nur Start-Skript mit Browser-Tab**: kein eigenes Fenster, kein sauberes Beenden.

## Konsequenzen
- Voraussetzung ist die WebView2-Runtime. Fehlt sie, zeigt das Programm eine Meldung mit Link.
- Das Programm ist nicht signiert, SmartScreen warnt beim ersten Start.
- Der Windows-Build läuft ausschließlich in CI auf einem Windows-Runner. Dort werden
  Fenster-Paket, Server-Ablauf und Installer getestet. Zusätzlich startet CI das Programm mit
  Fenster, liest den Fenstertitel aus und legt ein Bildschirmfoto ab. Dieser Schritt darf
  fehlschlagen, ohne den Build zu stoppen, weil er einen interaktiven Desktop auf dem Runner
  voraussetzt. Der Inhalt des Fensters und der CSV-Export darin werden nicht automatisiert geprüft.
- Mehrere Konten auf einem PC sind möglich, die Datenbank gehört aber dem Windows-Benutzer.
