"""Intent-to-agent dispatching.

The supervisor decides *what* the user wants. This dispatcher owns *which*
domain agent to call and how to gather the minimal domain context needed.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import commerce_agent, diet_agent, restaurant_agent, travel_agent
from app.agents.cross_domain import cross_domain_composer
from app.agents.domain_results import to_legacy_payload
from app.models.diet import HealthProfile, MealRecord
from app.services.context_builder import build_preferences
from app.services.llm import llm_service
from app.services.travel_text import (
    DEFAULT_CITY,
    KNOWN_CITIES,
    extract_days,
    extract_destination,
    extract_destination_from_messages,
    general_chat_system_prompt,
    llm_extract_destination,
)


THINKING_LABELS = {
    "travel_plan": "正在规划行程...",
    "travel_adjust": "正在调整行程...",
    "travel_query": "正在查看行程...",
    "diet_recommend": "正在分析饮食需求...",
    "diet_log": "正在记录饮食...",
    "diet_analyze": "正在分析营养数据...",
    "restaurant_recommend": "正在搜索餐厅...",
    "commerce_recommend": "正在搜索推荐商品...",
    "auto_cart": "正在处理购物请求...",
    "quick_reorder": "正在查找历史订单...",
}


def thinking_label_for_intent(intent: str) -> str:
    return THINKING_LABELS.get(intent, "正在处理...")


class AgentDispatcher:
    async def dispatch(
        self,
        *,
        intent: str,
        extracted: dict[str, Any],
        user_message: str,
        messages: list[dict],
        context: dict[str, Any],
        user_id: int,
        db: AsyncSession,
        progress_reporter: "ProgressReporter | None" = None,
    ) -> dict[str, Any]:
        if intent == "clarification":
            return {"response": extracted.get("question", "请提供更多信息，我来帮你安排。")}

        preferences = build_preferences(context)
        travel_memory = context.get("travel_memory", {}) or {}
        avoid_pois = list(travel_memory.get("avoid_pois", []) or [])

        if intent == "travel_plan":
            destination = extracted.get("destination") or extract_destination(user_message)
            days = extracted.get("days") or extract_days(user_message) or 3
            result = to_legacy_payload(await travel_agent.plan_trip(
                destination=destination,
                days=days,
                user_id=user_id,
                db=db,
                user_preferences=preferences,
                original_message=user_message,
                reporter=progress_reporter,
                conversation_messages=messages,
                avoid_pois=avoid_pois,
            ))
            result = await cross_domain_composer.merge(
                result,
                destination=destination,
                extracted=extracted,
                user_id=user_id,
                db=db,
                context=context,
            )
            if result.get("travel_plan"):
                suggestions = []
                if "restaurants" not in result:
                    suggestions.append("- 需要推荐当地美食餐厅吗？")
                suggestions.append("- 看看旅行装备和当地特产")
                suggestions.append("- 到行程页面查看详细地图路线")
                result["response"] = result.get("response", "") + "\n\n" + "-" * 20 + "\n\n**接下来你可以：**\n" + "\n".join(suggestions)
            return result

        if intent == "travel_query" and context.get("current_travel_plan"):
            return _answer_plan_query(user_message, context["current_travel_plan"])

        if intent == "travel_adjust" and context.get("current_travel_plan"):
            return await self._dispatch_travel_adjust(
                user_message=user_message,
                messages=messages,
                context=context,
                user_id=user_id,
                db=db,
                preferences=preferences,
                progress_reporter=progress_reporter,
            )

        if intent == "diet_recommend":
            return await self._dispatch_diet_recommend(user_message, user_id, db)

        if intent == "diet_log":
            return to_legacy_payload(await diet_agent.log_meal(user_id=user_id, user_message=user_message, db=db))

        if intent == "diet_analyze":
            recent_meals = await self._load_recent_meal_dicts(user_id, db, limit=30)
            return to_legacy_payload(await diet_agent.analyze_nutrition(user_message=user_message, meal_records=recent_meals))

        if intent == "restaurant_recommend":
            return await self._dispatch_restaurant_recommend(
                user_message=user_message,
                extracted=extracted,
                context=context,
                user_id=user_id,
                db=db,
            )

        if intent == "commerce_recommend":
            return to_legacy_payload(await commerce_agent.commerce_recommend(
                user_message=user_message,
                user_id=user_id,
                db=db,
                session_id=context.get("session_id"),
            ))

        if intent == "auto_cart":
            return to_legacy_payload(await commerce_agent.auto_cart(
                user_message=user_message,
                user_id=user_id,
                context=context,
                db=db,
            ))

        if intent == "quick_reorder":
            return to_legacy_payload(await commerce_agent.quick_reorder(user_id=user_id, db=db))

        return await self._dispatch_general_chat(messages)

    async def _dispatch_travel_adjust(
        self,
        *,
        user_message: str,
        messages: list[dict],
        context: dict[str, Any],
        user_id: int,
        db: AsyncSession,
        preferences: dict[str, Any],
        progress_reporter: "ProgressReporter | None" = None,
    ) -> dict[str, Any]:
        plan = context["current_travel_plan"]

        # Quick query detection: if the user is just asking about the plan (not modifying it),
        # respond directly without triggering heavy re-planning.
        if _is_plan_query(user_message):
            return await _answer_plan_query(user_message, plan)

        new_dest = extract_destination(user_message)
        if new_dest == DEFAULT_CITY:
            new_dest = extract_destination_from_messages(messages)
        if (not new_dest or new_dest == DEFAULT_CITY) and messages:
            new_dest = await llm_extract_destination(user_message, messages)
        # Only trigger full re-plan if user explicitly wants a different city
        if new_dest and new_dest != plan["destination"] and new_dest in KNOWN_CITIES:
            days = extract_days(user_message) or plan["days"] or 3
            if progress_reporter:
                await progress_reporter.step(f"正在规划{new_dest}的行程...")
            return to_legacy_payload(await travel_agent.plan_trip(
                destination=new_dest,
                days=days,
                user_id=user_id,
                db=db,
                user_preferences=preferences,
                original_message=user_message,
                reporter=progress_reporter,
                conversation_messages=messages,
                avoid_pois=list(context.get("travel_memory", {}).get("avoid_pois", []) or []),
            ))

        return to_legacy_payload(await travel_agent.adjust_plan(
            plan_id=plan["id"],
            instruction=user_message,
            current_itinerary=plan.get("itinerary", {}),
            destination=plan["destination"],
            days=plan["days"],
            db=db,
            user_id=user_id,
            reporter=progress_reporter,
            conversation_messages=messages,
            avoid_pois=list(context.get("travel_memory", {}).get("avoid_pois", []) or []),
        ))

    async def _dispatch_diet_recommend(
        self,
        user_message: str,
        user_id: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        hp_result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        hp = hp_result.scalar_one_or_none()
        recent_meals = await self._load_recent_meal_records(user_id, db, limit=14)
        wants_plan = diet_agent._wants_diet_plan(user_message)

        result = await diet_agent.recommend_diet(
            user_message=user_message,
            user_id=user_id,
            db=db,
            health_profile=hp,
            meal_records=recent_meals,
            wants_plan=wants_plan,
        )
        if hp is None:
            result.response = result.response + (
                "\n\n---\n"
                "提示：在「饮食健康」页面设置健康档案（身高、体重、过敏源、饮食目标等），"
                "我可以为你提供更精准的饮食建议。"
            )
        return to_legacy_payload(result)

    async def _dispatch_restaurant_recommend(
        self,
        *,
        user_message: str,
        extracted: dict[str, Any],
        context: dict[str, Any],
        user_id: int,
        db: AsyncSession,
    ) -> dict[str, Any]:
        city = extracted.get("destination") or extracted.get("city") or ""
        cuisine = extracted.get("cuisine")
        hp_result = await db.execute(select(HealthProfile).where(HealthProfile.user_id == user_id))
        hp = hp_result.scalar_one_or_none()
        dietary_restrictions = hp.dietary_restrictions if hp else None

        if "附近" in user_message and not city:
            user_city = context.get("user_preferences", {}).get("city", "")
            if user_city:
                city = user_city

        return to_legacy_payload(await restaurant_agent.recommend_restaurants(
            city=city or context.get("user_preferences", {}).get("city", DEFAULT_CITY),
            user_message=user_message,
            cuisine=cuisine,
            dietary_restrictions=dietary_restrictions,
            db=db,
        ))

    async def _dispatch_general_chat(self, messages: list[dict]) -> dict[str, Any]:
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = await llm_service.chat(
            system_prompt=general_chat_system_prompt(),
            messages=clean_messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return {"response": resp}

    async def _load_recent_meal_records(
        self,
        user_id: int,
        db: AsyncSession,
        *,
        limit: int,
    ) -> list[MealRecord]:
        result = await db.execute(
            select(MealRecord).where(MealRecord.user_id == user_id).order_by(MealRecord.date.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def _load_recent_meal_dicts(
        self,
        user_id: int,
        db: AsyncSession,
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        records = await self._load_recent_meal_records(user_id, db, limit=limit)
        return [
            {
                "date": str(record.date),
                "meal_type": record.meal_type,
                "foods": record.foods,
                "total_nutrition": record.total_nutrition,
            }
            for record in records
        ]


QUERY_KEYWORDS = (
    "今天", "明天", "后天", "安排", "有什么", "怎么玩",
    "第", "天去哪", "天去", "天玩", "行程是什么", "行程怎么",
    "安排什么", "看下", "显示", "列出", "怎么走",
)


def _is_plan_query(message: str) -> bool:
    """Detect if the user is just asking about the current plan, not modifying it."""
    adjust_keywords = (
        "换", "改", "加", "删", "移除", "去掉", "不想去", "不去",
        "重新", "调整", "修改", "更新", "替换", "增加", "添加",
    )
    if any(kw in message for kw in adjust_keywords):
        return False
    return any(kw in message for kw in QUERY_KEYWORDS)


def _answer_plan_query(message: str, plan: dict) -> dict[str, Any]:
    """Quickly answer a query about the current plan without re-planning."""
    itinerary = plan.get("itinerary", {}) or {}
    day_by_day = itinerary.get("day_by_day", []) or []

    # Extract target day
    target_day = None
    day_map = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "1": 0, "2": 1, "3": 2, "4": 3, "5": 4}
    for key, idx in day_map.items():
        if f"第{key}天" in message:
            target_day = day_by_day[idx] if idx < len(day_by_day) else None
            break

    # If "今天" or no specific day, show all
    if target_day is None:
        lines = [f"你的{plan['destination']}行程（共{plan['days']}天）:"]
        for day in day_by_day:
            day_num = day.get("day", "?")
            day_theme = day.get("theme", "")
            lines.append(f"\n**第{day_num}天: {day_theme}**")
            weather = day.get("weather", {})
            if weather.get("condition"):
                lines.append(f"  天气: {weather.get('condition')} {weather.get('temp_min','')}~{weather.get('temp_max','')}°C")
            for act in day.get("activities", []) or []:
                lines.append(f"  - {act.get('time','')}: {act.get('poi','')} ({act.get('duration','')})")
        return {"response": "\n".join(lines)}

    # Show specific day
    day_num = target_day.get("day", "?")
    day_theme = target_day.get("theme", "")
    lines = [f"**第{day_num}天: {day_theme}**"]
    weather = target_day.get("weather", {})
    if weather.get("condition"):
        lines.append(f"天气: {weather.get('condition')} {weather.get('temp_min','')}~{weather.get('temp_max','')}°C")
    lines.append("")
    for act in target_day.get("activities", []) or []:
        lines.append(f"- {act.get('time','')}: {act.get('poi','')} ({act.get('duration','')})")
        if act.get("description"):
            lines.append(f"  {act.get('description','')}")
    lines.append("")
    for meal in target_day.get("meals", []) or []:
        lines.append(f"- {meal.get('type','')}: {meal.get('restaurant','')} — {meal.get('recommendation','')}")
    return {"response": "\n".join(lines)}


agent_dispatcher = AgentDispatcher()
