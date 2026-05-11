from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    blacklist_token,
    blacklist_refresh_token,
    check_refresh_blacklisted,
    extract_jti,
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserLogin,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
)

bearer_scheme = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
AUTH_COOKIE_PATH = "/"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly cookies for access and refresh tokens."""
    for legacy_path in ("/api", "/api/v1/auth", "/api/auth"):
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


def _clear_auth_cookies(response: Response) -> None:
    """Delete auth cookies."""
    for path in (AUTH_COOKIE_PATH, "/api", "/api/v1/auth", "/api/auth"):
        response.delete_cookie(key=ACCESS_COOKIE, path=path)
        response.delete_cookie(key=REFRESH_COOKIE, path=path)


async def _check_login_locked(username: str) -> bool:
    """Check if a username is temporarily locked due to failed attempts."""
    r = await get_redis()
    if not r:
        return False
    key = f"login_lockout:{username}"
    exists = await r.exists(key)
    if exists:
        ttl = await r.ttl(key)
        if ttl > 0:
            return True
    return False


async def _record_failed_login(username: str) -> int:
    """Record a failed login attempt. Returns the current attempt count."""
    r = await get_redis()
    if not r:
        return 0
    key = f"login_attempts:{username}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, settings.LOGIN_LOCKOUT_MINUTES * 60)

    if count >= settings.LOGIN_MAX_ATTEMPTS:
        lock_key = f"login_lockout:{username}"
        await r.setex(lock_key, settings.LOGIN_LOCKOUT_MINUTES * 60, "1")
        await r.delete(key)
        return count

    return count


async def _clear_login_attempts(username: str) -> None:
    """Clear failed login tracking on successful login."""
    r = await get_redis()
    if not r:
        return
    await r.delete(f"login_attempts:{username}")
    await r.delete(f"login_lockout:{username}")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
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
    db: AsyncSession = Depends(get_db),
):
    locked = await _check_login_locked(payload.username)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"账户已被临时锁定，请 {settings.LOGIN_LOCKOUT_MINUTES} 分钟后再试",
        )

    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        await _record_failed_login(payload.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await _clear_login_attempts(payload.username)

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    _set_auth_cookies(response, access_token, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    request: Request,
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Invalidate the current access token and clear cookies."""
    # Blacklist access token from header or cookie
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE)
    if token:
        await blacklist_token(token)
    # Also blacklist the refresh token for rotation
    refresh = request.cookies.get(REFRESH_COOKIE)
    if refresh:
        await blacklist_refresh_token(refresh)
    _clear_auth_cookies(response)
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
    payload: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    # Read refresh token from cookie first, then fall back to request body
    refresh_token = request.cookies.get(REFRESH_COOKIE)
    if not refresh_token and payload:
        refresh_token = payload.refresh_token

    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token provided")

    # Check if this refresh token has been revoked (rotation)
    jti = extract_jti(refresh_token)
    if jti and await check_refresh_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user_id = decode_refresh_token(refresh_token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Rotate: blacklist old refresh, issue new pair
    await blacklist_refresh_token(refresh_token)

    access_token = create_access_token(user.id)
    new_refresh = create_refresh_token(user.id)
    _set_auth_cookies(response, access_token, new_refresh)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user from cookie or header",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user (from cookie or Authorization header)."""
    return UserResponse.model_validate(current_user)
