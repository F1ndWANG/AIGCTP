"""Authentication cookie and token-source helpers."""

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
AUTH_COOKIE_PATH = "/"
LEGACY_AUTH_COOKIE_PATHS = ("/api", "/api/v1/auth", "/api/auth")


def access_token_candidates(cookie_token: str | None, header_token: str | None) -> tuple[str, ...]:
    """Return access token candidates in validation priority order."""
    candidates = []
    if cookie_token:
        candidates.append(cookie_token)
    if header_token and header_token != cookie_token:
        candidates.append(header_token)
    return tuple(candidates)


def logout_access_token(cookie_token: str | None, header_token: str | None) -> str | None:
    """Return the access token source that should be revoked on logout."""
    return header_token or cookie_token


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly auth cookies and clear older scoped cookies."""
    for legacy_path in LEGACY_AUTH_COOKIE_PATHS:
        response.delete_cookie(key=ACCESS_COOKIE, path=legacy_path)
        response.delete_cookie(key=REFRESH_COOKIE, path=legacy_path)

    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=AUTH_COOKIE_PATH,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=AUTH_COOKIE_PATH,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )


def clear_auth_cookies(response: Response) -> None:
    """Delete all known auth cookie path variants."""
    for path in (AUTH_COOKIE_PATH, *LEGACY_AUTH_COOKIE_PATHS):
        response.delete_cookie(key=ACCESS_COOKIE, path=path)
        response.delete_cookie(key=REFRESH_COOKIE, path=path)
