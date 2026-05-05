from contextlib import asynccontextmanager
import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import close_redis
from app.core.logging import setup_logging, get_logger
from app.api import auth, users, travel, chat, route, diet, commerce, feedback, restaurant
from app.middleware.rate_limit import RateLimitMiddleware

logger = get_logger(__name__)


def _validate_env() -> None:
    """Warn about missing or default critical env vars at startup."""
    issues = []
    if not settings.LLM_API_KEY:
        issues.append("LLM_API_KEY is not set")
    if settings.JWT_SECRET in ("dev-secret-change-in-production", "your_jwt_secret_key", ""):
        issues.append("JWT_SECRET is using default value (insecure for production)")
    if issues:
        warnings.warn("Startup environment issues: " + "; ".join(issues), stacklevel=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.DEBUG)
    _validate_env()
    await init_db()
    yield
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(travel.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(route.router, prefix="/api/v1")
app.include_router(diet.router, prefix="/api/v1")
app.include_router(commerce.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(restaurant.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.1.0"}
