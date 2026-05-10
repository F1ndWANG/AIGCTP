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
import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.dispatcher import agent_dispatcher, thinking_label_for_intent
from app.services.context_builder import has_current_travel_plan
from app.services.intent_classifier import classify as classify_intent
from app.services.llm import llm_service, CircuitBreakerOpen
from app.services.progress import ProgressReporter
from app.services.travel_text import general_chat_system_prompt


# ──────────────────────────────────────────────
# Synchronous keyword classifier (used by tests)
# ──────────────────────────────────────────────


def _classify_intent(user_message: str, has_travel_plan: bool = False) -> tuple[str, dict]:
    """Synchronous keyword-only classifier for deterministic tests.

    Production routing uses the async hybrid classifier (_run_classifier).
    Delegates to intent_classifier.keyword_intent_score as the single source of truth.
    """
    from app.services.intent_classifier import keyword_intent_score

    result = keyword_intent_score(user_message.strip(), has_travel_plan)
    if result:
        return result["intent"], dict(result.get("extracted") or {})
    return "general_chat", {}


# ──────────────────────────────────────────────
# Intent classification
# ──────────────────────────────────────────────


async def _run_classifier(
    user_message: str,
    has_travel_plan: bool,
    force_travel_adjust: bool = False,
    recent_messages: list[dict] | None = None,
) -> tuple[str, dict]:
    """Unified intent classification: hybrid keyword + LLM semantic."""
    if force_travel_adjust and has_travel_plan:
        return "travel_adjust", {}

    result = await classify_intent(
        user_message,
        has_travel_plan=has_travel_plan,
        recent_messages=recent_messages,
    )
    intent = result["intent"]
    extracted: dict[str, Any] = dict(result["extracted"])

    if result.get("composite_intents"):
        extracted["also_recommend_food"] = "restaurant_recommend" in result["composite_intents"]
        extracted["also_recommend_products"] = "commerce_recommend" in result["composite_intents"]

    if result.get("needs_clarification") and intent not in ("general_chat", "clarification"):
        question = result.get("clarification_question", "")
        if question:
            return "clarification", {"question": question, "original_intent": intent}

    return intent, extracted


# ──────────────────────────────────────────────
# Agent entry points
# ──────────────────────────────────────────────


async def run_agent(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Non-streaming entry point. Analyze intent and route to the right agent."""
    has_travel_plan = has_current_travel_plan(context)
    intent, extracted = await _run_classifier(
        user_message, has_travel_plan,
        force_travel_adjust=bool(context.get("force_travel_adjust")),
        recent_messages=messages,
    )
    return await agent_dispatcher.dispatch(
        intent=intent, extracted=extracted,
        user_message=user_message, messages=messages,
        context=context, user_id=user_id, db=db,
    )


async def run_agent_stream(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
):
    """Streaming entry point for SSE consumption with real-time progress events."""
    yield {"type": "thinking", "content": "正在分析你的请求..."}

    has_travel_plan = has_current_travel_plan(context)
    try:
        intent, extracted = await _run_classifier(
            user_message, has_travel_plan,
            force_travel_adjust=bool(context.get("force_travel_adjust")),
            recent_messages=messages,
        )
    except CircuitBreakerOpen:
        yield {"type": "result", "content": {"response": "AI 服务暂时不可用，请稍后重试。如果问题持续，请联系管理员。"}}
        yield {"type": "done"}
        return

    if intent == "clarification":
        yield {"type": "result", "content": {"response": extracted.get("question", "请提供更多信息。")}}
        yield {"type": "done"}
        return

    if intent == "general_chat":
        yield {"type": "thinking", "content": "正在思考..."}
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        try:
            async for token in llm_service.chat_stream(
                system_prompt=general_chat_system_prompt(),
                messages=clean_messages,
                max_tokens=1024,
                temperature=0.7,
            ):
                yield {"type": "token", "content": token}
        except CircuitBreakerOpen:
            yield {"type": "result", "content": {"response": "AI 服务暂时不可用，请稍后重试。"}}
        yield {"type": "done"}
        return

    yield {"type": "thinking", "content": thinking_label_for_intent(intent)}

    # Bridge agent progress events to SSE via queue
    progress_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=32)

    async def on_progress(msg: str) -> None:
        try:
            progress_queue.put_nowait(msg)
        except asyncio.QueueFull:
            pass  # drop progress update if queue is full

    reporter = ProgressReporter(on_progress)

    async def run_dispatch():
        return await agent_dispatcher.dispatch(
            intent=intent, extracted=extracted,
            user_message=user_message, messages=messages,
            context=context, user_id=user_id, db=db,
            progress_reporter=reporter,
        )

    agent_task = asyncio.create_task(run_dispatch())

    while not agent_task.done():
        try:
            msg = await asyncio.wait_for(progress_queue.get(), timeout=0.3)
            yield {"type": "thinking", "content": msg}
        except asyncio.TimeoutError:
            pass

    try:
        result = await agent_task
        yield {"type": "result", "content": result}
    except CircuitBreakerOpen:
        yield {"type": "result", "content": {"response": "AI 服务暂时不可用，请稍后重试。"}}

    yield {"type": "done"}
