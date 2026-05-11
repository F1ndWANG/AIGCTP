"""LLM 服务 — DeepSeek API (OpenAI-compatible) with circuit breaker, retry, and fallback.

Features:
- Exponential backoff retry (transient errors only)
- Error classification (retryable vs non-retryable)
- Circuit breaker (5 failures -> open 30s -> half-open)
- Optional fallback model when primary is unavailable
- Response caching for default params
"""
import asyncio
import hashlib
import json
import re
import time

from openai import AsyncOpenAI
from openai import (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

from app.core.config import settings
from app.core.cache import get_str, set_str
from app.core.logging import get_logger

from app.core.metrics import (
    llm_calls_total,
    llm_call_duration_seconds,
    llm_cache_hits,
    llm_cache_misses,
    llm_circuit_breaker_state,
)

logger = get_logger(__name__)


# ── Error classification ──────────────────────────────────────────


def _is_retryable(err: Exception) -> bool:
    """Return True if the error is transient and retrying may help."""
    if isinstance(err, (APITimeoutError, APIConnectionError, InternalServerError)):
        return True
    if isinstance(err, RateLimitError):
        return True
    # Circuit breaker is our own exception — not retryable here
    return False


# ── Circuit Breaker ───────────────────────────────────────────────


class CircuitBreaker:
    """Simple circuit breaker: fail fast after N consecutive failures."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._last_failure_time = 0.0
        self._state: str = "closed"  # closed / open / half_open
        self._update_metric()

    def _update_metric(self) -> None:
        value = {"closed": 0.0, "half_open": 0.5, "open": 1.0}.get(self._state, 0.0)
        llm_circuit_breaker_state.set(value)

    @property
    def is_open(self) -> bool:
        if self._state == "closed":
            return False
        if self._state == "open":
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                self._state = "half_open"
                self._update_metric()
                logger.info("Circuit breaker: open -> half_open")
                return False
            return True
        return False

    def success(self) -> None:
        if self._state != "closed":
            logger.info("Circuit breaker: reset to closed")
        self._state = "closed"
        self._failures = 0
        self._update_metric()

    def failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._failures >= self.failure_threshold:
            self._state = "open"
            self._update_metric()
            logger.warning("Circuit breaker: opened after %d failures", self._failures)


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open."""
    pass


# ── LLM Service ───────────────────────────────────────────────────


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
            timeout=60,
        )
        self.model = settings.LLM_MODEL
        self.fallback_model = settings.LLM_FALLBACK_MODEL
        self.circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        self._max_retries = 2
        self._retry_base_delay = 1.0  # seconds

    def _cache_key(self, system_prompt: str, messages: list[dict], max_tokens: int, temperature: float) -> str:
        raw = f"{system_prompt}|||{json.dumps(messages, sort_keys=True, ensure_ascii=False)}|||{max_tokens}|||{temperature}"
        return f"llm:chat:{hashlib.md5(raw.encode()).hexdigest()}"

    def _check_circuit(self) -> None:
        if self.circuit.is_open:
            raise CircuitBreakerOpen("LLM service temporarily unavailable — circuit breaker open")

    async def _call_with_retry(
        self,
        method_name: str,
        factory,
        *,
        max_retries: int | None = None,
    ) -> str:
        """Execute an LLM call with exponential backoff retry.

        Only retries on transient errors (timeout, connection, 5xx, rate-limit).
        Non-retryable errors (auth, bad-request) propagate immediately.
        """
        retries = max_retries if max_retries is not None else self._max_retries
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            try:
                result = await factory()
                self.circuit.success()
                return result
            except CircuitBreakerOpen:
                raise
            except Exception as e:
                last_error = e

                if _is_retryable(e) and attempt < retries:
                    delay = self._retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs",
                        method_name, attempt + 1, retries + 1,
                        e.__class__.__name__, delay,
                    )
                    await asyncio.sleep(delay)
                elif not _is_retryable(e):
                    logger.warning(
                        "%s failed with non-retryable error: %s",
                        method_name, e.__class__.__name__,
                    )
                    raise
                else:
                    self.circuit.failure()
                    logger.warning(
                        "%s failed after %d attempts: %s",
                        method_name, retries + 1, e.__class__.__name__,
                    )
                    raise

        # Should not reach here
        raise last_error or RuntimeError(f"{method_name} failed unexpectedly")

    async def _call_with_fallback(
        self,
        method_name: str,
        factory,
        *,
        max_retries: int | None = None,
    ) -> str:
        """Call LLM with retry, falling back to alternate model on failure."""
        try:
            return await self._call_with_retry(method_name, factory, max_retries=max_retries)
        except (APITimeoutError, APIConnectionError, InternalServerError, RateLimitError, CircuitBreakerOpen):
            if self.fallback_model:
                original_model = self.model
                self.model = self.fallback_model
                logger.warning(
                    "%s: falling back from %s to %s",
                    method_name, original_model, self.fallback_model,
                )
                try:
                    result = await self._call_with_retry(
                        f"{method_name}[fallback]", factory, max_retries=1,
                    )
                    return result
                finally:
                    self.model = original_model
            raise

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self._check_circuit()

        use_cache = max_tokens == 4096 and temperature == 0.7
        if use_cache:
            cache_key = self._cache_key(system_prompt, messages, max_tokens, temperature)
            cached = await get_str(cache_key)
            if cached is not None:
                llm_cache_hits.inc()
                return cached

        llm_cache_misses.inc()

        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)

        async def _do_chat() -> str:
            start = time.monotonic()
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=60,
            )
            llm_call_duration_seconds.labels(method="chat").observe(time.monotonic() - start)
            text = resp.choices[0].message.content or ""
            if use_cache and text:
                await set_str(cache_key, text, ttl=settings.REDIS_TTL_LLM_CHAT)
            llm_calls_total.labels(method="chat", status="success").inc()
            return text

        try:
            return await self._call_with_fallback("chat", _do_chat)
        except Exception:
            llm_calls_total.labels(method="chat", status="error").inc()
            raise

    async def chat_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        self._check_circuit()

        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)

        start = time.monotonic()
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                timeout=60,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
            self.circuit.success()
            llm_call_duration_seconds.labels(method="chat_stream").observe(time.monotonic() - start)
            llm_calls_total.labels(method="chat_stream", status="success").inc()
        except CircuitBreakerOpen:
            raise
        except Exception:
            self.circuit.failure()
            llm_calls_total.labels(method="chat_stream", status="error").inc()
            raise

    async def extract_json(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 2048,
    ) -> dict:
        self._check_circuit()

        openai_messages = [
            {"role": "system", "content": system_prompt + "\n\nRespond ONLY with valid JSON. No markdown fences, no other text."},
        ]
        openai_messages.extend(messages)

        async def _do_extract() -> dict:
            start = time.monotonic()
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                max_tokens=max_tokens,
                temperature=0.2,
                timeout=30,
            )
            llm_call_duration_seconds.labels(method="extract_json").observe(time.monotonic() - start)
            text = resp.choices[0].message.content or ""
            text = text.strip()
            if not text:
                raise ValueError("LLM returned empty JSON response")
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            return json.loads(text)

        try:
            result = await self._call_with_fallback("extract_json", _do_extract, max_retries=1)
            llm_calls_total.labels(method="extract_json", status="success").inc()
            return result
        except Exception:
            llm_calls_total.labels(method="extract_json", status="error").inc()
            raise

    async def chat_with_artifact(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> dict:
        """Generate text response + optional JSON artifact in a single call."""
        self._check_circuit()

        artifact_system = (
            system_prompt + "\n\n"
            "When you include structured data (travel plan, diet plan, products), "
            "append it at the end as a JSON code block:\n"
            "```json\n{...}\n```\n"
            "If no structured data is needed, omit the JSON block."
        )
        openai_messages = [{"role": "system", "content": artifact_system}]
        openai_messages.extend(messages)

        async def _do_artifact() -> str:
            start = time.monotonic()
            resp = await self.client.chat.completions.create(
                model=self.model, messages=openai_messages,
                max_tokens=max_tokens, temperature=temperature, timeout=45,
            )
            llm_call_duration_seconds.labels(method="chat_with_artifact").observe(time.monotonic() - start)
            return resp.choices[0].message.content or ""

        try:
            text = await self._call_with_fallback("chat_with_artifact", _do_artifact)
            llm_calls_total.labels(method="chat_with_artifact", status="success").inc()
            return _parse_artifact_response(text)
        except Exception:
            llm_calls_total.labels(method="chat_with_artifact", status="error").inc()
            raise


def _parse_artifact_response(text: str) -> dict:
    """Extract JSON artifact from a code-fence-terminated response."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if m:
        text_part = text[:m.start()].strip()
        try:
            return {"text": text_part, "artifact": json.loads(m.group(1).strip())}
        except (json.JSONDecodeError, ValueError):
            pass
    return {"text": text, "artifact": None}


llm_service = LLMService()
