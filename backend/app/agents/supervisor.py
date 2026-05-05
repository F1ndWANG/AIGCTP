"""
Supervisor Agent - 意图识别 + 路由分发

分析用户输入，判断意图并路由到对应的子 Agent。
当前支持:
  - 旅行规划     → travel_agent.plan_trip
  - 行程调整     → travel_agent.adjust_plan
  - 饮食推荐     → diet_agent.recommend_diet
  - 饮食记录     → diet_agent.log_meal
  - 营养分析     → diet_agent.analyze_nutrition
  - 餐厅推荐     → restaurant_agent.recommend_restaurants
  - 通用问答     → direct LLM
"""
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.services.llm import llm_service
from app.agents import travel_agent, diet_agent, restaurant_agent, commerce_agent
from app.models.diet import HealthProfile, MealRecord


def _classify_intent(
    user_message: str,
    has_travel_plan: bool,
) -> tuple[str, dict]:
    """Fast keyword-based intent classification — no LLM call needed."""
    msg = user_message.strip()
    extracted: dict = {}

    # Order matters: more specific patterns first
    if has_travel_plan and any(kw in msg for kw in ["调整", "修改", "太赶", "太累", "轻松", "重新规划", "预算不足"]):
        return "travel_adjust", extracted

    if any(kw in msg for kw in ["再买一次", "复购", "再来一单", "重新购买", "上次买"]):
        return "quick_reorder", extracted

    if any(kw in msg for kw in ["帮我买", "帮我加购", "加购", "下单", "采购", "囤货"]):
        return "auto_cart", extracted

    if any(kw in msg for kw in ["我吃了", "午餐吃了", "早餐吃了", "晚餐吃了", "记录饮食", "今天吃了", "吃了什么", "刚吃了"]):
        return "diet_log", extracted

    if any(kw in msg for kw in ["分析饮食", "营养分析", "卡路里", "热量", "蛋白质摄入", "吃了多少"]):
        return "diet_analyze", extracted

    # Cross-domain: travel + food/restaurants
    is_travel = any(kw in msg for kw in ["旅游", "旅行", "攻略", "游玩", "几日游", "行程", "目的地", "一日游", "二日游", "多日游"])
    also_food = any(kw in msg for kw in ["推荐餐厅", "好吃", "餐馆", "饭店", "美食", "特产", "小吃"])
    also_shopping = any(kw in msg for kw in ["推荐商品", "购物", "买什么", "纪念品", "特产", "好物", "值得买"])

    if is_travel and (also_food or also_shopping):
        dest = _extract_destination_fallback(msg)
        days = _extract_days_fallback(msg) or 3
        return "travel_plan", {
            "destination": dest, "days": days, "preferences": {},
            "also_recommend_food": also_food,
            "also_recommend_products": also_shopping,
        }

    if any(kw in msg for kw in ["推荐餐厅", "附近吃的", "好吃", "餐馆", "饭店", "美食", "哪里吃", "去哪吃", "附近有什么"]):
        city = _extract_destination_fallback(msg)
        return "restaurant_recommend", {"city": city, "cuisine": _extract_cuisine(msg)}

    if any(kw in msg for kw in ["推荐商品", "想买", "购物", "买什么", "有什么好", "哪里买", "数码", "家电"]):
        return "commerce_recommend", extracted

    if any(kw in msg for kw in ["推荐吃的", "不想吃饭", "吃什么", "饿", "健康", "减肥", "增肌", "饮食", "食谱", "菜谱", "推荐吃"]):
        return "diet_recommend", extracted

    # Route/navigation query — not a travel plan
    if any(kw in msg for kw in ["路线", "导航", "怎么去", "去这里", "指路", "多远", "到那里"]):
        return "route_query", extracted

    if any(kw in msg for kw in ["旅游", "旅行", "攻略", "游玩", "几日游", "行程", "目的地", "规划", "一日游", "二日游", "多日游"]):
        dest = _extract_destination_fallback(msg)
        days = _extract_days_fallback(msg) or 3
        return "travel_plan", {"destination": dest, "days": days, "preferences": {}}

    return "general_chat", extracted


async def run_agent(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """Main entry: analyze intent and route to the right agent.

    Returns:
        dict with keys: response (str), travel_plan (optional dict)
    """
    # Step 1: Fast keyword-based intent classification (no LLM call)
    has_travel_plan = "current_travel_plan" in context and context["current_travel_plan"] is not None
    intent, extracted = _classify_intent(user_message, has_travel_plan)

    # Step 2: Route to appropriate agent
    if intent == "travel_plan":
        destination = extracted.get("destination") or _extract_destination_fallback(user_message)
        days = extracted.get("days") or _extract_days_fallback(user_message) or 3
        preferences = {
            **(context.get("user_preferences", {})),
            **extracted.get("preferences", {}),
        }

        result = await travel_agent.plan_trip(
            destination=destination,
            days=days,
            user_id=user_id,
            db=db,
            user_preferences=preferences,
        )

        # Cross-domain: parallel restaurant/commerce calls when user asks
        also_food = extracted.get("also_recommend_food")
        also_products = extracted.get("also_recommend_products")
        if also_food or also_products:
            extra_parts = []
            tasks = []
            if also_food:
                tasks.append(restaurant_agent.recommend_restaurants(
                    city=destination,
                    user_message=f"去{destination}旅游，推荐当地的特色美食、小吃和餐厅",
                ))
            if also_products:
                tasks.append(commerce_agent.commerce_recommend(
                    user_message=f"去{destination}旅游，推荐旅行装备、当地特产和纪念品",
                    user_id=user_id,
                    db=db,
                ))

            if tasks:
                import asyncio
                extra_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in extra_results:
                    if isinstance(r, dict) and r.get("response"):
                        extra_parts.append(r["response"])

            if extra_parts:
                combined = result["response"] + "\n\n" + "\n\n".join(extra_parts)
                result["response"] = combined

        return result

    elif intent == "travel_adjust" and has_travel_plan:
        plan = context["current_travel_plan"]
        return await travel_agent.adjust_plan(
            plan_id=plan["id"],
            instruction=user_message,
            current_itinerary=plan.get("itinerary", {}),
            destination=plan["destination"],
            days=plan["days"],
            db=db,
        )

    elif intent == "diet_recommend":
        hp_result = await db.execute(
            select(HealthProfile).where(HealthProfile.user_id == user_id)
        )
        hp = hp_result.scalar_one_or_none()
        meal_result = await db.execute(
            select(MealRecord)
            .where(MealRecord.user_id == user_id)
            .order_by(MealRecord.date.desc())
            .limit(14)
        )
        recent_meals = list(meal_result.scalars().all())
        return await diet_agent.recommend_diet(
            user_message=user_message,
            user_id=user_id,
            db=db,
            health_profile=hp,
            meal_records=recent_meals,
        )

    elif intent == "diet_log":
        return await diet_agent.log_meal(
            user_id=user_id,
            user_message=user_message,
            db=db,
        )

    elif intent == "diet_analyze":
        meal_result = await db.execute(
            select(MealRecord)
            .where(MealRecord.user_id == user_id)
            .order_by(MealRecord.date.desc())
            .limit(30)
        )
        recent_meals = [{
            "date": str(r.date),
            "meal_type": r.meal_type,
            "foods": r.foods,
            "total_nutrition": r.total_nutrition,
        } for r in meal_result.scalars().all()]
        return await diet_agent.analyze_nutrition(
            user_message=user_message,
            meal_records=recent_meals,
        )

    elif intent == "restaurant_recommend":
        city = extracted.get("city") or extracted.get("destination") or ""
        cuisine = extracted.get("cuisine")
        # Check if user is asking about "nearby" — use GPS or user's city preference
        is_nearby = "附近" in user_message and not city
        if is_nearby:
            user_city = context.get("user_preferences", {}).get("city", "")
            if user_city:
                return await restaurant_agent.recommend_restaurants(
                    city=user_city,
                    user_message=user_message,
                    cuisine=cuisine,
                )
        return await restaurant_agent.recommend_restaurants(
            city=city or context.get("user_preferences", {}).get("city", "成都"),
            user_message=user_message,
            cuisine=cuisine,
        )

    elif intent == "commerce_recommend":
        return await commerce_agent.commerce_recommend(
            user_message=user_message,
            user_id=user_id,
            db=db,
        )

    elif intent == "auto_cart":
        return await commerce_agent.auto_cart(
            user_message=user_message,
            user_id=user_id,
            context=context,
            db=db,
        )

    elif intent == "quick_reorder":
        return await commerce_agent.quick_reorder(
            user_id=user_id,
            db=db,
        )

    else:
        # General chat — respond directly with LLM with full conversation history
        system_prompt = """你是 AI 生活推荐系统的智能助手。你可以帮助用户:
1. 规划旅行行程（告诉用户你可以帮他们规划旅行）
2. 推荐饮食和健康方案（告诉用户你可以帮他们推荐吃什么、记录饮食、分析营养）
3. 推荐餐厅（告诉用户你可以推荐各地美食餐厅）
4. 推荐商品和购物（告诉用户你可以推荐各种商品、自动加购、一键复购）

用热情专业的中文回复。如果用户提到旅行相关的内容，主动询问是否需要规划行程。"""
        # Pass full conversation history for continuous Q&A (strip internal fields like session_id)
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = await llm_service.chat(
            system_prompt=system_prompt,
            messages=clean_messages,
            max_tokens=1024,
            temperature=0.7,
        )
        return {"response": resp}


async def run_agent_stream(
    user_message: str,
    messages: list[dict],
    context: dict,
    user_id: int,
    db: AsyncSession,
):
    """Streaming variant — yields event dicts for SSE consumption.

    Yields:
        {"type": "token", "content": str}  — streaming token
        {"type": "result", "content": dict}  — full agent result for non-streaming flows
        {"type": "done"}  — signal end
    """
    # Send thinking signal immediately so frontend has feedback
    yield {"type": "thinking", "content": "正在分析您的请求..."}

    # Step 1: Fast keyword-based intent classification (no LLM call)
    has_travel_plan = "current_travel_plan" in context and context["current_travel_plan"] is not None
    intent, extracted = _classify_intent(user_message, has_travel_plan)

    if intent == "travel_plan":
        yield {"type": "thinking", "content": "正在规划旅行行程..."}
        destination = extracted.get("destination") or _extract_destination_fallback(user_message)
        days = extracted.get("days") or _extract_days_fallback(user_message) or 3
        preferences = {
            **(context.get("user_preferences", {})),
            **extracted.get("preferences", {}),
        }

        result = await travel_agent.plan_trip(
            destination=destination,
            days=days,
            user_id=user_id,
            db=db,
            user_preferences=preferences,
        )

        # Cross-domain: parallel restaurant/commerce calls when user asks
        also_food = extracted.get("also_recommend_food")
        also_products = extracted.get("also_recommend_products")
        if also_food or also_products:
            yield {"type": "thinking", "content": "正在同步搜索当地美食和好物..."}
            extra_parts = []
            tasks = []
            if also_food:
                tasks.append(restaurant_agent.recommend_restaurants(
                    city=destination,
                    user_message=f"去{destination}旅游，推荐当地的特色美食、小吃和餐厅",
                ))
            if also_products:
                tasks.append(commerce_agent.commerce_recommend(
                    user_message=f"去{destination}旅游，推荐旅行装备、当地特产和纪念品",
                    user_id=user_id,
                    db=db,
                ))

            if tasks:
                import asyncio
                extra_results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in extra_results:
                    if isinstance(r, dict) and r.get("response"):
                        extra_parts.append(r["response"])

            if extra_parts:
                combined = result["response"] + "\n\n" + "\n\n".join(extra_parts)
                result["response"] = combined

        yield {"type": "result", "content": result}

    elif intent == "travel_adjust" and has_travel_plan:
        yield {"type": "thinking", "content": "正在调整行程..."}
        plan = context["current_travel_plan"]
        result = await travel_agent.adjust_plan(
            plan_id=plan["id"],
            instruction=user_message,
            current_itinerary=plan.get("itinerary", {}),
            destination=plan["destination"],
            days=plan["days"],
            db=db,
        )
        yield {"type": "result", "content": result}

    elif intent == "diet_recommend":
        yield {"type": "thinking", "content": "正在分析饮食需求..."}
        hp_result = await db.execute(
            select(HealthProfile).where(HealthProfile.user_id == user_id)
        )
        hp = hp_result.scalar_one_or_none()
        meal_result = await db.execute(
            select(MealRecord)
            .where(MealRecord.user_id == user_id)
            .order_by(MealRecord.date.desc())
            .limit(14)
        )
        recent_meals = list(meal_result.scalars().all())
        result = await diet_agent.recommend_diet(
            user_message=user_message,
            user_id=user_id,
            db=db,
            health_profile=hp,
            meal_records=recent_meals,
        )
        yield {"type": "result", "content": result}

    elif intent == "diet_log":
        yield {"type": "thinking", "content": "正在记录饮食..."}
        result = await diet_agent.log_meal(
            user_id=user_id,
            user_message=user_message,
            db=db,
        )
        yield {"type": "result", "content": result}

    elif intent == "diet_analyze":
        yield {"type": "thinking", "content": "正在分析营养数据..."}
        meal_result = await db.execute(
            select(MealRecord)
            .where(MealRecord.user_id == user_id)
            .order_by(MealRecord.date.desc())
            .limit(30)
        )
        recent_meals = [{
            "date": str(r.date),
            "meal_type": r.meal_type,
            "foods": r.foods,
            "total_nutrition": r.total_nutrition,
        } for r in meal_result.scalars().all()]
        result = await diet_agent.analyze_nutrition(
            user_message=user_message,
            meal_records=recent_meals,
        )
        yield {"type": "result", "content": result}

    elif intent == "restaurant_recommend":
        yield {"type": "thinking", "content": "正在搜索餐厅..."}
        city = extracted.get("city") or extracted.get("destination") or ""
        cuisine = extracted.get("cuisine")
        result = await restaurant_agent.recommend_restaurants(
            city=city,
            user_message=user_message,
            cuisine=cuisine,
        )
        yield {"type": "result", "content": result}

    elif intent == "commerce_recommend":
        yield {"type": "thinking", "content": "正在搜索推荐商品..."}
        result = await commerce_agent.commerce_recommend(
            user_message=user_message,
            user_id=user_id,
            db=db,
        )
        yield {"type": "result", "content": result}

    elif intent == "auto_cart":
        yield {"type": "thinking", "content": "正在处理购物请求..."}
        result = await commerce_agent.auto_cart(
            user_message=user_message,
            user_id=user_id,
            context=context,
            db=db,
        )
        yield {"type": "result", "content": result}

    elif intent == "quick_reorder":
        yield {"type": "thinking", "content": "正在查找历史订单..."}
        result = await commerce_agent.quick_reorder(
            user_id=user_id,
            db=db,
        )
        yield {"type": "result", "content": result}

    else:
        # General chat — stream tokens with full conversation history
        yield {"type": "thinking", "content": "正在思考..."}
        system_prompt = """你是 AI 生活推荐系统的智能助手。你可以帮助用户:
1. 规划旅行行程（告诉用户你可以帮他们规划旅行）
2. 推荐饮食和健康方案（告诉用户你可以帮他们推荐吃什么、记录饮食、分析营养）
3. 推荐餐厅（告诉用户你可以推荐各地美食餐厅）
4. 推荐商品和购物（告诉用户你可以推荐各种商品、自动加购、一键复购）

用热情专业的中文回复。如果用户提到旅行相关的内容，主动询问是否需要规划行程。"""
        clean_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        async for token in llm_service.chat_stream(
            system_prompt=system_prompt,
            messages=clean_messages,
            max_tokens=1024,
            temperature=0.7,
        ):
            yield {"type": "token", "content": token}

    yield {"type": "done"}


def _extract_destination_fallback(text: str) -> str:
    """Simple regex fallback for destination extraction."""
    patterns = [
        # Priority 1: explicit prefix (去/到/在/规划/推荐/来)
        r"(?:去|到|在|规划|推荐|来)\s*([一-鿿]{2,6}?)(?:[的游玩旅游旅行]|[\d]+日)",
        # Priority 2: "X日游" as suffix — handle before generic patterns
        r"([一-鿿]{2,6})(?:一日游|二日游|三日游|多日游|\d日游)",
        # Priority 3: "一日游X" (一日游北京)
        r"一日游\s*([一-鿿]{2,6})",
        # Priority 4: X旅游 / X旅行 / X攻略 / X游玩 (non-greedy)
        r"([一-鿿]{2,6}?)(?:旅游|旅行|攻略|游玩)",
        # Priority 5: X有什么好吃的/美食/餐厅/饭店/餐馆
        r"([一-鿿]{2,6})(?:有什么好吃的|美食|餐厅|饭店|餐馆)",
        # Priority 6: X有什么好玩/景点
        r"([一-鿿]{2,6})(?:有什么好玩|景点)",
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1)
    return "成都"  # default


def _extract_days_fallback(text: str) -> int:
    """Extract number of days from text. Handles both '3天' and '三日'."""
    # ASCII digits: "3天", "3日"
    match = re.search(r"(\d+)\s*[天日]", text)
    if match:
        return int(match.group(1))
    # Chinese numbers: "一日", "三天", "两日"
    cn_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    cn_match = re.search(r"([一二两三四五六七八九])\s*[天日]", text)
    if cn_match:
        return cn_map.get(cn_match.group(1), 0)
    return 0


def _extract_cuisine(text: str) -> str | None:
    """Extract cuisine type from text."""
    cuisine_keywords = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "火锅", "烧烤", "日料", "韩餐", "西餐", "甜品", "咖啡", "奶茶",
        "海鲜", "素食", "小吃", "面食", "麻辣", "清淡",
    ]
    for kw in cuisine_keywords:
        if kw in text:
            return kw
    return None
