"""Tests for security: password hashing, JWT token creation and verification."""
import time
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


class TestPasswordHashing:
    async def test_hash_password_returns_string(self):
        h = hash_password("test123")
        assert isinstance(h, str) and len(h) > 0

    async def test_hash_password_unique_per_call(self):
        h1 = hash_password("test123")
        h2 = hash_password("test123")
        assert h1 != h2

    async def test_verify_password_correct(self):
        h = hash_password("correct-password")
        assert verify_password("correct-password", h) is True

    async def test_verify_password_incorrect(self):
        h = hash_password("correct-password")
        assert verify_password("wrong-password", h) is False


class TestJWT:
    async def test_create_access_token(self):
        token = create_access_token(42)
        assert isinstance(token, str) and len(token) > 20

    async def test_decode_access_token_valid(self):
        token = create_access_token(42)
        decoded = decode_access_token(token)
        assert decoded == 42

    async def test_decode_access_token_invalid(self):
        decoded = decode_access_token("invalid.token.here")
        assert decoded is None

    async def test_decode_access_token_expired(self):
        from datetime import timedelta
        token = create_access_token(42, expires_delta=timedelta(hours=-1))
        decoded = decode_access_token(token)
        assert decoded is None
