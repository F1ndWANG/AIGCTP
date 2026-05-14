"""Authentication domain operations.

The API layer translates these outcomes into HTTP responses and cookies; this
module owns user lookup, password verification, and token issuance.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    blacklist_refresh_token,
    check_refresh_blacklisted,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    extract_jti,
    hash_password,
    verify_password,
)
from app.models.user import User


@dataclass(frozen=True)
class AuthTokenPair:
    access_token: str
    refresh_token: str


@dataclass(frozen=True)
class AuthResult:
    user: User
    tokens: AuthTokenPair


class UsernameAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class MissingRefreshTokenError(Exception):
    pass


class RevokedRefreshTokenError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


class RefreshUserNotFoundError(Exception):
    pass


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


def issue_token_pair(user_id: int) -> AuthTokenPair:
    return AuthTokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


async def register_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
) -> AuthResult:
    if await get_user_by_username(db, username):
        raise UsernameAlreadyExistsError

    user = User(
        username=username,
        hashed_password=hash_password(password),
        display_name=display_name or username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AuthResult(user=user, tokens=issue_token_pair(user.id))


async def authenticate_user(db: AsyncSession, *, username: str, password: str) -> AuthResult:
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError
    return AuthResult(user=user, tokens=issue_token_pair(user.id))


async def refresh_token_pair(db: AsyncSession, refresh_token: str | None) -> AuthResult:
    if not refresh_token:
        raise MissingRefreshTokenError

    jti = extract_jti(refresh_token)
    if jti and await check_refresh_blacklisted(jti):
        raise RevokedRefreshTokenError

    user_id = decode_refresh_token(refresh_token)
    if user_id is None:
        raise InvalidRefreshTokenError

    user = await db.get(User, user_id)
    if not user:
        raise RefreshUserNotFoundError

    await blacklist_refresh_token(refresh_token)
    return AuthResult(user=user, tokens=issue_token_pair(user.id))
