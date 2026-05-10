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
from app.agents.domain_results import DietAgentResult

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
    wants_plan: bool = False,
) -> DietAgentResult:
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

    if wants_plan and not _is_valid_diet_plan(diet_plan_data):
        diet_plan_data = _fallback_diet_plan(user_message)
        response_text = _format_diet_plan_response(diet_plan_data)

    # Save diet plan to DB if generated
    if _is_valid_diet_plan(diet_plan_data):
        activate_markers = ("开始执行", "立即开始", "马上开始", "开始计划", "启用")
        wants_active = any(marker in user_message for marker in activate_markers)
        try:
            plan = DietPlan(
                user_id=user_id,
                title=diet_plan_data.get("title", "AI 饮食推荐"),
                duration_days=diet_plan_data.get("duration_days", 1),
                meals=diet_plan_data.get("meals"),
                total_nutrition=diet_plan_data.get("total_nutrition"),
                tips=diet_plan_data.get("tips", []),
                status="active" if wants_active else "draft",
            )
            db.add(plan)
            await db.flush()
            await db.refresh(plan)
        except Exception as e:
            logger.warning("Failed to save diet plan: %s", e)
            await db.rollback()

    return DietAgentResult(response=response_text, diet_plan=diet_plan_data)


def _wants_diet_plan(user_message: str) -> bool:
    """Return True when the user explicitly asks for a structured diet plan."""
    plan_markers = ("计划", "食谱", "菜单", "一周", "7天", "七天", "每日", "每天")
    diet_markers = ("饮食", "减肥", "减脂", "增肌", "控糖", "健康餐", "营养")
    return any(marker in user_message for marker in plan_markers) and any(
        marker in user_message for marker in diet_markers
    )


def _infer_duration_days(user_message: str) -> int:
    if any(marker in user_message for marker in ("一周", "7天", "七天")):
        return 7
    return 1


def _infer_goal(user_message: str) -> str:
    if "增肌" in user_message:
        return "增肌"
    if "控糖" in user_message:
        return "控糖"
    if "减肥" in user_message or "减脂" in user_message:
        return "减脂"
    return "健康饮食"


def _is_valid_diet_plan(diet_plan_data: Any) -> bool:
    return isinstance(diet_plan_data, dict) and bool(diet_plan_data.get("meals"))


def _fallback_diet_plan(user_message: str) -> dict[str, Any]:
    """Build a deterministic diet plan when the LLM does not return structured JSON."""
    duration_days = _infer_duration_days(user_message)
    goal = _infer_goal(user_message)

    templates = [
        {
            "breakfast": [("燕麦粥", "1碗", 220), ("水煮蛋", "1个", 70), ("蓝莓", "1小把", 40)],
            "lunch": [("糙米饭", "1小碗", 180), ("香煎鸡胸肉", "120g", 200), ("西兰花", "200g", 70)],
            "dinner": [("清蒸鱼", "120g", 160), ("杂蔬沙拉", "1份", 90), ("红薯", "100g", 90)],
        },
        {
            "breakfast": [("全麦面包", "2片", 180), ("低脂牛奶", "250ml", 120), ("苹果", "1个", 80)],
            "lunch": [("藜麦饭", "1小碗", 170), ("虾仁炒蛋", "1份", 230), ("生菜", "200g", 40)],
            "dinner": [("豆腐菌菇汤", "1碗", 150), ("凉拌黄瓜", "1份", 45), ("玉米", "半根", 80)],
        },
        {
            "breakfast": [("无糖酸奶", "200g", 120), ("坚果", "10g", 60), ("香蕉", "半根", 45)],
            "lunch": [("荞麦面", "1碗", 260), ("牛肉片", "100g", 190), ("菠菜", "200g", 50)],
            "dinner": [("鸡蛋羹", "1份", 120), ("番茄炒蛋", "半份", 140), ("紫甘蓝沙拉", "1份", 60)],
        },
    ]

    day_by_day = []
    total_calories = 0
    for day in range(1, duration_days + 1):
        template = templates[(day - 1) % len(templates)]
        meals = []
        for meal_type, key in (("早餐", "breakfast"), ("午餐", "lunch"), ("晚餐", "dinner")):
            foods = [
                {"name": name, "amount": amount, "calories": calories}
                for name, amount, calories in template[key]
            ]
            total_calories += sum(food["calories"] for food in foods)
            meals.append({"meal_type": meal_type, "foods": foods})
        day_by_day.append({"day": day, "meals": meals})

    avg_calories = round(total_calories / duration_days)
    return {
        "title": f"{duration_days}天{goal}饮食计划",
        "duration_days": duration_days,
        "meals": {"day_by_day": day_by_day},
        "total_nutrition": {
            "calories": avg_calories,
            "protein": 95 if goal in ("减脂", "增肌") else 75,
            "carbs": 150 if goal == "减脂" else 190,
            "fat": 45,
        },
        "tips": [
            "每天保证足量饮水，优先选择蒸、煮、炖等低油烹饪方式。",
            "如果运动量较大，可在训练后补充无糖酸奶、鸡蛋或低脂牛奶。",
            "晚餐尽量提前到睡前3小时完成，减少高糖零食和含糖饮料。",
        ],
    }


def _format_diet_plan_response(diet_plan_data: dict[str, Any]) -> str:
    title = diet_plan_data.get("title", "饮食计划")
    duration_days = diet_plan_data.get("duration_days", 1)
    nutrition = diet_plan_data.get("total_nutrition") or {}
    calories = nutrition.get("calories", 0)
    return (
        f"已为你生成《{title}》，共 {duration_days} 天，并已保存到“饮食健康”的饮食计划中。\n\n"
        f"计划以高蛋白、控油、适量碳水和充足蔬菜为核心，日均热量约 {calories} kcal。"
        "你可以进入“饮食健康 -> 饮食计划”查看完整每日三餐安排。"
    )


async def log_meal(
    user_id: int,
    user_message: str,
    db: AsyncSession,
) -> DietAgentResult:
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

    # Save to database — merge with existing record if same date+meal_type
    try:
        meal_type = result.get("meal_type", "lunch")
        today = date.today()
        existing_result = await db.execute(
            select(MealRecord).where(
                MealRecord.user_id == user_id,
                MealRecord.date == today,
                MealRecord.meal_type == meal_type,
            )
        )
        existing = existing_result.scalar_one_or_none()

        new_foods = result.get("foods", [])
        if existing:
            existing_foods = existing.foods or []
            existing_names = {f.get("name") for f in existing_foods}
            for f in new_foods:
                if f.get("name") not in existing_names:
                    existing_foods.append(f)
            existing.foods = existing_foods
            if result.get("total_nutrition"):
                existing.total_nutrition = result["total_nutrition"]
            if result.get("notes"):
                existing.notes = result["notes"]
            record = existing
        else:
            record = MealRecord(
                user_id=user_id,
                date=today,
                meal_type=meal_type,
                foods=new_foods,
                total_nutrition=result.get("total_nutrition"),
                notes=result.get("notes", ""),
            )
            db.add(record)
        await db.flush()
        await db.refresh(record)
    except Exception as e:
        logger.warning("Failed to save meal record: %s", e)
        await db.rollback()
        return DietAgentResult(response="抱歉，记录饮食时出现错误，请稍后再试。")

    return DietAgentResult(
        response=result.get("response", "已记录您的饮食信息！"),
        meal_record={
            "id": record.id,
            "date": str(record.date),
            "meal_type": record.meal_type,
            "foods": record.foods,
            "total_nutrition": record.total_nutrition,
        },
    )


async def analyze_nutrition(
    user_message: str,
    meal_records: list[dict],
) -> DietAgentResult:
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

    return DietAgentResult(response=response)


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
