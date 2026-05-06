"""
Preference Learner - 从对话中学习用户偏好

自动提取用户偏好信号（饮食、旅行、购物等），
跨 session 持久化，使推荐越来越精准。

策略：
  1. 每轮对话后从用户消息中提取偏好信号（LLM）
  2. 在 conversation context 中累积
  3. 达到阈值后批量写入 User.preferences
  4. 下次对话时注入上下文
"""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import llm_service
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)

EXTRACTION_PROMPT = """从用户消息中提取偏好信息。只提取明确表达或强烈暗示的偏好。

## 提取类别
- food_preferences: 饮食偏好（喜欢的菜系、菜品、忌口）
- dietary_restrictions: 饮食限制（过敏、素食、清真等）
- travel_style: 旅行风格（自由行/跟团、节奏快慢、预算等级）
- accommodation_preference: 住宿偏好（酒店/民宿、价格区间）
- budget_hint: 预算暗示（经济/舒适/豪华）
- shopping_interest: 购物兴趣（品类、风格、价格偏好）
- general_preferences: 其他偏好（语言、沟通风格等）

## 输出格式（纯JSON）
```json
{
  "extracted": {
    "food_preferences": [],
    "dietary_restrictions": [],
    "travel_style": [],
    "accommodation_preference": [],
    "budget_hint": [],
    "shopping_interest": [],
    "general_preferences": []
  },
  "has_new_info": true
}
```"""


async def extract_preferences(user_message: str) -> dict[str, Any]:
    """Extract preference signals from a single user message."""
    try:
        result = await llm_service.extract_json(
            system_prompt="你是偏好分析专家。只提取明确表达的偏好，不确定就不提取。",
            messages=[{"role": "user", "content": user_message}],
            max_tokens=256,
        )
        extracted = result.get("extracted", {})
        has_new = result.get("has_new_info", False)
        if has_new and any(extracted.values()):
            return extracted
    except Exception as e:
        logger.debug("Preference extraction skipped: %s", e)
    return {}


def merge_preferences(
    current: dict[str, Any],
    new_signals: dict[str, Any],
) -> dict[str, Any]:
    """Merge newly extracted preferences into accumulated preferences.

    Uses set-based dedup within each category.
    """
    merged = dict(current)
    for category, items in new_signals.items():
        if not items:
            continue
        existing = set(merged.get(category, []))
        for item in items:
            if isinstance(item, str):
                existing.add(item)
        merged[category] = sorted(existing)
    return merged


def should_flush(extraction_count: int) -> bool:
    """Decide whether to flush accumulated preferences to DB."""
    return extraction_count > 0 and extraction_count % 5 == 0


async def flush_to_db(
    user_id: int,
    accumulated: dict[str, Any],
    db: AsyncSession,
) -> None:
    """Write accumulated preferences into User.preferences."""
    if not accumulated:
        return
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return

        current: dict = dict(user.preferences or {})
        learned: dict = current.get("_learned", {})
        for category, items in accumulated.items():
            if items:
                existing = set(learned.get(category, []))
                existing.update(items)
                learned[category] = sorted(existing)

        current["_learned"] = learned
        from sqlalchemy.orm.attributes import flag_modified
        user.preferences = current
        flag_modified(user, "preferences")
        await db.commit()
        logger.info("Flushed %d preference categories for user %d", len(accumulated), user_id)
    except Exception as e:
        logger.warning("Failed to flush preferences: %s", e)
        await db.rollback()


def build_user_profile(preferences: dict[str, Any] | None) -> dict[str, Any]:
    """Build a user profile string from preferences for agent context injection."""
    if not preferences:
        return {}

    learned = preferences.get("_learned", {})
    explicit = {k: v for k, v in preferences.items() if k != "_learned"}
    profile = {}

    if explicit:
        profile["explicit"] = explicit
    if learned:
        profile["learned"] = learned

    return profile


def format_profile_for_prompt(profile: dict[str, Any]) -> str:
    """Format user profile into a natural language prefix for agent prompts."""
    if not profile:
        return ""

    parts = []
    learned = profile.get("learned", {})
    if not learned:
        return ""

    if learned.get("food_preferences"):
        parts.append(f"饮食偏好: {', '.join(learned['food_preferences'])}")
    if learned.get("dietary_restrictions"):
        parts.append(f"饮食限制: {', '.join(learned['dietary_restrictions'])}")
    if learned.get("travel_style"):
        parts.append(f"旅行风格: {', '.join(learned['travel_style'])}")
    if learned.get("accommodation_preference"):
        parts.append(f"住宿偏好: {', '.join(learned['accommodation_preference'])}")
    if learned.get("budget_hint"):
        parts.append(f"预算倾向: {', '.join(learned['budget_hint'])}")
    if learned.get("shopping_interest"):
        parts.append(f"购物兴趣: {', '.join(learned['shopping_interest'])}")

    if parts:
        return "知道用户的以下偏好：\n" + "\n".join(parts)
    return ""
