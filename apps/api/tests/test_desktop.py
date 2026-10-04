"""The desktop launcher: data folder, settings and the embedded server."""

from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest
from app import desktop
from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_data_dir_follows_the_platform_and_the_override(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    assert (
        desktop.data_dir({"LEDGERLENS_DATA_DIR": str(tmp_path / "custom")}) == tmp_path / "custom"
    )
    monkeypatch.setattr(desktop.sys, "platform", "win32")
    assert desktop.data_dir({"APPDATA": str(tmp_path)}) == tmp_path / "LedgerLens"
    monkeypatch.setattr(desktop.sys, "platform", "linux")
    assert desktop.data_dir({"XDG_DATA_HOME": str(tmp_path)}) == tmp_path / "LedgerLens"


def test_prepare_environment_sets_everything_the_api_reads(tmp_path: Path) -> None:
    data = tmp_path / "LedgerLens"
    env: dict[str, str] = {}
    desktop.prepare_environment(data, env)

    assert env["APP_ENV"] == "desktop"
    assert env["DATABASE_URL"] == f"sqlite:///{(data / 'ledgerlens.db').as_posix()}"
    assert env["UPLOAD_DIR"] == str(data / "uploads")
    assert len(env["SECRET_KEY"]) >= 32
    assert (data / "uploads").is_dir()
    assert "ANTHROPIC_API_KEY" in (data / "config.env").read_text()  # commented template


def test_secret_key_is_stable_across_starts(tmp_path: Path) -> None:
    first: dict[str, str] = {}
    second: dict[str, str] = {}
    desktop.prepare_environment(tmp_path, first)
    desktop.prepare_environment(tmp_path, second)
    assert first["SECRET_KEY"] == second["SECRET_KEY"]


def test_config_file_overrides_defaults_but_not_the_process_environment(tmp_path: Path) -> None:
    (tmp_path / "config.env").write_bytes(
        b"\xef\xbb\xbfAI_PROVIDER=anthropic\r\nANTHROPIC_API_KEY=sk-ant-test\r\nLOG_LEVEL=DEBUG\r\n"
    )  # UTF-8 with BOM and Windows line endings, as Notepad may write it
    env = {"LOG_LEVEL": "WARNING"}
    desktop.prepare_environment(tmp_path, env)

    assert env["AI_PROVIDER"] == "anthropic"
    assert env["ANTHROPIC_API_KEY"] == "sk-ant-test"
    assert env["LOG_LEVEL"] == "WARNING"  # already set in the process, so it wins


def test_pick_port_prefers_the_requested_port_and_falls_back() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        free = probe.getsockname()[1]
    assert desktop.pick_port(free) == free

    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy_port = busy.getsockname()[1]
        chosen = desktop.pick_port(busy_port)
    assert chosen not in (0, busy_port)


def test_wait_until_healthy_gives_up_on_a_closed_port() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    assert desktop.wait_until_healthy(f"http://127.0.0.1:{port}", timeout=0.5) is False


def test_embedded_server_starts_answers_and_stops() -> None:
    port = desktop.pick_port(0)
    server = desktop.build_server(port)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        assert desktop.wait_until_healthy(f"http://127.0.0.1:{port}", timeout=15)
    finally:
        server.should_exit = True
        thread.join(timeout=10)
    assert not thread.is_alive()


# --- serving the web app from the API process -----------------------------------------------
@pytest.fixture
def web_client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>LEDGERLENS-SPA</body></html>")
    (dist / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    settings = Settings(app_env="desktop", frontend_dist=dist)
    # No `with`: entering the client would run the start-up migration check on the test database.
    return TestClient(create_app(settings), base_url="http://127.0.0.1:8765")


def test_web_app_and_client_side_routes_are_served(web_client: TestClient) -> None:
    root = web_client.get("/")
    assert root.status_code == 200 and "LEDGERLENS-SPA" in root.text
    deep_link = web_client.get("/receipts")  # no such file: the React router handles it
    assert deep_link.status_code == 200 and "LEDGERLENS-SPA" in deep_link.text
    asset = web_client.get("/assets/app.js")
    assert asset.status_code == 200 and "console.log" in asset.text


def test_api_routes_win_over_the_web_app(web_client: TestClient) -> None:
    assert web_client.get("/health").json()["status"] == "ok"
    unknown = web_client.get("/api/v1/does-not-exist")
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "not_found"  # JSON, not index.html
    assert web_client.get("/api/v1/auth/me").status_code == 401


def test_files_outside_the_web_folder_are_not_served(web_client: TestClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "TOP-SECRET" not in web_client.get(path).text


def test_desktop_mode_rejects_foreign_host_headers(web_client: TestClient) -> None:
    assert web_client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    assert web_client.get("/health", headers={"Host": "localhost:8765"}).status_code == 200


def test_missing_web_build_fails_loudly(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"index\.html"):
        create_app(Settings(app_env="desktop", frontend_dist=tmp_path))


def test_startup_errors_never_repeat_setting_values() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as caught:
        Settings(secret_key="super-secret-value-0123456789abcdef", ai_provider="anthropic")
    text = desktop.describe_error(caught.value)
    assert "ANTHROPIC_API_KEY is required" in text
    assert "super-secret-value" not in text
    assert "input_value" not in text
