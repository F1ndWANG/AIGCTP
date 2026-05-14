from pydantic_settings import BaseSettings
from typing import Optional

from app.core.config_validation import (
    enforce_production_settings,
    validate_runtime_settings,
    warn_development_settings,
)

__all__ = ["Settings", "settings", "validate_runtime_settings"]


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

    # Product image generation (OpenAI-compatible image API)
    IMAGE_API_KEY: Optional[str] = None
    IMAGE_API_BASE: str = "https://api.openai.com/v1"
    IMAGE_MODEL: str = "gpt-image-2"
    PRODUCT_IMAGE_OUTPUT_DIR: str = "../frontend/public/generated-products"
    PRODUCT_IMAGE_PUBLIC_PATH: str = "/generated-products"

    # Recommendation embeddings (optional; local similarity fallback is always available)
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_API_BASE: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    RECOMMENDATION_DECAY_HALF_LIFE_DAYS: int = 14
    RECOMMENDATION_DEFAULT_LIMIT: int = 12
    RECOMMENDATION_MAX_CANDIDATES: int = 96
    RECOMMENDATION_SCORE_WEIGHTS: str = ""
    RECOMMENDATION_MMR_RELEVANCE: float = 0.75

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
    DB_AUTO_CREATE_TABLES: Optional[bool] = None

    # Testing
    TESTING: bool = False
    DEMO_CATALOG_AUTO_SEED: Optional[bool] = None

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


if settings.is_production:
    enforce_production_settings(settings)
else:
    warn_development_settings(settings)
