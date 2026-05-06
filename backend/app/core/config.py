import warnings
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI Life Recommender"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://lifeai:lifeai_dev@localhost:5432/life_recommender"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_TTL_DEFAULT: int = 300
    REDIS_TTL_POI: int = 3600
    REDIS_TTL_CONVERSATION: int = 3600

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # LLM (DeepSeek, OpenAI-compatible)
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-v4-pro"

    # Amap (高德地图)
    AMAP_API_KEY: Optional[str] = None

    # QWeather (和风天气)
    QWEATHER_API_KEY: Optional[str] = None

    # JWT
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72

    # Testing
    TESTING: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# Startup validation: warn about default secrets
_DEFAULT_SECRETS = ("dev-secret-change-in-production", "your_jwt_secret_key", "")
if settings.JWT_SECRET in _DEFAULT_SECRETS:
    warnings.warn(
        "WARNING: JWT_SECRET is set to a default/example value. "
        "This is insecure for production. Set a strong random value in .env",
        stacklevel=2,
    )
