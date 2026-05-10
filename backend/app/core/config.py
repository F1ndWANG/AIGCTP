import os
import sys
import warnings
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Life Recommender"
    APP_ENV: str = "development"  # development | staging | production
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_DEFAULT: int = 300
    REDIS_TTL_POI: int = 3600
    REDIS_TTL_RESTAURANT: int = 1800
    REDIS_TTL_LLM_CHAT: int = 3600
    REDIS_TTL_CONVERSATION: int = 3600
    REDIS_MAX_CONNECTIONS: int = 10

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 5
    RATE_LIMIT_CHAT_PER_MINUTE: int = 30

    # LLM (DeepSeek, OpenAI-compatible)
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-flash"
    LLM_FALLBACK_MODEL: Optional[str] = None

    # Amap (高德地图)
    AMAP_API_KEY: Optional[str] = None

    # QWeather (和风天气)
    QWEATHER_API_KEY: Optional[str] = None

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # short-lived for cookie auth
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_EXPIRATION_HOURS: int = 72  # kept for backward compat

    # Cookie
    COOKIE_SECURE: bool = False  # set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None

    # Security
    PASSWORD_MIN_LENGTH: int = 8
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Sentry
    SENTRY_DSN: Optional[str] = None

    # Uvicorn workers (Docker)
    WORKERS: int = 4

    # Slow query threshold (seconds)
    SLOW_QUERY_THRESHOLD: float = 0.5

    # Request limits
    MAX_REQUEST_BODY_SIZE: int = 1_048_576  # 1MB

    # Database pool
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    # Testing
    TESTING: bool = False

    # Trusted proxies (space-separated IPs/CIDRs for X-Forwarded-For)
    TRUSTED_PROXIES: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def trusted_proxies_list(self) -> list[str]:
        return [p.strip() for p in self.TRUSTED_PROXIES.split() if p.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# ── Production validation ──────────────────────────────────────────
def _validate_production() -> None:
    """Refuse to start in production mode with unsafe settings."""
    errors = []

    _DEFAULT_SECRETS = ("dev-secret-change-in-production", "your_jwt_secret_key", "")
    if settings.JWT_SECRET in _DEFAULT_SECRETS:
        errors.append("JWT_SECRET is set to a default/example value")
    if len(settings.JWT_SECRET) < 32:
        errors.append("JWT_SECRET must be at least 32 characters")

    if not settings.LLM_API_KEY:
        errors.append("LLM_API_KEY is not set")
    elif any(p in settings.LLM_API_KEY.lower() for p in ("placeholder", "sk-your-", "replace-with")):
        errors.append("LLM_API_KEY appears to be a placeholder value")

    if not settings.AMAP_API_KEY:
        errors.append("AMAP_API_KEY is not set")
    elif any(p in settings.AMAP_API_KEY.lower() for p in ("your_", "placeholder")):
        errors.append("AMAP_API_KEY appears to be a placeholder value")

    if not settings.QWEATHER_API_KEY:
        errors.append("QWEATHER_API_KEY is not set")
    elif any(p in settings.QWEATHER_API_KEY.lower() for p in ("your_", "placeholder")):
        errors.append("QWEATHER_API_KEY appears to be a placeholder value")

    if settings.DEBUG:
        errors.append("DEBUG must be False in production")

    if not errors:
        return

    msg = "Production startup failed:\n" + "\n".join(f"  - {e}" for e in errors)
    print(msg, file=sys.stderr)
    sys.exit(1)


def _warn_dev() -> None:
    """Warn about missing or default critical env vars at startup (dev only)."""
    issues = []
    if not settings.LLM_API_KEY:
        issues.append("LLM_API_KEY is not set")
    _DEFAULT_SECRETS = ("dev-secret-change-in-production", "your_jwt_secret_key", "")
    if settings.JWT_SECRET in _DEFAULT_SECRETS:
        issues.append("JWT_SECRET is using default value (insecure for production)")
    if issues:
        warnings.warn("Startup environment issues: " + "; ".join(issues), stacklevel=2)


if settings.is_production:
    _validate_production()
else:
    _warn_dev()
