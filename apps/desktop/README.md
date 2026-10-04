# LedgerLens desktop program

Packaging for the Windows program: a PyInstaller recipe, an Inno Setup installer script and the
icon. The program itself is `apps/api/app/desktop.py`. It starts the API on `127.0.0.1`, serves
the built web app from the same port and opens it in a native window (pywebview, which uses
Microsoft Edge WebView2 on Windows). User documentation is in
[`docs/10-desktop-programm.md`](../../docs/10-desktop-programm.md).

| File | Purpose |
|---|---|
| `entry.py` | executable entry point that PyInstaller freezes |
| `ledgerlens.spec` | PyInstaller recipe (data files, hidden imports, icon) |
| `installer.iss` | Inno Setup script that builds `LedgerLens-Setup-<version>.exe` |
| `ledgerlens.ico` | program icon, rendered from `apps/web/public/favicon.svg` |

## Run from source

```powershell
cd apps\web;  npm ci; npm run build          # the program serves apps/web/dist
cd ..\api;    uv sync --extra desktop
uv run python -m app.desktop                  # window; add --headless for the server only
```

## Build the program

```powershell
cd apps\web; npm ci; npm run build
cd ..\api;   uv sync --extra desktop
uv run pyinstaller ..\desktop\ledgerlens.spec --noconfirm --distpath ..\desktop\dist --workpath ..\desktop\build
..\desktop\dist\LedgerLens\LedgerLens.exe
```

Build the installer with [Inno Setup 6](https://jrsoftware.org/isinfo.php):

```powershell
iscc /DAppVersion=0.1.0 apps\desktop\installer.iss    # -> apps\desktop\dist\LedgerLens-Setup-0.1.0.exe
```

CI does all of this on a Windows runner (`.github/workflows/desktop.yml`) and tests the result:
`LedgerLens.exe --check` proves the window toolkit was packaged, `--headless` plus
`deploy/smoke-test.sh` runs the whole product flow against the built program, and the installer is
installed silently, started and uninstalled again.

## Options

| Flag | Meaning |
|---|---|
| `--headless` | run the server without a window (used by CI) |
| `--check` | verify that the window toolkit is packaged, then exit |
| `--port N` | preferred port, default 8765; another free port is used if it is taken |

Environment: `LEDGERLENS_DATA_DIR` moves the data folder, which is useful for tests. Settings
in `<data folder>\config.env` use the same names as `.env.example`.

## Known limits

- The program is not code signed, so Windows SmartScreen warns on first start.
- The CSV export from inside the window relies on pywebview's download support. It has not been
  tried on a real desktop yet.
- A PostgreSQL `DATABASE_URL` in `config.env` is supported by the code, but the packaged
  program was not tested against a real server.
