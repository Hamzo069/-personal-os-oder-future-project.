"""LedgerLens as a local desktop program.

One process starts the API on 127.0.0.1, serves the built web app from the same port and
shows it in a native window (Microsoft Edge WebView2 on Windows). All data stays in the
user's profile:

    %APPDATA%\\LedgerLens\\ledgerlens.db     the database (SQLite)
    %APPDATA%\\LedgerLens\\uploads\\          receipt files
    %APPDATA%\\LedgerLens\\config.env         optional settings, e.g. the Anthropic API key
    %APPDATA%\\LedgerLens\\ledgerlens.log     log file

Run it from a source checkout with `uv run python -m app.desktop`, or build the Windows
program as described in apps/desktop/README.md. `--headless` skips the window and only runs
the server, which is what CI uses to test the packaged program.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import secrets
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import MutableMapping, Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn

APP_NAME = "LedgerLens"
DEFAULT_PORT = 8765
HOST = "127.0.0.1"
WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"

CONFIG_TEMPLATE = """\
# LedgerLens settings. Save this file and restart LedgerLens for changes to take effect.
# Lines starting with # are ignored.

# Real receipt recognition with Claude. Costs a few cents per receipt.
# Without these two lines LedgerLens runs with a demo mode that fills in placeholder values.
# AI_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-your-key

# Use a PostgreSQL database such as Supabase instead of the local file.
# DATABASE_URL=postgresql+psycopg://user:password@host:5432/postgres?sslmode=require
"""

logger = logging.getLogger("ledgerlens.desktop")


# --- locations -----------------------------------------------------------------------------
def data_dir(environ: MutableMapping[str, str] | None = None) -> Path:
    environ = os.environ if environ is None else environ
    override = environ.get("LEDGERLENS_DATA_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        base = Path(environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / APP_NAME


def web_dist_dir() -> Path:
    """The built web app: unpacked next to the executable, or apps/web/dist in a checkout."""
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled) / "web_dist"
    return Path(__file__).resolve().parents[2] / "web" / "dist"


# --- configuration -------------------------------------------------------------------------
def read_config_file(path: Path) -> dict[str, str]:
    """KEY=VALUE pairs of config.env. utf-8-sig tolerates the BOM some editors add."""
    from dotenv import dotenv_values

    return {k: v for k, v in dotenv_values(path, encoding="utf-8-sig").items() if v is not None}


def load_or_create_secret(path: Path) -> str:
    """The key that signs access tokens. Generated once and kept, so logins survive restarts."""
    if path.is_file():
        value = path.read_text(encoding="ascii").strip()
        if len(value) >= 32:
            return value
    value = secrets.token_urlsafe(48)
    path.write_text(value, encoding="ascii")
    return value


def prepare_environment(
    data: Path, environ: MutableMapping[str, str] | None = None
) -> MutableMapping[str, str]:
    """Create the data folder and set every setting the API reads, before it is imported.

    Values from config.env win over the defaults below; variables already present in the
    process environment win over both.
    """
    environ = os.environ if environ is None else environ
    data.mkdir(parents=True, exist_ok=True)
    (data / "uploads").mkdir(exist_ok=True)

    config_path = data / "config.env"
    if not config_path.exists():
        config_path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    for key, value in read_config_file(config_path).items():
        environ.setdefault(key, value)

    defaults = {
        "APP_ENV": "desktop",
        "DATABASE_URL": f"sqlite:///{(data / 'ledgerlens.db').as_posix()}",
        "UPLOAD_DIR": str(data / "uploads"),
        "SECRET_KEY": load_or_create_secret(data / "secret.key"),
        "FRONTEND_DIST": str(web_dist_dir()),
        "LOG_LEVEL": "INFO",
    }
    for key, value in defaults.items():
        environ.setdefault(key, value)
    return environ


# --- runtime helpers -----------------------------------------------------------------------
def setup_logging(data: Path) -> None:
    """Log to a file. A windowed program has no console, so sys.stdout may be None."""
    data.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        data / "ledgerlens.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    if sys.stdout is None or sys.stderr is None:
        sink = open(data / "console.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or sink
        sys.stderr = sys.stderr or sink


def pick_port(preferred: int) -> int:
    """The preferred port if it is free, otherwise any free port."""
    for candidate in (preferred, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, candidate))
            except OSError:
                continue
            return int(sock.getsockname()[1])
    raise OSError("No free port available")


def wait_until_healthy(url: str, timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as response:  # noqa: S310
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.25)
    return False


def describe_error(exc: BaseException) -> str:
    """A readable message that never repeats setting values.

    Pydantic's own text for an invalid setting contains `input_value=...`, which can include
    an API key. It would end up in a dialog and in the log file, so it is built from the
    error messages only.
    """
    from pydantic import ValidationError

    if isinstance(exc, ValidationError):
        lines = []
        for err in exc.errors(include_input=False, include_url=False, include_context=False):
            where = ".".join(str(part) for part in err["loc"])
            message = err["msg"].removeprefix("Value error, ")
            lines.append(f"{where}: {message}" if where else message)
        return "\n".join(lines)
    return str(exc)


def show_error(message: str) -> None:
    logger.error(message)
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
    else:
        print(message, file=sys.stderr)


def build_server(port: int) -> uvicorn.Server:
    import uvicorn

    from app.main import app

    # Explicit implementations: uvicorn's "auto" lookups are string imports that a frozen
    # program cannot discover. log_config=None because there may be no console.
    config = uvicorn.Config(
        app, host=HOST, port=port, log_config=None, http="h11", ws="none", loop="asyncio"
    )
    return uvicorn.Server(config)


def self_check() -> int:
    """`--check`: confirm the window toolkit was packaged. Used by CI on Windows."""
    try:
        import webview

        if sys.platform == "win32":
            import webview.platforms.edgechromium  # noqa: F401
    except Exception:
        logger.exception("Window toolkit check failed")
        return 1
    logger.info("Window toolkit check passed")
    return 0


def run_window(url: str, data: Path) -> None:
    import webview

    webview.settings["ALLOW_DOWNLOADS"] = True  # CSV export
    webview.create_window(APP_NAME, url, width=1320, height=860, min_size=(900, 600))
    # Persistent profile, otherwise the login cookie is dropped whenever the window closes.
    # On Windows force Edge WebView2: the fallback engine is Internet Explorer.
    webview.start(
        gui="edgechromium" if sys.platform == "win32" else None,
        private_mode=False,
        storage_path=str(data / "webview"),
    )


# --- entry point ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--headless", action="store_true", help="run the server without a window")
    parser.add_argument("--check", action="store_true", help="verify the window toolkit and exit")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    data = data_dir()
    setup_logging(data)
    if args.check:
        return self_check()

    try:
        prepare_environment(data)
        port = pick_port(args.port)
        server = build_server(port)  # imports the API, which reads the environment
    except Exception as exc:
        from pydantic import ValidationError

        if isinstance(exc, ValidationError):
            logger.error("LedgerLens could not start: %s", describe_error(exc))
        else:
            logger.exception("LedgerLens could not start")
        show_error(
            f"LedgerLens could not start:\n\n{describe_error(exc)}\n\n"
            f"Settings: {data / 'config.env'}\nLog file: {data / 'ledgerlens.log'}"
        )
        return 1

    url = f"http://{HOST}:{port}"
    logger.info("Starting LedgerLens on %s, data in %s", url, data)

    if args.headless:
        with contextlib.suppress(KeyboardInterrupt):
            server.run()
        return 0

    thread = threading.Thread(target=server.run, name="ledgerlens-server", daemon=True)
    thread.start()
    if not wait_until_healthy(url):
        show_error(f"The LedgerLens server did not start.\nLog file: {data / 'ledgerlens.log'}")
        server.should_exit = True
        return 1
    try:
        run_window(url, data)
    except Exception as exc:
        logger.exception("The window could not be opened")
        show_error(
            f"The LedgerLens window could not be opened:\n\n{exc}\n\n"
            f"On Windows this needs the Microsoft Edge WebView2 runtime:\n{WEBVIEW2_URL}"
        )
        return 1
    finally:
        server.should_exit = True
        thread.join(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
