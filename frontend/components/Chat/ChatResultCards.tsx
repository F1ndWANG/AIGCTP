"use client";

import { useRouter } from "next/navigation";
import TravelPlanCard from "@/components/TravelPlan/TravelPlanCard";
import { withSession } from "@/lib/session";
import type { TravelPlanResponse, ProductListItem, SavedRestaurantRecommendation } from "@/lib/types";

interface ChatResultCardsProps {
  currentPlan: TravelPlanResponse | null;
  currentProducts: ProductListItem[];
  currentRestaurantRec: SavedRestaurantRecommendation | null;
  currentDietPlan: Record<string, unknown> | null;
  currentCartItems: Array<Record<string, unknown>>;
  sessionId?: string;
  onConfirmPlan: (id: number) => void;
  confirmingPlan: boolean;
  onAddToCart: (productId: number) => void;
}

export default function ChatResultCards({
  currentPlan,
  currentProducts,
  currentRestaurantRec,
  currentDietPlan,
  currentCartItems,
  sessionId,
  onConfirmPlan,
  confirmingPlan,
  onAddToCart,
}: ChatResultCardsProps) {
  const router = useRouter();

  const hasAny =
    (currentPlan && currentPlan.itinerary) ||
    currentProducts.length > 0 ||
    currentRestaurantRec ||
    currentDietPlan ||
    currentCartItems.length > 0;

  if (!hasAny) return null;

  return (
    <div className="max-w-2xl mx-auto w-full px-4 pb-4 space-y-3">
      {/* Travel Plan */}
      {currentPlan && currentPlan.itinerary && (
        <TravelPlanCard
          plan={currentPlan}
          onConfirm={onConfirmPlan}
          confirming={confirmingPlan}
          onView={(id: number) => router.push(withSession(`/travel/${id}`, sessionId))}
        />
      )}

      {/* Products */}
      {currentProducts.length > 0 && (
        <section className="bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">已同步到商品</h3>
              <p className="text-xs text-gray-400 dark:text-gray-500">AI 推荐商品已进入商品页，可直接加购。</p>
            </div>
            <button
              onClick={() => router.push(withSession("/products", sessionId))}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              查看商品
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {currentProducts.slice(0, 3).map((product) => (
              <div key={product.id} className="border dark:border-slate-700 rounded-lg p-3">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{product.name}</p>
                <p className="text-sm text-red-600 font-semibold mt-1">¥{product.price}</p>
                <button
                  onClick={() => onAddToCart(product.id)}
                  className="mt-2 w-full text-xs py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  加入购物车
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Restaurant Recommendation */}
      {currentRestaurantRec && (
        <section className="bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">已同步到餐厅</h3>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {currentRestaurantRec.city || "当前"} · {currentRestaurantRec.restaurants.length} 个推荐
              </p>
            </div>
            <button
              onClick={() => router.push(withSession("/restaurants", sessionId))}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              选择餐厅
            </button>
          </div>
          <div className="flex gap-2 overflow-x-auto">
            {currentRestaurantRec.restaurants.slice(0, 4).map((restaurant, index) => (
              <div key={`${restaurant.name}-${index}`} className="min-w-40 border dark:border-slate-700 rounded-lg p-3">
                <p className="text-sm font-medium truncate">{restaurant.name}</p>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">{restaurant.address}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Diet Plan */}
      {currentDietPlan && (
        <section className="bg-green-50 border border-green-100 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-green-900">已同步到饮食健康</h3>
              <p className="text-xs text-green-700 mt-1">
                {(currentDietPlan.title as string) || "AI 饮食计划"} 已保存为草稿，可进入饮食计划确认。
              </p>
            </div>
            <button
              onClick={() => router.push(withSession("/diet", sessionId))}
              className="text-xs px-3 py-1.5 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              去确认
            </button>
          </div>
        </section>
      )}

      {/* Cart Items */}
      {currentCartItems.length > 0 && (
        <section className="bg-orange-50 border border-orange-100 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-orange-900">已同步到购物车</h3>
              <p className="text-xs text-orange-700 mt-1">
                已加入 {currentCartItems.length} 件商品，可在购物车查看。
              </p>
            </div>
            <button
              onClick={() => router.push(withSession("/cart", sessionId))}
              className="text-xs px-3 py-1.5 bg-orange-500 text-white rounded-lg hover:bg-orange-600"
            >
              查看购物车
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
