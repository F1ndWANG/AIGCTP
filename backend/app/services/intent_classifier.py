"""
LLM 语义意图分类器 — Supervisor 路由的核心分类引擎

混合策略:
  1. 关键词快速路径（高置信度直接返回，零 LLM 开销）
  2. LLM 语义分类（模糊/复杂/复合意图）
  3. 提取结构化参数（目的地、天数、菜系等）
"""
import json
import re
from typing import Any

from app.services.llm import llm_service

# ──────────────────────────────────────────────
# 快速关键词检测（零 LLM 开销路径）
# ──────────────────────────────────────────────

DEFAULT_CITY = "成都"
KNOWN_CITIES = (
    "北京", "上海", "广州", "深圳", "成都", "重庆", "杭州", "西安",
    "南京", "武汉", "长沙", "厦门", "苏州", "天津", "青岛", "大理",
    "丽江", "昆明", "三亚", "桂林", "洛阳", "开封",
)

TRAVEL_KEYWORDS = frozenset(("旅游", "旅行", "攻略", "游玩", "几日游", "行程", "目的地"))
TRAVEL_PREFIXES = ("推荐", "去", "到", "来", "想", "想去", "打算", "准备", "计划", "了解", "说说", "问问", "关于")


def _quick_travel_detection(message: str) -> bool:
    if any(kw in message for kw in TRAVEL_KEYWORDS):
        return True
    prefix_pat = rf"(?:{'|'.join(TRAVEL_PREFIXES)})\s*[一-鿿]{{2,6}}\s*(?:玩|旅游|旅行|游玩|逛逛|看看|景点|攻略|天气)"
    suffix_pat = r"[一-鿿]{2,6}\s*(?:一日游|二日游|三日游|\d日游|旅游|旅行|攻略|好玩|景点|推荐|值得去)"
    return bool(re.search(prefix_pat, message)) or bool(re.search(suffix_pat, message))


def _quick_reorder_detection(message: str) -> bool:
    return any(kw in message for kw in ("再买一次", "复购", "再来一单", "重新购买", "上次买"))


def _quick_auto_cart_detection(message: str) -> bool:
    return any(kw in message for kw in ("帮我买", "帮我加购", "加购", "加入购物车", "放到购物车", "购物车", "下单", "采购", "囤货"))


def _quick_diet_log_detection(message: str) -> bool:
    return any(kw in message for kw in ("我吃了", "午餐吃了", "早餐吃了", "晚餐吃了", "记录饮食", "今天吃了", "吃了什么", "刚吃了"))


def _quick_diet_analyze_detection(message: str) -> bool:
    return any(kw in message for kw in ("分析饮食", "营养分析", "卡路里", "热量", "蛋白质摄入", "吃了多少"))


def _quick_restaurant_detection(message: str) -> bool:
    return any(kw in message for kw in ("推荐餐厅", "找餐厅", "附近吃的", "好吃", "餐馆", "饭店", "美食", "哪里吃", "去哪吃", "附近有什么"))


def _quick_commerce_detection(message: str) -> bool:
    return any(kw in message for kw in ("推荐商品", "推荐物品", "行程物品", "旅行好物", "好物", "装备", "用品", "想买", "买什么", "有什么好", "哪里买", "数码", "家电"))


def _quick_diet_detection(message: str) -> bool:
    return any(kw in message for kw in ("推荐吃的", "不想吃饭", "吃什么", "饿", "健康餐", "减肥", "增肌", "饮食", "食谱", "菜谱", "推荐吃"))


def _quick_route_detection(message: str) -> bool:
    return any(kw in message for kw in ("路线", "导航", "怎么去", "去这里", "指路", "多远", "到那里"))


def keyword_intent_score(message: str, has_travel_plan: bool) -> dict | None:
    """快速关键词检测，高置信度直接返回意图。

    Returns:
        None — 需要 LLM 语义分析
        dict — {intent, extracted, composite_intents}
    """
    msg = message.strip()
    extracted: dict[str, Any] = {}

    # 最高优先级：精确匹配
    if _quick_reorder_detection(msg):
        return {"intent": "quick_reorder", "extracted": {}, "composite_intents": [], "confidence": 0.95}

    if _quick_auto_cart_detection(msg):
        return {"intent": "auto_cart", "extracted": {}, "composite_intents": [], "confidence": 0.95}

    if _quick_diet_log_detection(msg):
        return {"intent": "diet_log", "extracted": {}, "composite_intents": [], "confidence": 0.95}

    if _quick_diet_analyze_detection(msg):
        return {"intent": "diet_analyze", "extracted": {}, "composite_intents": [], "confidence": 0.95}

    if _quick_commerce_detection(msg) and not any(city in msg for city in KNOWN_CITIES):
        return {"intent": "commerce_recommend", "extracted": {}, "composite_intents": [], "confidence": 0.9}

    # 旅行调整检测（依赖上下文）
    if has_travel_plan:
        adjust_markers = (
            "调整", "修改", "更新", "变动", "太赶", "换", "换成", "不想去",
            "不去", "不要", "去掉", "删掉", "删除", "移除", "换掉",
            "玩过", "去过", "加上", "加入", "安排", "预算", "控制", "轻松",
        )
        if any(m in msg for m in adjust_markers):
            return {"intent": "travel_adjust", "extracted": {}, "composite_intents": [], "confidence": 0.85}
        if re.search(r"(第[一二三四五六七八九\d]+天|上午|下午|晚上|中午|早上).*(去|加|安排|换)", msg):
            return {"intent": "travel_adjust", "extracted": {}, "composite_intents": [], "confidence": 0.85}
        if re.search(r"想去[一-鿿A-Za-z0-9·]{2,20}", msg):
            return {"intent": "travel_adjust", "extracted": {}, "composite_intents": [], "confidence": 0.85}

    # 复合意图检测（同时命中的多个领域）
    is_travel = _quick_travel_detection(msg)
    also_food = _quick_restaurant_detection(msg) or _quick_diet_detection(msg)
    also_shopping = _quick_commerce_detection(msg)

    if is_travel and (also_food or also_shopping):
        composite = []
        if also_food:
            composite.append("restaurant_recommend")
        if also_shopping:
            composite.append("commerce_recommend")
        return {
            "intent": "travel_plan",
            "extracted": {},
            "composite_intents": composite,
            "confidence": 0.9,
        }

    if _quick_travel_detection(msg):
        return {"intent": "travel_plan", "extracted": {}, "composite_intents": [], "confidence": 0.9}

    if _quick_restaurant_detection(msg):
        return {"intent": "restaurant_recommend", "extracted": {"city": _extract_dest(msg)}, "composite_intents": [], "confidence": 0.85}

    if _quick_commerce_detection(msg):
        return {"intent": "commerce_recommend", "extracted": {}, "composite_intents": [], "confidence": 0.8}

    if _quick_diet_detection(msg):
        return {"intent": "diet_recommend", "extracted": {}, "composite_intents": [], "confidence": 0.8}

    if _quick_route_detection(msg):
        return {"intent": "route_query", "extracted": {}, "composite_intents": [], "confidence": 0.85}

    if is_travel or (has_travel_plan and re.fullmatch(r"[一-鿿]{2,4}", msg)):
        return {"intent": "travel_plan", "extracted": {}, "composite_intents": [], "confidence": 0.7}

    # 纯地名匹配（可能意图模糊）
    if re.fullmatch(r"[一-鿿]{2,4}", msg) and msg in KNOWN_CITIES:
        return {"intent": "travel_plan", "extracted": {}, "composite_intents": [], "confidence": 0.65}

    return None  # 需要 LLM 语义分析


# ──────────────────────────────────────────────
# LLM 语义分类
# ──────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """你是意图分类专家。分析用户消息并输出 JSON。

## 意图列表
- travel_plan: 想要规划新的旅行行程（"帮我规划成都三日游"）
- travel_adjust: 对已有行程进行修改（"不想去天安门"、"把故宫换成颐和园"、"重新规划这三天"）
- travel_query: 仅询问已有行程的信息（"今天去哪"、"第二天什么安排"、"行程有哪些"）—— 不是调整，只是查询
- diet_recommend: 饮食推荐、健康饮食建议
- diet_log: 记录饮食（"午餐吃了..."、"刚吃了..."）
- diet_analyze: 饮食营养分析（"分析我的饮食"）
- restaurant_recommend: 找餐厅、美食推荐
- commerce_recommend: 商品推荐、购物建议
- auto_cart: 加购/下单（"帮我买...", "加入购物车"）
- quick_reorder: 复购
- route_query: 路线导航
- general_chat: 闲聊或不属于以上类别

## 关键区分
- 询问当前行程信息（无修改意图）→ travel_query
- 要求改变/替换/增加/删除行程内容 → travel_adjust
- 想规划全新旅行 → travel_plan

## 复合意图
消息涉及多个领域时，次要意图放入 secondary_intents。

## 输出格式（纯JSON）
{"primary_intent": "...", "secondary_intents": [], "confidence": 0.95, "reasoning": "简短理由"}"""


async def _llm_classify(message: str, recent_context: list[dict] | None = None) -> dict:
    """使用 LLM 进行语义意图分类。"""
    # 构建上下文
    context_text = ""
    if recent_context:
        recent = recent_context[-4:]
        lines = []
        for m in recent:
            role = "用户" if m.get("role") == "user" else "AI"
            content = (m.get("content") or "")[:100]
            lines.append(f"{role}: {content}")
        if lines:
            context_text = "\n## 最近对话上下文\n" + "\n".join(lines)

    user_prompt = f"## 用户消息\n{message}{context_text}\n\n分类意图并输出JSON。"
    try:
        result = await llm_service.extract_json(
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=256,
        )
        intent = result.get("primary_intent", "general_chat")
        if intent not in _VALID_INTENTS:
            intent = "general_chat"
        return {
            "intent": intent,
            "composite_intents": result.get("secondary_intents", []),
            "confidence": min(float(result.get("confidence", 0.5)), 1.0),
            "reasoning": result.get("reasoning", ""),
        }
    except Exception as e:
        logger.warning("LLM intent classification failed: %s", e)
        return {"intent": "general_chat", "composite_intents": [], "confidence": 0.0, "reasoning": "LLM 分类失败"}


_VALID_INTENTS = frozenset({
    "travel_plan", "travel_adjust", "travel_query",
    "diet_recommend", "diet_log", "diet_analyze",
    "restaurant_recommend",
    "commerce_recommend", "auto_cart", "quick_reorder",
    "route_query", "general_chat",
})


# ──────────────────────────────────────────────
# LLM 参数提取
# ──────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """从用户消息中提取结构化参数（JSON 格式，只输出 JSON）。

## 字段说明
- destination: 目的地城市或景点名称（没有则为空字符串）
- days: 旅行天数（数字，没有则为 0）
- cuisine: 菜系偏好（没有则为空字符串）
- keywords: 购物搜索关键词（列表，没有则为空列表）
- dietary_restrictions: 饮食限制（列表）
- needs_clarification: 是否需要追问更多信息（true/false）
- clarification_question: 如果要追问，问什么

## 输出格式
{"destination": "", "days": 0, "cuisine": "", "keywords": [], "dietary_restrictions": [], "needs_clarification": false, "clarification_question": ""}"""


async def extract_parameters(
    message: str,
    intent: str,
    keyword_result: dict | None = None,
) -> dict[str, Any]:
    """提取意图对应的结构化参数。

    先用 LLM 提取，然后用关键词回退填充缺失字段。
    """
    try:
        result = await llm_service.extract_json(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
            max_tokens=196,
        )
        params: dict = {
            "destination": (result.get("destination") or "").strip(),
            "days": int(result.get("days") or 0),
            "cuisine": (result.get("cuisine") or "").strip(),
            "keywords": result.get("keywords") or [],
            "dietary_restrictions": result.get("dietary_restrictions") or [],
            "needs_clarification": bool(result.get("needs_clarification", False)),
            "clarification_question": (result.get("clarification_question") or "").strip(),
        }
    except Exception:
        params = {
            "destination": "", "days": 0, "cuisine": "",
            "keywords": [], "dietary_restrictions": [],
            "needs_clarification": False, "clarification_question": "",
        }

    # 用关键词回退填充缺失字段
    if not params["destination"] or params["needs_clarification"]:
        kw_dest = _extract_dest(message)
        if kw_dest:
            params["destination"] = kw_dest
    if not params["days"]:
        params["days"] = _extract_days(message)
    if not params["cuisine"]:
        params["cuisine"] = _extract_cuisine(message)
    if intent == "commerce_recommend" and not params["keywords"]:
        params["keywords"] = _extract_commerce_keywords(message)

    # 低置信度意图 + 缺少必要参数 → 需要追问
    if intent == "travel_plan" and not params["destination"]:
        params["needs_clarification"] = True
        params["clarification_question"] = "你想去哪里玩呢？"
    elif intent == "travel_plan" and not params["days"]:
        params["needs_clarification"] = True
        params["clarification_question"] = f"你打算在{params['destination']}玩几天？"
    elif intent == "travel_plan":
        params["needs_clarification"] = False
        params["clarification_question"] = ""
    elif intent == "restaurant_recommend" and not params["destination"]:
        params["needs_clarification"] = True
        params["clarification_question"] = "你想在哪个城市找餐厅？"
    elif intent == "restaurant_recommend":
        params["needs_clarification"] = False
        params["clarification_question"] = ""
    elif intent == "commerce_recommend" and not params["keywords"]:
        params["needs_clarification"] = True
        params["clarification_question"] = "你想买什么类型的商品？"
    elif intent == "diet_recommend":
        pass  # 饮食推荐不需要追问，AI可以直接给建议

    return params


# ──────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────

async def classify(
    message: str,
    has_travel_plan: bool = False,
    recent_messages: list[dict] | None = None,
) -> dict[str, Any]:
    """主入口：混合意图分类。

    Returns:
        intent (str): 主意图
        composite_intents (list[str]): 复合次要意图列表
        confidence (float): 置信度 [0, 1]
        extracted (dict): 提取的参数
        needs_clarification (bool): 是否需要追问
        clarification_question (str): 追问问题
        reasoning (str): LLM 推理理由（如有）
    """
    # Step 1: 关键词快速路径
    keyword_result = keyword_intent_score(message, has_travel_plan)

    if keyword_result and keyword_result.get("confidence", 0) >= 0.7:
        llm_params = await extract_parameters(message, keyword_result["intent"], keyword_result)
        return {
            "intent": keyword_result["intent"],
            "composite_intents": keyword_result.get("composite_intents", []),
            "confidence": keyword_result["confidence"],
            "extracted": llm_params,
            "needs_clarification": llm_params.get("needs_clarification", False),
            "clarification_question": llm_params.get("clarification_question", ""),
            "reasoning": f"关键词快速匹配: {keyword_result['intent']}",
        }

    # Step 2: LLM 语义分类（带超时回退）
    import asyncio
    try:
        llm_result = await asyncio.wait_for(
            _llm_classify(message, recent_messages),
            timeout=6,
        )
    except asyncio.TimeoutError:
        # LLM 分类超时，用关键词结果回退
        if keyword_result and keyword_result.get("confidence", 0) >= 0.3:
            llm_params = await extract_parameters(message, keyword_result["intent"], keyword_result)
            return {
                "intent": keyword_result["intent"],
                "composite_intents": keyword_result.get("composite_intents", []),
                "confidence": keyword_result["confidence"],
                "extracted": llm_params,
                "needs_clarification": llm_params.get("needs_clarification", False),
                "clarification_question": llm_params.get("clarification_question", ""),
                "reasoning": "LLM 超时，回退关键词",
            }
        return {
            "intent": "general_chat",
            "composite_intents": [],
            "confidence": 0.5,
            "extracted": await extract_parameters(message, "general_chat", None),
            "needs_clarification": False,
            "clarification_question": "",
            "reasoning": "LLM 超时，回退通用对话",
        }
    if keyword_result and (
        llm_result["confidence"] < 0.3
        or llm_result["intent"] == "general_chat"
    ):
        # LLM 低置信度但有关键词匹配 → 用关键词
        final_intent = keyword_result["intent"]
        composite = keyword_result.get("composite_intents", [])
        confidence = max(keyword_result["confidence"], llm_result["confidence"]) if keyword_result else llm_result["confidence"]
    else:
        final_intent = llm_result["intent"]
        composite = llm_result.get("composite_intents", [])
        confidence = llm_result["confidence"]

    # Step 3: 提取参数
    llm_params = await extract_parameters(message, final_intent, keyword_result)

    return {
        "intent": final_intent,
        "composite_intents": composite,
        "confidence": confidence,
        "extracted": llm_params,
        "needs_clarification": llm_params.get("needs_clarification", False),
        "clarification_question": llm_params.get("clarification_question", ""),
        "reasoning": llm_result.get("reasoning", ""),
    }


# ──────────────────────────────────────────────
# 关键词回退提取器（从原 supervisor 迁移）
# ──────────────────────────────────────────────

def _extract_dest(text: str) -> str:
    """从文本中提取目的地城市。"""
    positions = [(text.find(city), city) for city in KNOWN_CITIES if city in text]
    positions = [(p, c) for p, c in positions if p >= 0]
    if positions:
        positions.sort(key=lambda x: x[0])
        return positions[0][1]

    patterns = [
        r"(?:去|到|在|规划|推荐|来)\s*([一-鿿]{2,6}?)(?:[的游玩旅游旅行]|\d+日)",
        r"([一-鿿]{2,6})(?:一日游|二日游|三日游|多日游|\d日游)",
        r"([一-鿿]{2,6}?)(?:旅游|旅行|攻略|游玩)",
        r"(?:推荐|想去|了解|说说|问问)\s*([一-鿿]{2,6})",
        r"^([一-鿿]{2,4})$",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            dest = m.group(1)
            for prefix in ("去", "到", "来", "在"):
                if dest.startswith(prefix):
                    dest = dest[len(prefix):]
                    break
            return dest
    return DEFAULT_CITY


def _extract_days(text: str) -> int:
    digit = re.search(r"(\d+)\s*[天日]", text)
    if digit:
        return int(digit.group(1))
    cn_map = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    # Try multi-character numbers first (e.g., "十二", "三十")
    multi = re.search(r"([十二三四五六七八九])(十)([一二三四五六七八九]?)\s*[天日]", text)
    if multi:
        tens = cn_map.get(multi.group(1), 1)
        ones = cn_map.get(multi.group(3), 0)
        return tens * 10 + ones
    cn = re.search(r"([一二两三四五六七八九十])\s*[天日]", text)
    if cn:
        return cn_map.get(cn.group(1), 0)
    return 0


def _extract_cuisine(text: str) -> str:
    cuisines = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "火锅", "烧烤", "日料", "韩餐", "西餐", "甜品", "咖啡", "奶茶",
        "海鲜", "素食", "小吃", "面食", "麻辣", "清淡",
    ]
    for c in cuisines:
        if c in text:
            return c
    return ""


def _extract_commerce_keywords(text: str) -> list[str]:
    cleaned = text.strip()
    for token in ("帮我", "推荐", "想买", "买什么", "有什么", "好物", "商品", "物品"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip(" ，。！？、")
    if cleaned:
        return [cleaned]
    return [text[:20]] if text.strip() else []
