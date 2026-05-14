"""Shared HTTP path constants used by routers and middleware."""

API_V1_PREFIX = "/api/v1"

HEALTH_PATH = "/health"
METRICS_PATH = "/metrics"
READY_PATH = "/health/ready"
LLM_HEALTH_PATH = "/health/llm"

API_METRICS_PATH = f"{API_V1_PREFIX}{METRICS_PATH}"
API_READY_PATH = f"{API_V1_PREFIX}{READY_PATH}"
API_LLM_HEALTH_PATH = f"{API_V1_PREFIX}{LLM_HEALTH_PATH}"

RATE_LIMIT_EXEMPT_PATHS = frozenset({
    HEALTH_PATH,
    API_READY_PATH,
    API_LLM_HEALTH_PATH,
})

METRICS_EXEMPT_PATHS = frozenset({
    API_METRICS_PATH,
    METRICS_PATH,
})
