import time

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPassword:
    def test_hash_and_verify(self):
        h = hash_password("secret123")
        assert h != "secret123"
        assert verify_password("secret123", h)
        assert not verify_password("wrong", h)

    def test_hash_is_salted(self):
        assert hash_password("secret123") != hash_password("secret123")


class TestJwt:
    def test_access_token_roundtrip(self):
        token = create_access_token("42")
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert payload["exp"] > payload["iat"]

    def test_refresh_token_type(self):
        token = create_refresh_token("7")
        assert decode_token(token)["type"] == "refresh"

    def test_decode_invalid_raises(self):
        with pytest.raises(ValueError):
            decode_token("not-a-jwt")

    def test_decode_wrong_secret_raises(self):
        s = get_settings()
        bogus = jwt.encode({"sub": "1", "exp": int(time.time()) + 60, "type": "access"},
                           "other-secret", algorithm=s.jwt_algorithm)
        with pytest.raises(ValueError):
            decode_token(bogus)
