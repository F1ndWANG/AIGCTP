"""Tests for LLM service: error classification, circuit breaker, cache key."""
import time

from app.services.llm import _is_retryable, CircuitBreaker, CircuitBreakerOpen
from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
    AuthenticationError,
    BadRequestError,
)


# Helper: mock request/response objects for OpenAI exception constructors
class _MockRequest:
    def __init__(self):
        self.method = "POST"
        self.url = "http://test"


class _MockResponse:
    def __init__(self):
        self.status_code = 500
        self.request = _MockRequest()
        self.headers = {}
        self.http_version = "1.1"

    def raise_for_status(self):
        pass


_MOCK_REQ = _MockRequest()
_MOCK_RESP = _MockResponse()


class TestIsRetryable:
    def test_timeout_is_retryable(self):
        assert _is_retryable(APITimeoutError("timeout")) is True

    def test_connection_error_is_retryable(self):
        assert _is_retryable(APIConnectionError(message="connection failed", request=_MOCK_REQ)) is True

    def test_internal_server_error_is_retryable(self):
        assert _is_retryable(InternalServerError("500", response=_MOCK_RESP, body={})) is True

    def test_rate_limit_is_retryable(self):
        assert _is_retryable(RateLimitError("rate limited", response=_MOCK_RESP, body={})) is True

    def test_auth_error_not_retryable(self):
        assert _is_retryable(AuthenticationError("401", response=_MOCK_RESP, body={})) is False

    def test_bad_request_not_retryable(self):
        assert _is_retryable(BadRequestError("400", response=_MOCK_RESP, body={})) is False

    def test_generic_exception_not_retryable(self):
        assert _is_retryable(ValueError("generic")) is False


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
        assert cb._state == "closed"
        assert cb.is_open is False

    def test_open_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        cb.failure()
        assert cb.is_open is False
        cb.failure()
        assert cb.is_open is False
        cb.failure()
        assert cb._state == "open"
        assert cb.is_open is True

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
        cb.failure()
        cb.failure()
        assert cb._state == "open"
        time.sleep(0.15)
        assert cb.is_open is False
        assert cb._state == "half_open"

    def test_success_closes_circuit(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
        cb.failure()
        cb.failure()
        assert cb._state == "open"
        cb.success()
        assert cb._state == "closed"
        assert cb._failures == 0

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
        cb.failure()
        cb.failure()
        cb.success()
        assert cb._failures == 0
        assert cb.is_open is False

    def test_open_state_blocks_request(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=30.0)
        cb.failure()
        assert cb.is_open is True

    def test_circuit_breaker_open_exception(self):
        exc = CircuitBreakerOpen("breaker is open")
        assert isinstance(exc, Exception)
        assert str(exc) == "breaker is open"
