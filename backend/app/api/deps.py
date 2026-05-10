import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token, extract_jti, check_token_blacklisted
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("app.api.deps")

ACCESS_COOKIE = "access_token"


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate user from httpOnly cookie or Authorization header.

    Validates the preferred token source (cookie first). If it's invalid/expired,
    falls back to the other source before returning 401.
    """
    cookie_token = request.cookies.get(ACCESS_COOKIE)
    header_token = credentials.credentials if credentials else None

    # Collect candidate tokens (cookie first)
    candidates = []
    if cookie_token:
        candidates.append(cookie_token)
    if header_token and header_token != cookie_token:
        candidates.append(header_token)

    for token in candidates:
        if not token:
            continue
        jti = extract_jti(token)
        if jti:
            is_blacklisted = await check_token_blacklisted(jti)
            if is_blacklisted:
                continue
        else:
            logger.warning("Token missing jti claim — cannot check blacklist")

        user_id = decode_access_token(token)
        if user_id is None:
            continue

        user = await db.get(User, user_id)
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
