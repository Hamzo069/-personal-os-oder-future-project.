from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_rate_limit_key_ignores_forwarded_header(client: TestClient) -> None:
    """Spoofing X-Forwarded-For must not give a client a fresh rate-limit bucket."""
    from app.api import deps

    deps.auth_limiter.limit = 2
    try:
        codes = [
            client.post(
                "/api/v1/auth/login",
                json={"email": "x@example.com", "password": "nope-nope-1"},
                headers={"X-Forwarded-For": f"10.0.0.{i}"},
            ).status_code
            for i in range(3)
        ]
    finally:
        deps.auth_limiter.limit = 30
    assert codes == [401, 401, 429]
