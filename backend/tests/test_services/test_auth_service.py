import pytest

from app.services.auth_service import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    MissingRefreshTokenError,
    UsernameAlreadyExistsError,
    authenticate_user,
    issue_token_pair,
    refresh_token_pair,
    register_user,
)


@pytest.mark.anyio
async def test_register_user_creates_user_and_tokens(session):
    result = await register_user(
        session,
        username="service-user",
        password="Pass1234",
        display_name="Service User",
    )

    assert result.user.id
    assert result.user.username == "service-user"
    assert result.user.display_name == "Service User"
    assert result.tokens.access_token
    assert result.tokens.refresh_token


@pytest.mark.anyio
async def test_register_user_rejects_duplicate_username(session):
    await register_user(session, username="duplicate", password="Pass1234")

    with pytest.raises(UsernameAlreadyExistsError):
        await register_user(session, username="duplicate", password="Pass1234")


@pytest.mark.anyio
async def test_authenticate_user_validates_password(session):
    await register_user(session, username="login-service", password="Pass1234")

    result = await authenticate_user(session, username="login-service", password="Pass1234")

    assert result.user.username == "login-service"
    assert result.tokens.access_token


@pytest.mark.anyio
async def test_authenticate_user_rejects_bad_password(session):
    await register_user(session, username="bad-pass-service", password="Pass1234")

    with pytest.raises(InvalidCredentialsError):
        await authenticate_user(session, username="bad-pass-service", password="Wrong123")


@pytest.mark.anyio
async def test_refresh_token_pair_rotates_valid_refresh_token(session):
    created = await register_user(session, username="refresh-service", password="Pass1234")

    refreshed = await refresh_token_pair(session, created.tokens.refresh_token)

    assert refreshed.user.id == created.user.id
    assert refreshed.tokens.access_token
    assert refreshed.tokens.refresh_token != created.tokens.refresh_token


@pytest.mark.anyio
async def test_refresh_token_pair_rejects_missing_or_invalid_token(session):
    with pytest.raises(MissingRefreshTokenError):
        await refresh_token_pair(session, None)

    with pytest.raises(InvalidRefreshTokenError):
        await refresh_token_pair(session, "not-a-jwt")


def test_issue_token_pair_returns_distinct_tokens():
    tokens = issue_token_pair(123)

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.access_token != tokens.refresh_token
