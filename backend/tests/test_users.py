def _register_and_token(client):
    r = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert r.status_code == 201
    return r.json()["tokens"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestMe:
    def test_me_requires_auth(self, client):
        r = client.get("/api/v1/users/me")
        assert r.status_code == 401

    def test_me_ok(self, client):
        token = _register_and_token(client)
        r = client.get("/api/v1/users/me", headers=_auth(token))
        assert r.status_code == 200
        assert r.json()["username"] == "alice"

    def test_me_invalid_token(self, client):
        r = client.get("/api/v1/users/me", headers=_auth("invalid.token.here"))
        assert r.status_code == 401


class TestUpdateProfile:
    def test_update_profile(self, client):
        token = _register_and_token(client)
        r = client.patch(
            "/api/v1/users/me",
            headers=_auth(token),
            json={"nickname": "Ally", "gender": "female", "birth_date": "2000-01-01"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["nickname"] == "Ally"
        assert body["gender"] == "female"
        assert body["birth_date"] == "2000-01-01"

    def test_update_profile_invalid_gender(self, client):
        token = _register_and_token(client)
        r = client.patch(
            "/api/v1/users/me",
            headers=_auth(token),
            json={"gender": "unknown"},
        )
        assert r.status_code == 422


class TestChangePassword:
    def test_change_password_success(self, client):
        token = _register_and_token(client)
        r = client.post(
            "/api/v1/users/me/password",
            headers=_auth(token),
            json={"old_password": "secret123", "new_password": "new-secret-456"},
        )
        assert r.status_code == 204
        # old password no longer works
        r2 = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "secret123"},
        )
        assert r2.status_code == 401
        # new password works
        r3 = client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "new-secret-456"},
        )
        assert r3.status_code == 200

    def test_change_password_wrong_old(self, client):
        token = _register_and_token(client)
        r = client.post(
            "/api/v1/users/me/password",
            headers=_auth(token),
            json={"old_password": "wrong-old", "new_password": "new-secret-456"},
        )
        assert r.status_code == 400
