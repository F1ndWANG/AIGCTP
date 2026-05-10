"""Middleware that rejects requests exceeding a configured body size limit."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_size: int | None = None) -> None:
        super().__init__(app)
        self.max_size = max_size or settings.MAX_REQUEST_BODY_SIZE

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "ERR_BODY_TOO_LARGE",
                    "detail": f"Request body exceeds {self.max_size // 1048576}MB limit",
                },
            )
        return await call_next(request)
