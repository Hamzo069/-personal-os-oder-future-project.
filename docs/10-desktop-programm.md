# 10 – Windows-Programm

LedgerLens gibt es als normales Windows-Programm mit eigenem Fenster. Du installierst es mit
einem Doppelklick und startest es über das Startmenü. Python, Node, PowerShell und Docker
brauchst du nicht. Alle Daten bleiben auf deinem PC.

## Installieren

1. Öffne auf GitHub den Bereich **Releases** des Repositorys und lade
   `LedgerLens-Setup-<version>.exe` herunter. Eine tragbare Version ohne Installation liegt
   als `LedgerLens-portable-<version>.zip` daneben.
2. Starte die Datei. Windows zeigt dabei meist **„Der Computer wurde durch Windows geschützt“**,
   weil das Programm nicht digital signiert ist. Klicke auf **Weitere Informationen** und dann
   auf **Trotzdem ausführen**. Eine Signatur kostet Geld und ist für ein privates Projekt
   unüblich.
3. Folge dem Installationsfenster. Es braucht keine Administratorrechte und installiert nur für
   dein Benutzerkonto.
4. Starte **LedgerLens** über das Startmenü oder das Desktop-Symbol und lege ein Konto an. Das
   Konto gilt nur auf diesem PC.

Das Fenster nutzt die Edge-WebView2-Komponente. Sie ist bei aktuellen Windows-10- und
Windows-11-Systemen vorhanden. Fehlt sie, zeigt LedgerLens eine Meldung mit dem Download-Link
unter https://developer.microsoft.com/microsoft-edge/webview2/.

## Wo liegen meine Daten?

Im Ordner `%APPDATA%\LedgerLens`. Öffne ihn mit **Windows-Taste + R**, dann
`%APPDATA%\LedgerLens` eingeben und Enter drücken.

| Datei | Inhalt |
|---|---|
| `ledgerlens.db` | Konten, Buchungen, Kategorien |
| `uploads\` | hochgeladene Belege |
| `config.env` | Einstellungen, zum Beispiel der API-Schlüssel |
| `ledgerlens.log` | Protokoll, hilft bei Fehlern |
| `secret.key` | Schlüssel für die Anmeldung, nicht weitergeben |

**Backup:** Kopiere den ganzen Ordner. Zum Wiederherstellen legst du ihn zurück.
**Deinstallieren:** Einstellungen, Apps, LedgerLens. Dein Datenordner bleibt dabei erhalten
und kann von Hand gelöscht werden.
**Update:** Installiere die neue Version einfach über die alte. Die Daten bleiben erhalten.

## Echte Belegerkennung einschalten

Ohne Schlüssel läuft ein Demo-Modus, der Belege mit Platzhalterwerten vorausfüllt.

1. Öffne den Datenordner und danach die Datei `config.env` mit dem Editor.
2. Entferne in diesen beiden Zeilen das `#` am Anfang und trage deinen Schlüssel ein:

   ```
   AI_PROVIDER=anthropic
   ANTHROPIC_API_KEY=sk-ant-dein-schluessel
   ```
3. Speichere die Datei, schließe LedgerLens und starte es neu.

Den Schlüssel erstellst du unter https://console.anthropic.com. Ein Beleg kostet etwa ein bis
zwei Cent. Ist die Datei fehlerhaft, zeigt LedgerLens beim Start eine Meldung mit dem Grund.

## Datenbank in Supabase statt lokal

Trage in `config.env` die Zeile `DATABASE_URL=...` ein, wie in
[08 – Deployment](08-deployment.md#supabase-als-datenbank) beschrieben. Das Programm
verwendet dann die Datenbank in der Cloud. Belege bleiben weiter auf deinem PC.

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| Meldung „LedgerLens could not start“ | Die Meldung nennt den Grund, meist ein Fehler in `config.env`. Details in `ledgerlens.log`. |
| Meldung zu WebView2 | WebView2-Runtime von der oben genannten Seite installieren. |
| Fenster bleibt weiß | Programm schließen, neu starten. Danach `ledgerlens.log` ansehen. |
| Port 8765 ist belegt | Kein Problem, LedgerLens wählt automatisch einen anderen Port. |

## Wie funktioniert das?

Das Programm startet die API auf `127.0.0.1`, also nur auf deinem PC, und liefert die
Weboberfläche über denselben Port aus. Das Fenster zeigt diese Seite an. Fremde Host-Header
weist der Server ab, damit eine geöffnete Webseite ihn nicht über DNS-Rebinding ansprechen kann.
Andere Programme desselben Windows-Benutzers können den Port erreichen, ein Zugriff auf
Daten braucht aber weiterhin eine Anmeldung. Die Entscheidung dazu steht in
[ADR 0006](adr/0006-desktop-programm-mit-eingebettetem-server.md).

## Neue Version veröffentlichen

1. Auf GitHub unter **Releases** auf **Draft a new release** klicken.
2. Einen neuen Tag wie `v0.1.0` anlegen und **Publish release** wählen.
3. Der Workflow „Desktop (Windows)“ baut Programm und Installer und hängt sie nach etwa zehn
   Minuten an das Release.

Jeder Push baut die Dateien ebenfalls und legt sie als Artefakt **LedgerLens-Windows** unter
**Actions** ab. Dort sind sie nur mit GitHub-Anmeldung erreichbar.

## Selbst bauen (Entwickler)

Siehe [`apps/desktop/README.md`](../apps/desktop/README.md).
