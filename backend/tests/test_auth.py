import pytest


VALID_PAYLOAD = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "secret123",
}


def _register(client, **overrides):
    payload = {**VALID_PAYLOAD, **overrides}
    return client.post("/api/v1/auth/register", json=payload)


def _login(client, username="alice", password="secret123"):
    return client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )


class TestRegister:
    def test_register_success(self, client):
        r = _register(client)
        assert r.status_code == 201
        body = r.json()
        assert body["user"]["username"] == "alice"
        assert body["user"]["email"] == "alice@example.com"
        assert "id" in body["user"]
        assert body["tokens"]["access_token"]
        assert body["tokens"]["refresh_token"]
        assert body["tokens"]["token_type"] == "bearer"

    def test_register_duplicate_username(self, client):
        assert _register(client).status_code == 201
        r = _register(client, email="other@example.com")
        assert r.status_code == 409

    def test_register_duplicate_email(self, client):
        assert _register(client).status_code == 201
        r = _register(client, username="bob")
        assert r.status_code == 409

    @pytest.mark.parametrize(
        "bad",
        [
            {"username": "ab"},                 # too short
            {"username": "bad name"},           # invalid chars
            {"email": "not-an-email"},
            {"password": "123"},                # too short
        ],
    )
    def test_register_validation(self, client, bad):
        r = _register(client, **bad)
        assert r.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        _register(client)
        r = _login(client)
        assert r.status_code == 200
        assert r.json()["tokens"]["access_token"]

    def test_login_wrong_password(self, client):
        _register(client)
        r = _login(client, password="nope-nope")
        assert r.status_code == 401

    def test_login_unknown_user(self, client):
        r = _login(client, username="ghost", password="whatever")
        assert r.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client):
        tokens = _register(client).json()["tokens"]
        r = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert r.status_code == 200
        assert r.json()["access_token"]

    def test_refresh_rejects_access_token(self, client):
        tokens = _register(client).json()["tokens"]
        r = client.post(
            "/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )
        assert r.status_code == 401

    def test_refresh_invalid(self, client):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert r.status_code == 401
