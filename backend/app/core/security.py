"""Security utilities: password hashing, JWT tokens, refresh tokens, token blacklist."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _make_jti() -> str:
    return uuid.uuid4().hex[:16]


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Short-lived access token (default: 15 minutes for cookie auth)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": str(user_id),
        "type": "access",
        "jti": _make_jti(),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Long-lived refresh token (default: 30 days)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": _make_jti(),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[int]:
    """Decode and validate an access token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") not in ("access", None):
            return None
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None


def decode_refresh_token(token: str) -> Optional[int]:
    """Decode and validate a refresh token. Returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        return None


# ── Token Blacklist (Redis-backed) ──────────────────────────────


def _decode_payload(token: str) -> Optional[dict]:
    """Decode JWT payload without validation (for extracting jti/exp)."""
    try:
        return jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},
        )
    except JWTError:
        return None


def extract_jti(token: str) -> Optional[str]:
    """Extract the ``jti`` claim from a JWT without full validation."""
    payload = _decode_payload(token)
    return payload.get("jti") if payload else None


def token_expires_in(token: str) -> int:
    """Return remaining TTL in seconds for a token (for blacklist TTL)."""
    payload = _decode_payload(token)
    if not payload:
        return 0
    exp = payload.get("exp", 0)
    remaining = int(exp - datetime.now(timezone.utc).timestamp())
    return max(remaining, 0)


async def check_token_blacklisted(jti: str) -> bool:
    """Check whether a JWT ``jti`` is on the Redis blacklist."""
    if not jti:
        return False
    from app.core.redis import get_redis
    r = await get_redis()
    if not r:
        return False
    return bool(await r.exists(f"token_blacklist:{jti}"))


async def blacklist_token(token: str) -> None:
    """Add a JWT to the Redis blacklist for its remaining lifetime."""
    jti = extract_jti(token)
    if not jti:
        return
    ttl = token_expires_in(token)
    if ttl < 1:
        return
    from app.core.redis import get_redis
    r = await get_redis()
    if not r:
        return
    await r.setex(f"token_blacklist:{jti}", ttl, "1")


async def blacklist_refresh_token(token: str) -> None:
    """Blacklist a refresh token jti (for rotation on refresh)."""
    await blacklist_token(token)


async def check_refresh_blacklisted(jti: str) -> bool:
    """Check whether a refresh token jti is blacklisted."""
    return await check_token_blacklisted(jti)

