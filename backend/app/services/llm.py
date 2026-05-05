"""LLM 服务 — DeepSeek API (OpenAI-compatible)"""
import hashlib
import json
import re
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.cache import get_str, set_str


class LLMService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
            timeout=60,
        )
        self.model = settings.LLM_MODEL

    def _cache_key(self, system_prompt: str, messages: list[dict], max_tokens: int, temperature: float) -> str:
        """Generate deterministic cache key from prompt + messages."""
        raw = f"{system_prompt}|||{json.dumps(messages, sort_keys=True, ensure_ascii=False)}|||{max_tokens}|||{temperature}"
        return f"llm:chat:{hashlib.md5(raw.encode()).hexdigest()}"

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Send a chat request and return the response text."""
        # Check Redis cache for default-param calls
        use_cache = max_tokens == 4096 and temperature == 0.7
        if use_cache:
            cache_key = self._cache_key(system_prompt, messages, max_tokens, temperature)
            cached = await get_str(cache_key)
            if cached is not None:
                return cached

        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=60,
        )
        text = resp.choices[0].message.content or ""

        if use_cache and text:
            await set_str(cache_key, text, ttl=3600)

        return text

    async def chat_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ):
        """Stream response."""
        openai_messages = [{"role": "system", "content": system_prompt}]
        openai_messages.extend(messages)

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

    async def extract_json(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 512,
    ) -> dict:
        """Get a structured JSON response."""
        openai_messages = [
            {"role": "system", "content": system_prompt + "\n\nRespond ONLY with valid JSON. No markdown fences, no other text."},
        ]
        openai_messages.extend(messages)

        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=0.2,
            timeout=30,
        )
        text = resp.choices[0].message.content or ""

        # Defensive JSON extraction
        text = text.strip()
        if text.startswith("```"):
            # Remove markdown fences
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        return json.loads(text)


llm_service = LLMService()
