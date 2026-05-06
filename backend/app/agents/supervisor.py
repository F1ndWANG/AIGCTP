"""
Supervisor Agent - 意图识别与路由分发

分析用户输入，判断意图并路由到对应的子 Agent。当前支持：
  - 旅行规划     -> travel_agent.plan_trip
  - 行程调整     -> travel_agent.adjust_plan
  - 饮食推荐     -> diet_agent.recommend_diet
  - 饮食记录     -> diet_agent.log_meal
  - 营养分析     -> diet_agent.analyze_nutrition
  - 餐厅推荐     -> restaurant_agent.recommend_restaurants
  - 商品推荐     -> commerce_agent.commerce_recommend
  - 通用问答     -> direct LLM

意图分类策略（混合）:
  1. 关键词快速路径（高置信度场景，零 LLM 开销）
  2. LLM 语义分类（模糊/复杂/复合意图）
  3. 参数提取（LLM + 关键词回退）
  4. 低置信度时主动追问确认
"""

import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dispatcher import agent_dispatcher, thinking_label_for_intent
from app.services.context_builder import has_current_travel_plan
from app.services.intent_classifier import classify as classify_intent
from app.services.intent_classifier import keyword_intent_score
from app.services.llm import llm_service
from app.services.travel_text import (
    extract_days,
    extract_destination,
    extract_destination_from_messages,
    general_chat_system_prompt,
    llm_extract_destination,
)


def _classify_intent(user_message: str, has_travel_plan: bool = False) -> tuple[str, dict]:
    """Synchronous compatibility wrapper for deterministic intent tests.

    Runtime routing uses the async hybrid classifier. This function exposes only
    the zero-LLM keyword path so tests and lightweight callers have a stable
    contract without needing an event loop or external model.
    """
    msg = user_message.strip()
    non_travel = keyword_intent_score(msg, has_travel_plan=False)
    if non_travel and non_travel["intent"] in {
        "quick_reorder",
        "auto_cart",
        "diet_log",
        "diet_analyze",
        "diet_recommend",
        "restaurant_recommend",
        "commerce_recommend",
    }:
        return non_travel["intent"], dict(non_travel.get("extracted") or {})

    if has_travel_plan:
        adjustment_markers = (
            "调整", "修改", "更新", "变动", "太赶", "换", "换成", "不想去",
            "玩过", "去过", "加上", "加入", "安排", "预算", "控制", "轻松",
        )
        if any(marker in msg for marker in adjustment_markers):
            return "travel_adjust", {}
        if re.search(r"(第[一二三四五六七八九\d]+天|上午|下午|晚上|中午|早上).*(去|加|安排|换)", msg):
            return "travel_adjust", {}
        if re.search(r"想去[一-鿿A-Za-z0-9·]{2,20}", msg):
            return "travel_adjust", {}

    result = keyword_intent_score(msg, has_travel_plan)
    if result:
        return result["intent"], dict(result.get("extracted") or {})
    return "general_chat", {}


async def _run_classifier(
    user_message: str,
    has_travel_plan: bool,
    force_travel_adjust: bool = False,
    recent_messages: list[dict] | None = None,
) -> tuple[str, dict]:
    """Unified intent classification: hybrid keyword + LLM semantic.

    Returns (intent, extracted_params) matching the original contract,
    preserving also_recommend_food/also_recommend_products conventions
    for cross-domain merging.
    """
    if force_travel_adjust and has_travel_plan:
        return "travel_adjust", {}

    result = await classify_intent(
        user_message,
        has_travel_plan=has_travel_plan,
        recent_messages=recent_messages,
    )
    intent = result["intent"]
    extracted: dict[str, Any] = dict(result["extracted"])

    # Preserve cross-domain conventions expected by downstream merge code
    if result.get("composite_intents"):
        extracted["also_recommend_food"] = "restaurant_recommend" in result["composite_intents"]
        extracted["also_recommend_products"] = "commerce_recommend" in result["composite_intents"]

    # Clarification: needs_clarification routes to a clarification response
    if result.get("needs_clarification") and intent not in ("general_chat", "clarification"):
        question = result.get("clarification_question", "")
        if question:
            return "clarification", {"question": question, "original_intent": intent}

    return intent, extracted


async def run_agent(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Analyze intent and route to the right agent."""
    has_travel_plan = has_current_travel_plan(context)
    intent, extracted = await _run_classifier(
        user_message,
        has_travel_plan,
        force_travel_adjust=bool(context.get("force_travel_adjust")),
        recent_messages=messages,
    )

    return await agent_dispatcher.dispatch(
        intent=intent,
        extracted=extracted,
        user_message=user_message,
        messages=messages,
        context=context,
        user_id=user_id,
        db=db,
    )


async def run_agent_stream(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
):
    """Streaming variant for SSE consumption."""
    yield {"type": "thinking", "content": "正在分析你的请求..."}

    has_travel_plan = has_current_travel_plan(context)
    intent, extracted = await _run_classifier(
        user_message,
        has_travel_plan,
        force_travel_adjust=bool(context.get("force_travel_adjust")),
        recent_messages=messages,
    )

    if intent == "clarification":
        yield {"type": "result", "content": {"response": extracted.get("question", "请提供更多信息。")}}
        yield {"type": "done"}
        return

    if intent == "general_chat":
        yield {"type": "thinking", "content": "正在思考..."}
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        async for token in llm_service.chat_stream(
            system_prompt=general_chat_system_prompt(),
            messages=clean_messages,
            max_tokens=1024,
            temperature=0.7,
        ):
            yield {"type": "token", "content": token}
    else:
        yield {"type": "thinking", "content": thinking_label_for_intent(intent)}
        result = await agent_dispatcher.dispatch(
            intent=intent,
            extracted=extracted,
            user_message=user_message,
            messages=messages,
            context=context,
            user_id=user_id,
            db=db,
        )
        yield {"type": "result", "content": result}

    yield {"type": "done"}


def _general_chat_system_prompt() -> str:
    return general_chat_system_prompt()


def _extract_destination_fallback(text: str) -> str:
    return extract_destination(text)


def _extract_days_fallback(text: str) -> int:
    return extract_days(text)


def _extract_cuisine(text: str) -> str | None:
    cuisine_keywords = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "火锅", "烧烤", "日料", "韩餐", "西餐", "甜品", "咖啡", "奶茶",
        "海鲜", "素食", "小吃", "面食", "麻辣", "清淡",
    ]
    for keyword in cuisine_keywords:
        if keyword in text:
            return keyword
    return None


def _extract_destination_from_messages(messages: list[dict]) -> str | None:
    return extract_destination_from_messages(messages)


async def _llm_extract_destination(user_message: str, messages: list[dict]) -> str | None:
    return await llm_extract_destination(user_message, messages)
