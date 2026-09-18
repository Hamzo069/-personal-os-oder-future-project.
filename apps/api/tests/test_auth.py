from fastapi.testclient import TestClient

from tests.conftest import UserSession

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
COOKIE = "ledgerlens_refresh"


def test_register_returns_token_and_sets_refresh_cookie(client: TestClient) -> None:
    response = client.post(
        REGISTER, json={"email": "New@Example.com", "password": "s3cure-password!", "name": "New"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    cookie = response.headers.get("set-cookie", "")
    assert COOKIE in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "new@example.com"  # normalised to lower case


def test_register_duplicate_email_conflicts(client: TestClient, alice: UserSession) -> None:
    response = client.post(
        REGISTER, json={"email": alice.email, "password": "s3cure-password!", "name": "Dup"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_weak_passwords(client: TestClient) -> None:
    for password in ["short1!", "onlylettersherexx", "12345678901234"]:
        response = client.post(
            REGISTER, json={"email": "weak@example.com", "password": password, "name": "W"}
        )
        assert response.status_code == 422, password


def test_login_success_and_failure(client: TestClient, alice: UserSession) -> None:
    ok = client.post(LOGIN, json={"email": alice.email, "password": alice.password})
    assert ok.status_code == 200
    bad = client.post(LOGIN, json={"email": alice.email, "password": "wrong-password-1"})
    assert bad.status_code == 401
    assert bad.headers["www-authenticate"] == "Bearer"
    unknown = client.post(LOGIN, json={"email": "ghost@example.com", "password": "whatever-123"})
    assert unknown.status_code == 401


def test_protected_route_requires_valid_token(client: TestClient) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_refresh_rotates_token_and_detects_reuse(client: TestClient, alice: UserSession) -> None:
    login = client.post(LOGIN, json={"email": alice.email, "password": alice.password})
    first_refresh_cookie = login.cookies[COOKIE]

    refreshed = client.post(REFRESH)  # cookie jar carries the refresh cookie
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    second_refresh_cookie = refreshed.cookies[COOKIE]
    assert second_refresh_cookie != first_refresh_cookie

    # Replaying the already-rotated token must fail and revoke the whole family.
    client.cookies.set(COOKIE, first_refresh_cookie)
    replay = client.post(REFRESH)
    assert replay.status_code == 401

    client.cookies.set(COOKIE, second_refresh_cookie)
    after_reuse = client.post(REFRESH)
    assert after_reuse.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, alice: UserSession) -> None:
    client.post(LOGIN, json={"email": alice.email, "password": alice.password})
    assert client.post(LOGOUT).status_code == 200
    assert client.post(REFRESH).status_code == 401


def test_refresh_without_cookie(client: TestClient) -> None:
    assert client.post(REFRESH).status_code == 401


def test_auth_rate_limit(client: TestClient) -> None:
    from app.api import deps

    deps.auth_limiter.limit = 3
    try:
        statuses = [
            client.post(
                LOGIN, json={"email": "x@example.com", "password": "nope-nope-1"}
            ).status_code
            for _ in range(4)
        ]
    finally:
        deps.auth_limiter.limit = 30
    assert statuses[:3] == [401, 401, 401]
    assert statuses[3] == 429
