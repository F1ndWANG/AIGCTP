import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import async_session, init_db
from app.core.redis import close_redis, get_redis
from app.core.logging import setup_logging, get_logger
from app.api import auth, users, travel, chat, route, diet, commerce, feedback, restaurant, runtime
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.demo_catalog import ensure_demo_catalog

logger = get_logger(__name__)


# ── Sentry (production only) ──
if settings.SENTRY_DSN and settings.is_production:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            traces_sample_rate=0.2,
        )
        logger.info("Sentry initialized")
    except Exception as e:
        logger.warning("Sentry init failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.DEBUG, app_env=settings.APP_ENV)
    await init_db()
    async with async_session() as db:
        await ensure_demo_catalog(db)
    yield
    await close_redis()


app = FastAPI(
    title="AIGCTP — AI Life Recommender API",
    description="""Multi-agent lifestyle recommendation platform.

    Features:
    * **Travel Planning** — multi-day itinerary generation with POI, weather, budget
    * **Diet & Nutrition** — meal logging, nutrition analysis, diet plan generation
    * **Restaurant Recommendations** — personalised restaurant search
    * **Commerce** — product recommendations, shopping cart, ordering
    * **Multi-Agent Architecture** — supervisor classifies intent, dispatcher routes to domain agents
    * **Async Workers** — arq-powered background job queue for heavy operations
    """,
    version="0.1.0",
    contact={"name": "AIGCTP Team", "url": "https://github.com/your-org/aigctp"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from app.middleware.request_size import RequestSizeLimitMiddleware
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

from app.core.metrics import MetricsMiddleware
app.add_middleware(MetricsMiddleware)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Inject request_id into request state and response header."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(travel.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(route.router, prefix="/api/v1")
app.include_router(diet.router, prefix="/api/v1")
app.include_router(commerce.router, prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(restaurant.router, prefix="/api/v1")
app.include_router(runtime.router, prefix="/api/v1")


@app.get("/api/v1/metrics")
async def metrics():
    from app.core.metrics import metrics_endpoint
    from fastapi import Request
    return await metrics_endpoint(Request({"type": "http", "method": "GET", "path": "/api/v1/metrics"}))


@app.get("/health")
async def health():
    """Fast liveness check."""
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.1.0"}


@app.get("/api/v1/health/ready")
async def health_ready():
    """Readiness probe: checks DB and Redis connectivity."""
    from sqlalchemy import text as sa_text

    checks = {"database": False, "redis": False}

    # Check database
    try:
        async with async_session() as db:
            await db.execute(sa_text("SELECT 1"))
            checks["database"] = True
    except Exception as e:
        checks["database_error"] = str(e)[:100]

    # Check Redis
    try:
        r = await get_redis()
        if r:
            await r.ping()
            checks["redis"] = True
            checks["redis_backend"] = type(r).__name__
    except Exception as e:
        checks["redis_error"] = str(e)[:100]

    redis_required = settings.is_production
    all_healthy = checks["database"] and (checks["redis"] or not redis_required)
    status_code = 200 if all_healthy else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "status": "ok" if checks["database"] and checks["redis"] else "degraded",
            "ready": all_healthy,
            "redis_required": redis_required,
            "checks": checks,
        },
        status_code=status_code,
    )


@app.get("/api/v1/health/llm")
async def health_llm():
    """Check DeepSeek API connectivity with a lightweight ping."""
    import asyncio
    try:
        from app.services.llm import llm_service
        ok = await asyncio.wait_for(
            llm_service.client.chat.completions.create(
                model=llm_service.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
                temperature=0,
                timeout=5,
            ),
            timeout=8,
        )
        text = ok.choices[0].message.content if ok.choices else ""
        return {
            "status": "ok",
            "model": llm_service.model,
            "base_url": settings.LLM_API_BASE,
            "latency_check": "connected",
        }
    except Exception as e:
        return {
            "status": "error",
            "model": settings.LLM_MODEL,
            "base_url": settings.LLM_API_BASE,
            "error": str(e)[:200],
        }
