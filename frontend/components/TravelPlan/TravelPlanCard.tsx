"use client";

import { useState } from "react";
import type { TravelPlanItinerary, TravelPlanItineraryDay } from "@/lib/types";
import RoutePanel from "./RoutePanel";
import { commerce as api } from "@/lib/api";
import { useToast } from "@/components/UI/Toast";

interface TravelPlanCardProps {
  plan: {
    id: number;
    destination: string;
    days: number;
    itinerary?: TravelPlanItinerary;
    status: string;
  };
  onView?: (id: number) => void;
}

export default function TravelPlanCard({ plan, onView }: TravelPlanCardProps) {
  const itinerary = plan.itinerary;
  const [selectedPoi, setSelectedPoi] = useState<string | null>(null);

  if (!itinerary || !itinerary.day_by_day) return null;

  return (
    <div className="bg-white rounded-xl shadow-md border overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-5">
        <div className="flex justify-between items-start">
          <div>
            <h2 className="text-xl font-bold">{plan.destination}</h2>
            <p className="text-blue-100 text-sm mt-1">
              {plan.days} 天行程 · {itinerary.theme || "精彩之旅"}
            </p>
          </div>
          <span className="px-2.5 py-1 bg-white/20 rounded-full text-xs">
            {plan.status === "draft" ? "草稿" : plan.status === "confirmed" ? "已确认" : "已完成"}
          </span>
        </div>

        {/* Budget */}
        {itinerary.budget_estimate && (
          <div className="mt-3 pt-3 border-t border-white/20 flex flex-wrap gap-3 text-sm">
            <span>💰 总预算: {itinerary.budget_estimate.total || "待估算"}</span>
          </div>
        )}
      </div>

      {/* Day by Day */}
      <div className="p-5 space-y-4">
        {itinerary.day_by_day.map((day: TravelPlanItineraryDay, idx: number) => (
          <DayCard
            key={idx}
            day={day}
            dayIndex={idx}
            onPoiClick={(poi) => setSelectedPoi(poi)}
          />
        ))}

        {/* Tips */}
        {itinerary.tips && itinerary.tips.length > 0 && (
          <div className="mt-4 pt-4 border-t">
            <h4 className="font-semibold text-gray-700 mb-2">
              💡 出行小贴士
            </h4>
            <ul className="space-y-1">
              {itinerary.tips.map((tip: string, i: number) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>
                  {tip}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Actions */}
      {onView && (
        <div className="px-5 pb-4">
          <button
            onClick={() => onView(plan.id)}
            className="w-full py-2.5 text-sm text-blue-600 border border-blue-200 rounded-lg hover:bg-blue-50 transition"
          >
            查看完整行程
          </button>
        </div>
      )}

      {/* Route Panel */}
      {selectedPoi && (
        <RoutePanel
          poiName={selectedPoi}
          city={plan.destination}
          onClose={() => setSelectedPoi(null)}
        />
      )}
    </div>
  );
}

function DayCard({
  day,
  dayIndex,
  onPoiClick,
}: {
  day: TravelPlanItineraryDay;
  dayIndex: number;
  onPoiClick: (poi: string) => void;
}) {
  const { toast } = useToast();

  const handleAddToCart = async (productId: number) => {
    try {
      await api.addCartItem({ product_id: productId, quantity: 1 });
      toast("已加入购物车", "success");
    } catch {
      toast("加入购物车失败", "error");
    }
  };
  return (
    <div className="border-l-2 border-blue-400 pl-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-0.5 rounded">
          第 {day.day || dayIndex + 1} 天
        </span>
        {day.theme && (
          <span className="text-sm font-medium text-gray-700">{day.theme}</span>
        )}
        {day.weather && (
          <span className="text-xs text-gray-400 ml-auto">
            {day.weather.condition || ""}{" "}
            {day.weather.temperature || (day.weather.temp_min != null ? `${day.weather.temp_min}~${day.weather.temp_max}°C` : day.weather.temp_low != null ? `${day.weather.temp_low}~${day.weather.temp_high}°C` : "")}
          </span>
        )}
      </div>

      {/* Meals — restaurant names are clickable for route planning */}
      {day.meals && day.meals.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-400 uppercase mb-1">🍽 餐饮推荐</p>
          <div className="space-y-1.5">
            {day.meals.map((meal: { type: string; recommendation: string; restaurant?: string; description?: string }, i: number) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <span className="text-gray-400 w-10 shrink-0 mt-0.5">{meal.type}</span>
                <div className="flex-1 min-w-0">
                  {meal.restaurant ? (
                    <button
                      onClick={() => onPoiClick(meal.restaurant!)}
                      className="text-sm font-medium text-blue-700 hover:text-blue-500 hover:underline text-left transition"
                    >
                      {meal.restaurant}
                    </button>
                  ) : (
                    <span className="text-sm font-medium text-gray-700">{meal.recommendation}</span>
                  )}
                  {meal.restaurant && (
                    <p className="text-xs text-gray-500">{meal.recommendation}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Activities */}
      <div className="space-y-2">
        {day.activities?.map((act: { time: string; poi: string; duration?: string; description?: string; tips?: string }, i: number) => (
          <div key={i} className="flex gap-3">
            <div className="w-12 shrink-0">
              <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                {act.time || "全天"}
              </span>
            </div>
            <div>
              <button
                onClick={() => onPoiClick(act.poi)}
                className="text-sm font-medium text-blue-700 hover:text-blue-500 hover:underline text-left transition"
              >
                {act.poi}
              </button>
              <p className="text-xs text-gray-500">
                {act.description}
                {act.duration && ` · ${act.duration}`}
              </p>
              {act.tips && (
                <p className="text-xs text-amber-600 mt-0.5">💡 {act.tips}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Shopping Recommendations */}
      {day.shopping && day.shopping.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-400 uppercase mb-1.5">🛍 推荐好物</p>
          <div className="space-y-1.5">
            {day.shopping.map((item, i) => (
              <div key={i} className="flex items-center justify-between bg-orange-50 rounded-lg px-3 py-2">
                <div className="min-w-0 flex-1 mr-2">
                  <p className="text-sm font-medium text-gray-700 truncate">{item.product_name}</p>
                  <p className="text-xs text-gray-500 truncate">{item.reason}</p>
                  <p className="text-xs font-bold text-red-600 mt-0.5">¥{item.price}</p>
                </div>
                <button
                  onClick={() => handleAddToCart(item.product_id)}
                  className="shrink-0 text-xs px-2.5 py-1 bg-orange-500 text-white rounded-md hover:bg-orange-600 transition"
                >
                  加购
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
