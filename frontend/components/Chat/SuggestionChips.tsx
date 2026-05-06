"use client";

import { useMemo } from "react";

interface SuggestionChipsProps {
  onSelect: (text: string) => void;
  lastResponse?: string;
  hasTravelPlan?: boolean;
  hasProducts?: boolean;
  hasRestaurants?: boolean;
  hasDietPlan?: boolean;
  show?: boolean;
}

export default function SuggestionChips({
  onSelect,
  lastResponse = "",
  hasTravelPlan = false,
  hasProducts = false,
  hasRestaurants = false,
  hasDietPlan = false,
  show = false,
}: SuggestionChipsProps) {
  const suggestions = useMemo(() => {
    if (!show) return [];

    const chips: string[] = [];

    if (hasTravelPlan) {
      chips.push("调整行程");
      chips.push("推荐当地美食");
      chips.push("看看有什么特产买");
    } else if (hasRestaurants) {
      chips.push("推荐特色菜");
      chips.push("帮我选一个");
    } else if (hasProducts) {
      chips.push("帮我加购");
      chips.push("看看其他商品");
    } else if (hasDietPlan) {
      chips.push("开始执行计划");
      chips.push("调整饮食方案");
    }

    // Generic suggestions based on response keywords
    if (lastResponse.includes("旅行") || lastResponse.includes("行程")) {
      if (!hasTravelPlan) chips.push("帮我规划一下");
    }
    if (lastResponse.includes("餐厅") || lastResponse.includes("美食")) {
      if (!chips.includes("推荐特色菜")) chips.push("附近还有吗");
    }
    if (lastResponse.includes("商品") || lastResponse.includes("推荐")) {
      if (!chips.includes("帮我加购")) chips.push("加入购物车");
    }

    return chips.slice(0, 4);
  }, [show, hasTravelPlan, hasProducts, hasRestaurants, hasDietPlan, lastResponse]);

  if (suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 px-4 pb-2">
      {suggestions.map((text) => (
        <button
          key={text}
          onClick={() => onSelect(text)}
          className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-blue-50 hover:text-blue-600 hover:border-blue-200 border border-gray-200 dark:border-slate-700 transition"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
