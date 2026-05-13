from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.recommendation import RecommendationEmbedding, RecommendationFeedLog
from app.models.user import User
from app.services.recommendation.candidate import collect_domain_candidates
from app.services.recommendation.embeddings import build_item_text, text_hash, token_vector
from app.services.recommendation.events import record_event
from app.services.recommendation.explain import explain_item
from app.services.recommendation.profile import build_user_profile
from app.services.recommendation.ranker import rank_candidates


class RecommendationService:
    algorithm = "hybrid_v1"

    async def profile_insights(self, db: AsyncSession, *, user: User) -> dict[str, Any]:
        profile = await build_user_profile(db, user)
        return {
            "algorithm": self.algorithm,
            "event_count": int(profile.get("event_count") or 0),
            "top_terms": [
                {"term": term, "weight": round(float(weight), 3)}
                for term, weight in sorted((profile.get("terms") or {}).items(), key=lambda item: item[1], reverse=True)[:16]
            ],
            "domain_terms": {
                domain: [
                    {"term": term, "weight": round(float(weight), 3)}
                    for term, weight in sorted(values.items(), key=lambda item: item[1], reverse=True)[:8]
                ]
                for domain, values in (profile.get("domain_terms") or {}).items()
            },
            "negative_item_count": len(profile.get("negative_items") or []),
            "preferences": profile.get("preferences") or {},
        }

    async def track(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        domain: str,
        item_type: str,
        item_id: str | int,
        event_type: str,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        weight: float | None = None,
        commit: bool = True,
    ):
        return await record_event(
            db,
            user_id=user_id,
            domain=domain,
            item_type=item_type,
            item_id=item_id,
            event_type=event_type,
            context=context,
            session_id=session_id,
            weight=weight,
            commit=commit,
        )

    async def recommend(
        self,
        db: AsyncSession,
        *,
        user: User,
        domain: str = "home",
        limit: int | None = None,
        context: dict[str, Any] | None = None,
        log: bool = True,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(limit or settings.RECOMMENDATION_DEFAULT_LIMIT, 50))
        profile = await build_user_profile(db, user)
        candidates = await collect_domain_candidates(db, user_id=user.id, domain=domain, limit=limit)
        return await self.rank_candidates(
            db,
            user=user,
            domain=domain,
            candidates=candidates,
            limit=limit,
            context=context or {},
            profile=profile,
            log=log,
        )

    async def rank_candidates(
        self,
        db: AsyncSession,
        *,
        user: User,
        domain: str,
        candidates: list[dict[str, Any]],
        limit: int,
        context: dict[str, Any] | None = None,
        profile: dict[str, Any] | None = None,
        log: bool = False,
    ) -> list[dict[str, Any]]:
        profile = profile or await build_user_profile(db, user)
        ranked = rank_candidates(candidates, profile=profile, context=context or {}, limit=limit)
        items: list[dict[str, Any]] = []
        for item in ranked:
            item = {k: v for k, v in item.items() if k not in {"_text"}}
            score = float((item.get("_scores") or {}).get("final_score", 0.0))
            item["score"] = round(score, 4)
            item["reason"] = explain_item(item, profile)
            items.append(item)

        if log:
            db.add(
                RecommendationFeedLog(
                    user_id=user.id,
                    domain=domain,
                    request_context=context or {},
                    results=[
                        {
                            "domain": item["domain"],
                            "item_type": item["item_type"],
                            "item_id": item["item_id"],
                            "score": item["score"],
                            "reason": item["reason"],
                            "sources": item.get("_scores") or {},
                        }
                        for item in items
                    ],
                )
            )
            await db.commit()
        return [{k: v for k, v in item.items() if k != "_scores"} for item in items]

    async def refresh_embeddings(
        self,
        db: AsyncSession,
        *,
        user: User,
        domain: str | None = None,
        item_ids: list[str] | None = None,
    ) -> int:
        domains = [domain] if domain else ["commerce", "restaurant", "travel", "diet"]
        total = 0
        for current_domain in domains:
            candidates = await collect_domain_candidates(db, user_id=user.id, domain=current_domain, limit=200)
            for item in candidates:
                if item_ids and item["item_id"] not in item_ids:
                    continue
                text = build_item_text(item)
                current_text_hash = text_hash(text)
                vector = token_vector(text)
                result = await db.execute(
                    select(RecommendationEmbedding).where(
                        RecommendationEmbedding.domain == item["domain"],
                        RecommendationEmbedding.item_type == item["item_type"],
                        RecommendationEmbedding.item_id == item["item_id"],
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.text_hash = current_text_hash
                    existing.embedding = vector
                    existing.model = "local-token-vector"
                else:
                    db.add(
                        RecommendationEmbedding(
                            domain=item["domain"],
                            item_type=item["item_type"],
                            item_id=item["item_id"],
                            text_hash=current_text_hash,
                            embedding=vector,
                            model="local-token-vector",
                        )
                    )
                total += 1
        await db.commit()
        return total
