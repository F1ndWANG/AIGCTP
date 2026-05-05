"use client";

import type { DietPlan } from "@/lib/types";

interface DietPlanCardProps {
  plan: DietPlan;
  onView?: (id: number) => void;
  onConfirm?: (id: number) => void;
  onDelete?: (id: number) => void;
}

interface DietPlanDay {
  day: number;
  meals: Array<{
    meal_type: string;
    foods: Array<{ name: string; amount: string; calories?: number }>;
  }>;
}

function formatMealType(mealType: string): string {
  if (mealType === "breakfast") return "早餐";
  if (mealType === "lunch") return "午餐";
  if (mealType === "dinner") return "晚餐";
  if (mealType === "snack") return "加餐";
  return mealType;
}

function formatStatus(status: string): string {
  if (status === "draft") return "草稿";
  if (status === "active") return "进行中";
  if (status === "completed") return "已完成";
  return status;
}

export default function DietPlanCard({
  plan,
  onView,
  onConfirm,
  onDelete,
}: DietPlanCardProps) {
  const dayByDay = plan.meals?.day_by_day || [];
  const nutrition = plan.total_nutrition;

  if (dayByDay.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-md border overflow-hidden">
      <div className="bg-gradient-to-r from-green-600 to-emerald-600 text-white p-4">
        <div className="flex justify-between items-start gap-3">
          <div>
            <h2 className="text-lg font-bold">{plan.title || "饮食计划"}</h2>
            <p className="text-green-100 text-sm mt-1">
              {plan.duration_days}天饮食计划
            </p>
          </div>
          <span className="px-2.5 py-1 bg-white/20 rounded-full text-xs flex-shrink-0">
            {formatStatus(plan.status)}
          </span>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {dayByDay.map((day: DietPlanDay, idx: number) => (
          <div key={idx} className="border-l-2 border-green-400 pl-4">
            <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded">
              第 {day.day} 天
            </span>
            <div className="mt-2 space-y-2">
              {day.meals.map((meal, mi: number) => (
                <div key={mi} className="text-sm">
                  <span className="text-gray-500 font-medium">
                    {formatMealType(meal.meal_type)}
                  </span>
                  <div className="ml-2 space-y-0.5">
                    {meal.foods.map((food, fi: number) => (
                      <div key={fi} className="flex justify-between gap-3 text-gray-700">
                        <span>
                          {food.name} ({food.amount})
                        </span>
                        {food.calories ? (
                          <span className="text-gray-400 flex-shrink-0">
                            {food.calories}kcal
                          </span>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {nutrition && (
        <div className="px-4 pb-4">
          <div className="bg-gray-50 rounded-lg p-3 grid grid-cols-4 gap-2 text-center text-xs">
            <div>
              <p className="text-gray-900 font-medium">{nutrition.calories || 0}</p>
              <p className="text-gray-400">总热量</p>
            </div>
            <div>
              <p className="text-gray-900 font-medium">{nutrition.protein || 0}g</p>
              <p className="text-gray-400">蛋白质</p>
            </div>
            <div>
              <p className="text-gray-900 font-medium">{nutrition.carbs || 0}g</p>
              <p className="text-gray-400">碳水</p>
            </div>
            <div>
              <p className="text-gray-900 font-medium">{nutrition.fat || 0}g</p>
              <p className="text-gray-400">脂肪</p>
            </div>
          </div>
        </div>
      )}

      {plan.tips && plan.tips.length > 0 && (
        <div className="px-4 pb-4">
          <h4 className="font-semibold text-gray-700 text-sm mb-2">小贴士</h4>
          <ul className="space-y-1">
            {plan.tips.map((tip: string, i: number) => (
              <li key={i} className="text-xs text-gray-500 flex gap-2">
                <span className="text-green-500">•</span>
                {tip}
              </li>
            ))}
          </ul>
        </div>
      )}

      {(onView || onConfirm || onDelete) && (
        <div className="px-4 pb-4 space-y-2">
          {plan.status === "draft" && onConfirm && (
            <button
              onClick={() => onConfirm(plan.id)}
              className="w-full py-2 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700 transition"
            >
              确认计划
            </button>
          )}
          {onView && (
            <button
              onClick={() => onView(plan.id)}
              className="w-full py-2 text-sm text-green-600 border border-green-200 rounded-lg hover:bg-green-50 transition"
            >
              查看详情
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(plan.id)}
              className="w-full py-2 text-sm text-red-500 border border-red-200 rounded-lg hover:bg-red-50 transition"
            >
              删除计划
            </button>
          )}
        </div>
      )}
    </div>
  );
}
