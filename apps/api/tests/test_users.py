from pathlib import Path

from app.core.config import get_settings
from fastapi.testclient import TestClient

from tests.conftest import MINIMAL_PNG, UserSession

ME = "/api/v1/users/me"


def test_update_profile(alice: UserSession) -> None:
    response = alice.patch(ME, json={"name": "Alice B.", "default_currency": "chf"})
    assert response.status_code == 200
    assert response.json()["name"] == "Alice B."
    assert response.json()["default_currency"] == "CHF"


def test_delete_account_requires_password_and_removes_everything(
    client: TestClient, alice: UserSession
) -> None:
    alice.add_transaction()
    alice.post("/api/v1/receipts", files={"file": ("r.png", MINIMAL_PNG, "image/png")})
    upload_dir = Path(get_settings().upload_dir)
    assert list(upload_dir.rglob("*.png"))

    wrong = alice.delete(ME, json={"password": "not-the-password-1"})
    assert wrong.status_code == 401

    ok = alice.delete(ME, json={"password": alice.password})
    assert ok.status_code == 204
    assert list(upload_dir.rglob("*.png")) == []
    assert alice.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login", json={"email": alice.email, "password": alice.password}
    )
    assert login.status_code == 401
