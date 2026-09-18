"""Test configuration.

Environment variables are set *before* the application is imported so that the
cached settings, the database engine and the rate limiters pick them up.
Every test gets a fresh SQLite database file and an empty upload directory.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="ledgerlens-test-"))
os.environ.update(
    {
        "APP_ENV": "test",
        "SECRET_KEY": "test-secret-key-that-is-long-enough-for-tests-0123456789",
        "DATABASE_URL": f"sqlite:///{_TMP / 'test.db'}",
        "UPLOAD_DIR": str(_TMP / "uploads"),
        "AI_PROVIDER": "mock",
        "MAX_UPLOAD_MB": "1",
        "RATE_LIMIT_AUTH_PER_MINUTE": "30",
        "RATE_LIMIT_AI_PER_MINUTE": "30",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "LOG_LEVEL": "WARNING",
    }
)

import pytest  # noqa: E402
from app.api import deps  # noqa: E402
from app.core.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MINIMAL_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
MINIMAL_PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture(autouse=True)
def _fresh_database() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    upload_dir = _TMP / "uploads"
    shutil.rmtree(upload_dir, ignore_errors=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
    deps.auth_limiter.reset()
    deps.ai_limiter.reset()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app, base_url="http://testserver") as c:
        yield c


class UserSession:
    """Convenience wrapper: a registered user plus an authenticated client."""

    def __init__(self, client: TestClient, email: str, password: str, name: str) -> None:
        self.client = client
        self.email = email
        self.password = password
        self.name = name
        self.access_token = ""

    def register(self) -> UserSession:
        response = self.client.post(
            "/api/v1/auth/register",
            json={"email": self.email, "password": self.password, "name": self.name},
        )
        assert response.status_code == 201, response.text
        self.access_token = response.json()["access_token"]
        return self

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    def get(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return self.client.get(url, headers=self.headers, **kwargs)

    def post(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return self.client.post(url, headers=self.headers, **kwargs)

    def patch(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return self.client.patch(url, headers=self.headers, **kwargs)

    def delete(self, url: str, **kwargs):  # type: ignore[no-untyped-def]
        return self.client.request("DELETE", url, headers=self.headers, **kwargs)

    def categories(self) -> dict[str, str]:
        response = self.get("/api/v1/categories")
        assert response.status_code == 200
        return {c["name"]: c["id"] for c in response.json()}

    def add_transaction(self, **overrides):  # type: ignore[no-untyped-def]
        payload = {
            "date": "2026-09-10",
            "merchant": "Test Merchant",
            "amount": "19.99",
            "currency": "EUR",
        }
        payload.update(overrides)
        response = self.post("/api/v1/transactions", json=payload)
        assert response.status_code == 201, response.text
        return response.json()


@pytest.fixture
def alice(client: TestClient) -> UserSession:
    return UserSession(client, "alice@example.com", "correct-horse-battery-9", "Alice").register()


@pytest.fixture
def bob(client: TestClient) -> UserSession:
    return UserSession(client, "bob@example.com", "another-strong-pass-42", "Bob").register()
