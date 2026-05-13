from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Any


TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return " ".join(normalize_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {normalize_text(v)}" for k, v in value.items())
    return str(value).lower()


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(normalize_text(text))
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if len(token) >= 4 and any("\u4e00" <= ch <= "\u9fff" for ch in token):
            expanded.extend(token[i : i + 2] for i in range(len(token) - 1))
    return [t for t in expanded if t.strip()]


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def token_vector(text: str) -> dict[str, float]:
    counter = Counter(tokenize(text))
    total = sum(counter.values()) or 1
    return {key: value / total for key, value in counter.items()}


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0
    keys = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in keys)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def text_similarity(text_a: str, text_b: str) -> float:
    return cosine_similarity(token_vector(text_a), token_vector(text_b))


def build_item_text(item: dict[str, Any]) -> str:
    metadata = item.get("metadata") or {}
    parts = [
        item.get("title"),
        item.get("subtitle"),
        item.get("description"),
        metadata.get("category"),
        metadata.get("city"),
        metadata.get("cuisine"),
        metadata.get("tags"),
        metadata.get("preferences"),
    ]
    return normalize_text(parts)
