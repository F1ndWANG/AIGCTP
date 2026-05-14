from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.http_paths import HEALTH_PATH, LLM_HEALTH_PATH, METRICS_PATH, READY_PATH
from app.core.metrics import metrics_endpoint
from app.services.health import liveness_report, llm_health_report, readiness_report


root_router = APIRouter(tags=["operations"])
api_router = APIRouter(tags=["operations"])


@root_router.get(HEALTH_PATH)
async def health():
    """Fast liveness check."""
    return liveness_report()


@api_router.get(METRICS_PATH)
async def metrics(request: Request):
    return await metrics_endpoint(request)


@api_router.get(READY_PATH)
async def health_ready():
    """Readiness probe: checks DB and Redis connectivity."""
    report = await readiness_report()
    return JSONResponse(content=report, status_code=200 if report["ready"] else 503)


@api_router.get(LLM_HEALTH_PATH)
async def health_llm():
    """Check DeepSeek API connectivity with a lightweight ping."""
    return await llm_health_report()
