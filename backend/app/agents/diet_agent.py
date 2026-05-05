"""
Diet Agent - 饮食健康助手

Handles diet recommendations, meal logging, and nutrition analysis.
"""
import json
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.llm import llm_service
from app.models.diet import HealthProfile, MealRecord, DietPlan
from app.core.logging import get_logger

logger = get_logger(__name__)

DIET_SYSTEM_PROMPT = """你是 AI 生活推荐系统的饮食健康专家。你擅长分析用户的饮食需求并提供个性化建议。

## 你的角色
- 你是一个专业、贴心的饮食健康顾问
- 你会考虑用户的健康档案（过敏源、慢性病、饮食目标、饮食限制）
- 你会结合用户的近期饮食记录给出建议
- 你会推荐具体的食物和菜品，而非泛泛而谈

## 推荐原则
1. **个性化**: 根据用户的健康状况和饮食目标定制建议
2. **可执行**: 推荐具体的菜品、食材和做法
3. **均衡营养**: 考虑蛋白质、碳水、脂肪的合理搭配
4. **本地化**: 结合用户所在地推荐可获得的食材/餐厅
"""


async def recommend_diet(
    user_message: str,
    user_id: int,
    db: AsyncSession,
    health_profile: HealthProfile | None = None,
    meal_records: list[MealRecord] | None = None,
) -> dict[str, Any]:
    """Generate diet recommendation based on user message and health context.

    Returns:
        dict with keys: response (str), diet_plan (optional dict)
    """
    profile_str = _format_health_profile(health_profile)
    meals_str = _format_recent_meals(meal_records)

    prompt = f"""根据用户的请求和健康信息，提供个性化的饮食推荐。

## 用户消息
{user_message}

## 用户健康档案
{profile_str}

## 近期饮食记录
{meals_str or "（暂无记录）"}

## 分析要求
1. 首先判断用户需要什么类型的建议：
   - recipe: 用户想要具体的食谱/菜品推荐
   - restaurant: 用户想出去吃/找餐厅
   - general_advice: 一般性的饮食建议
2. 考虑用户的健康限制和饮食目标
3. 给出具体、可操作的建议

## 输出格式
```json
{{
  "recommendation_type": "recipe|restaurant|general_advice",
  "response": "给用户的完整回复，热情专业，包含具体推荐",
  "nutrition_tips": "相关的营养建议",
  "diet_plan": {{
    "title": "饮食计划标题（如有）",
    "duration_days": 1,
    "meals": {{
      "day_by_day": [
        {{
          "day": 1,
          "meals": [
            {{"meal_type": "早餐", "foods": [{{"name": "食物名", "amount": "分量", "calories": 0}}]}},
            {{"meal_type": "午餐", "foods": [{{"name": "食物名", "amount": "分量", "calories": 0}}]}},
            {{"meal_type": "晚餐", "foods": [{{"name": "食物名", "amount": "分量", "calories": 0}}]}}
          ]
        }}
      ]
    }},
    "total_nutrition": {{"calories": 0, "protein": 0, "carbs": 0, "fat": 0}},
    "tips": ["tip1", "tip2"]
  }}
}}
```

如果用户没有明确要求生成饮食计划，diet_plan 字段可为 null。
"""

    try:
        result = await llm_service.extract_json(
            system_prompt=DIET_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.warning("Diet agent extract_json failed: %s", e)
        result = {
            "recommendation_type": "general_advice",
            "response": "我建议您保持均衡饮食，多吃蔬菜水果，适量摄入蛋白质。如果您有具体的饮食需求，请告诉我！",
        }

    response_text = result.get("response", "")
    diet_plan_data = result.get("diet_plan")

    # Save diet plan to DB if generated
    if diet_plan_data and diet_plan_data.get("meals"):
        try:
            plan = DietPlan(
                user_id=user_id,
                title=diet_plan_data.get("title", "AI 饮食推荐"),
                duration_days=diet_plan_data.get("duration_days", 1),
                meals=diet_plan_data.get("meals"),
                total_nutrition=diet_plan_data.get("total_nutrition"),
                tips=diet_plan_data.get("tips", []),
                status="draft",
            )
            db.add(plan)
            await db.commit()
            await db.refresh(plan)
        except Exception as e:
            logger.warning("Failed to save diet plan: %s", e)

    return {
        "response": response_text,
        "diet_plan": diet_plan_data,
    }


async def log_meal(
    user_id: int,
    user_message: str,
    db: AsyncSession,
) -> dict[str, Any]:
    """Parse a natural language meal description into a structured meal record.

    Returns:
        dict with keys: response (str), meal_record (optional dict)
    """
    prompt = f"""从用户的描述中提取饮食记录信息，输出结构化 JSON。

## 用户描述
{user_message}

## 输出格式
```json
{{
  "meal_type": "breakfast|lunch|dinner|snack",
  "foods": [
    {{"name": "食物名称", "amount": "分量描述", "calories": 估计卡路里, "protein": 蛋白质克数, "carbs": 碳水克数, "fat": 脂肪克数}}
  ],
  "total_nutrition": {{"calories": 总卡路里, "protein": 总蛋白质, "carbs": 总碳水, "fat": 总脂肪}},
  "notes": "补充说明",
  "response": "对用户的确认回复，友好热情"
}}

注意：如果用户没有明确说明餐次（早/午/晚/加餐），请根据时间或内容推断。
营养数据请给出合理估计值，如果无法估计则用 0。
"""

    try:
        result = await llm_service.extract_json(
            system_prompt="你是一个饮食记录助手，从自然语言提取结构化饮食数据。",
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        logger.warning("Log meal extract_json failed: %s", e)
        result = {
            "meal_type": "lunch",
            "foods": [{"name": user_message, "amount": "一份", "calories": 0}],
            "response": "已记录您的饮食信息！",
        }

    # Save to database
    try:
        record = MealRecord(
            user_id=user_id,
            date=date.today(),
            meal_type=result.get("meal_type", "lunch"),
            foods=result.get("foods", []),
            total_nutrition=result.get("total_nutrition"),
            notes=result.get("notes", ""),
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
    except Exception as e:
        logger.warning("Failed to save meal record: %s", e)
        return {"response": "抱歉，记录饮食时出现错误，请稍后再试。"}

    return {
        "response": result.get("response", "已记录您的饮食信息！"),
        "meal_record": {
            "id": record.id,
            "date": str(record.date),
            "meal_type": record.meal_type,
            "foods": record.foods,
            "total_nutrition": record.total_nutrition,
        },
    }


async def analyze_nutrition(
    user_message: str,
    meal_records: list[dict],
) -> dict[str, Any]:
    """Analyze nutrition from recent meal records.

    Returns:
        dict with response string
    """
    records_str = json.dumps(meal_records, ensure_ascii=False, indent=2)

    prompt = f"""分析以下饮食记录的营养情况，给出专业建议。

## 用户问题
{user_message}

## 近期饮食记录
{records_str}

## 分析要求
1. 计算总热量和三大营养素（蛋白质/碳水/脂肪）的摄入情况
2. 评估营养均衡性
3. 给出具体的改进建议
4. 用热情专业的语气回复
"""

    try:
        response = await llm_service.chat(
            system_prompt="你是一个营养分析专家，用中文回复。",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.5,
        )
    except Exception as e:
        logger.warning("Analyze nutrition failed: %s", e)
        response = "暂时无法分析您的饮食记录，请稍后再试。"

    return {"response": response}


def _format_health_profile(profile: HealthProfile | None) -> str:
    if not profile:
        return "（未设置健康档案）"
    parts = []
    if profile.height:
        parts.append(f"身高: {profile.height}cm")
    if profile.weight:
        parts.append(f"体重: {profile.weight}kg")
    if profile.age:
        parts.append(f"年龄: {profile.age}")
    if profile.gender:
        parts.append(f"性别: {profile.gender}")
    if profile.allergies:
        parts.append(f"过敏源: {', '.join(profile.allergies)}")
    if profile.chronic_conditions:
        parts.append(f"慢性病: {', '.join(profile.chronic_conditions)}")
    if profile.diet_goals:
        parts.append(f"饮食目标: {', '.join(profile.diet_goals)}")
    if profile.dietary_restrictions:
        parts.append(f"饮食限制: {', '.join(profile.dietary_restrictions)}")
    return "\n".join(parts) if parts else "（未设置健康档案）"


def _format_recent_meals(records: list[MealRecord] | None) -> str:
    if not records:
        return ""
    lines = []
    for r in records[-7:]:
        foods_str = ", ".join(f.get("name", "") for f in (r.foods or []))
        nut = r.total_nutrition or {}
        cal = nut.get("calories", 0) or 0
        lines.append(f"  {r.date} {r.meal_type}: {foods_str} ({cal}kcal)")
    return "\n".join(lines)
