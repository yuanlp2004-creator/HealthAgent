"""P2 E2E smoke test — runs against a live uvicorn process on 127.0.0.1:8000.

Covers: register -> me -> update profile -> change password -> login(old fail) ->
login(new ok) -> refresh -> /healthz. Exits non-zero on any assertion failure.
"""
from __future__ import annotations

import sys
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"


def wait_ready(timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/healthz", timeout=2.0)
            if r.status_code == 200 and r.json().get("status") == "ok":
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError("backend /healthz not ready")


def main() -> int:
    wait_ready()
    suffix = uuid.uuid4().hex[:8]
    username = f"smoke_{suffix}"
    email = f"{username}@example.com"
    password = "InitPass123"
    new_password = "NewPass456"

    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")

    with httpx.Client(base_url=API, timeout=10.0) as c:
        r = c.post("/auth/register", json={
            "username": username, "email": email, "password": password, "nickname": "冒烟"
        })
        check("register 201", r.status_code == 201, f"status={r.status_code}")
        data = r.json()
        access = data["tokens"]["access_token"]
        refresh = data["tokens"]["refresh_token"]
        check("register returns user.username", data["user"]["username"] == username)

        r = c.post("/auth/register", json={
            "username": username, "email": f"other_{suffix}@example.com", "password": password
        })
        check("duplicate username -> 409", r.status_code == 409, f"status={r.status_code}")

        r = c.get("/users/me", headers={"Authorization": f"Bearer {access}"})
        check("me ok with token", r.status_code == 200 and r.json()["username"] == username)

        r = c.get("/users/me")
        check("me without token -> 401", r.status_code == 401)

        r = c.patch("/users/me",
                    headers={"Authorization": f"Bearer {access}"},
                    json={"nickname": "冒烟user", "gender": "male", "birth_date": "2000-01-01"})
        check("update profile 200",
              r.status_code == 200 and r.json()["nickname"] == "冒烟user" and r.json()["gender"] == "male")

        r = c.post("/auth/refresh", json={"refresh_token": refresh})
        check("refresh 200", r.status_code == 200 and "access_token" in r.json())
        access2 = r.json()["access_token"]

        r = c.post("/auth/refresh", json={"refresh_token": access2})
        check("refresh with access token -> 401", r.status_code == 401)

        r = c.post("/users/me/password",
                   headers={"Authorization": f"Bearer {access2}"},
                   json={"old_password": "wrong", "new_password": new_password})
        check("change pwd wrong old -> 400", r.status_code == 400)

        r = c.post("/users/me/password",
                   headers={"Authorization": f"Bearer {access2}"},
                   json={"old_password": password, "new_password": new_password})
        check("change pwd success -> 204", r.status_code == 204)

        r = c.post("/auth/login", json={"username": username, "password": password})
        check("old password rejected -> 401", r.status_code == 401)

        r = c.post("/auth/login", json={"username": username, "password": new_password})
        check("new password login -> 200",
              r.status_code == 200 and r.json()["user"]["username"] == username)

    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== smoke: {passed}/{total} passed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
