"""Composition for multi-domain agent results."""
from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import commerce_agent
from app.agents.domain_results import to_legacy_payload


class CrossDomainComposer:
    async def merge(
        self,
        result: dict[str, Any],
        *,
        destination: str,
        extracted: dict[str, Any],
        user_id: int,
        db: AsyncSession,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        also_products = extracted.get("also_recommend_products")
        if not also_products:
            return result

        extra_parts: list[str] = []
        tasks = [
            commerce_agent.commerce_recommend(
                user_message=f"去 {destination} 旅游，推荐旅行装备、当地特产和纪念品，与行程相关的实用好物",
                user_id=user_id,
                db=db,
                session_id=context.get("session_id"),
            )
        ]

        extra_results = await asyncio.gather(*tasks, return_exceptions=True)
        for item in extra_results:
            if not isinstance(item, Exception):
                item = to_legacy_payload(item)
            if isinstance(item, dict) and item.get("response"):
                extra_parts.append(item["response"])
                if item.get("products"):
                    result["products"] = item["products"]

        if extra_parts:
            result["response"] = result["response"] + "\n\n---\n\n## 旅行装备推荐\n\n" + "\n\n".join(extra_parts)
        return result


cross_domain_composer = CrossDomainComposer()
