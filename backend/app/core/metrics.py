"""Prometheus metrics for the application.

Exposes:
- HTTP request count and latency (by path, method, status)
- LLM call count and latency (by method, success/failure)
- Active user/session gauge
- Cache hit/miss counters
"""
import time

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


# ── HTTP Metrics ──

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# ── LLM Metrics ──

llm_calls_total = Counter(
    "llm_calls_total",
    "Total LLM API calls",
    ["method", "status"],  # method: chat, chat_stream, extract_json, chat_with_artifact
)

llm_call_duration_seconds = Histogram(
    "llm_call_duration_seconds",
    "LLM API call duration in seconds",
    ["method"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 45.0, 60.0),
)

llm_cache_hits = Counter(
    "llm_cache_hits_total",
    "LLM response cache hits",
)

llm_cache_misses = Counter(
    "llm_cache_misses_total",
    "LLM response cache misses (served by API)",
)

llm_circuit_breaker_state = Gauge(
    "llm_circuit_breaker_state",
    "LLM circuit breaker state: 0=closed, 1=open, 0.5=half_open",
)

# ── Application Metrics ──

active_sessions = Gauge(
    "active_sessions_total",
    "Currently active chat sessions",
)

active_users = Gauge(
    "active_users_total",
    "Currently active users",
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records HTTP metrics for every request."""

    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path in ("/api/v1/metrics", "/metrics"):
            return await call_next(request)

        path = request.url.path
        method = request.method
        start = time.monotonic()

        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception:
            status = "500"
            raise
        finally:
            http_requests_total.labels(method=method, path=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, path=path).observe(
                time.monotonic() - start
            )


async def metrics_endpoint(request: Request):
    """Prometheus metrics scrape endpoint."""
    resp = Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    return resp
