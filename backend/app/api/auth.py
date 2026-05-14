from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.deps import BearerCredentials, CurrentUser, DbSession
from app.core.auth_context import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    logout_access_token,
    set_auth_cookies,
)
from app.core.config import settings
from app.core.security import blacklist_refresh_token, blacklist_token
from app.schemas.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)
from app.services.auth_attempts import check_login_locked, clear_login_attempts, record_failed_login
from app.services.auth_service import (
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    MissingRefreshTokenError,
    RefreshUserNotFoundError,
    RevokedRefreshTokenError,
    UsernameAlreadyExistsError,
    authenticate_user,
    refresh_token_pair,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    response: Response,
    db: DbSession,
):
    try:
        result = await register_user(
            db,
            username=payload.username,
            password=payload.password,
            display_name=payload.display_name,
        )
    except UsernameAlreadyExistsError:
        raise HTTPException(status_code=400, detail="Username already exists")

    set_auth_cookies(response, result.tokens.access_token, result.tokens.refresh_token)
    return TokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        user=UserResponse.model_validate(result.user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with username and password. Sets httpOnly cookies.",
)
async def login(
    payload: UserLogin,
    response: Response,
    db: DbSession,
):
    locked = await check_login_locked(payload.username)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"账户已被临时锁定，请 {settings.LOGIN_LOCKOUT_MINUTES} 分钟后再试",
        )

    try:
        result = await authenticate_user(db, username=payload.username, password=payload.password)
    except InvalidCredentialsError:
        await record_failed_login(payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await clear_login_attempts(payload.username)

    set_auth_cookies(response, result.tokens.access_token, result.tokens.refresh_token)
    return TokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        user=UserResponse.model_validate(result.user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    request: Request,
    current_user: CurrentUser,
    credentials: BearerCredentials,
):
    """Invalidate the current access token and clear cookies."""
    # Blacklist access token from header or cookie
    token = logout_access_token(
        request.cookies.get(ACCESS_COOKIE),
        credentials.credentials if credentials else None,
    )
    if token:
        await blacklist_token(token)
    # Also blacklist the refresh token for rotation
    refresh = request.cookies.get(REFRESH_COOKIE)
    if refresh:
        await blacklist_refresh_token(refresh)
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new token pair. Old refresh token is rotated (blacklisted).",
)
async def refresh(
    response: Response,
    request: Request,
    db: DbSession,
    payload: RefreshTokenRequest | None = None,
):
    # Read refresh token from cookie first, then fall back to request body
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token and payload:
        refresh_token = payload.refresh_token

    try:
        result = await refresh_token_pair(db, refresh_token)
    except MissingRefreshTokenError:
        raise HTTPException(status_code=401, detail="No refresh token provided")
    except RevokedRefreshTokenError:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")
    except InvalidRefreshTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    except RefreshUserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    set_auth_cookies(response, result.tokens.access_token, result.tokens.refresh_token)
    return TokenResponse(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        user=UserResponse.model_validate(result.user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user from cookie or header",
)
async def get_me(current_user: CurrentUser):
    """Return the currently authenticated user (from cookie or Authorization header)."""
    return UserResponse.model_validate(current_user)
