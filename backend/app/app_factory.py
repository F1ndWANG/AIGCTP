import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.ops import api_router as ops_api_router
from app.api.ops import root_router as ops_root_router
from app.api.router import api_router
from app.core.app_info import fastapi_metadata
from app.core.config import settings
from app.core.http_paths import API_V1_PREFIX
from app.core.logging import get_logger
from app.core.metrics import MetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_size import RequestSizeLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.bootstrap import shutdown, startup


logger = get_logger(__name__)


def _init_observability() -> None:
    if not (settings.SENTRY_DSN and settings.is_production):
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=0.2,
        )
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning("Sentry init failed: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await startup()
    yield
    await shutdown()


def create_app() -> FastAPI:
    _init_observability()
    app = FastAPI(
        **fastapi_metadata(),
        lifespan=lifespan,
    )
    _register_middleware(app)
    _register_routes(app)
    return app


def _register_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _register_routes(app: FastAPI) -> None:
    app.include_router(ops_root_router)
    app.include_router(api_router, prefix=API_V1_PREFIX)
    app.include_router(ops_api_router, prefix=API_V1_PREFIX)
