"use client";

import { useRouter } from "next/navigation";
import { ShoppingBag, Utensils, Apple, ShoppingCart, ArrowRight, Map as MapIcon } from "lucide-react";
import TravelPlanCard from "@/components/TravelPlan/TravelPlanCard";
import { Card } from "@/components/UI/card";
import { MagicCard } from "@/components/UI/magic-card";
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
      {currentPlan && currentPlan.itinerary && (
        <MagicCard mode="gradient" gradientFrom="#d946ef" gradientTo="#14b8a6" gradientSize={360} className="rounded-xl">
          <Card size="sm" className="border-0 shadow-none bg-transparent">
            <div className="p-4">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapIcon className="h-4 w-4 text-primary" />
                  <h3 className="text-sm font-semibold text-card-foreground">已同步到行程</h3>
                </div>
                <button
                  onClick={() => router.push(withSession(`/travel/${currentPlan.id}`, sessionId))}
                  className="flex items-center gap-1 text-xs text-primary hover:text-primary/80"
                >
                  查看行程 <ArrowRight className="h-3 w-3" />
                </button>
              </div>
              <TravelPlanCard
                plan={currentPlan}
                onConfirm={onConfirmPlan}
                confirming={confirmingPlan}
              />
            </div>
          </Card>
        </MagicCard>
      )}

      {/* Products */}
      {currentProducts.length > 0 && (
        <MagicCard mode="gradient" gradientFrom="#d946ef" gradientTo="#ec4899" gradientSize={300} className="rounded-xl">
          <Card size="sm" className="border-0 shadow-none bg-transparent">
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <ShoppingBag className="h-4 w-4 text-primary" />
                  <h3 className="font-semibold text-card-foreground text-sm">已同步到商品</h3>
                </div>
                <button
                  onClick={() => router.push(withSession("/products", sessionId))}
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
                >
                  查看商品 <ArrowRight className="h-3 w-3" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-3">AI 推荐商品已进入商品页，可直接加购。</p>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {currentProducts.slice(0, 3).map((product) => (
                  <div key={product.id} className="border border-border rounded-lg p-3 bg-card/50">
                    <p className="text-sm font-medium text-card-foreground truncate">{product.name}</p>
                    <p className="text-sm text-destructive font-semibold mt-1">¥{product.price}</p>
                    <button
                      onClick={() => onAddToCart(product.id)}
                      className="mt-2 w-full text-xs py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                    >
                      加入购物车
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </MagicCard>
      )}

      {/* Restaurant Recommendation */}
      {currentRestaurantRec && (
        <MagicCard mode="gradient" gradientFrom="#f97316" gradientTo="#ef4444" gradientSize={300} className="rounded-xl">
          <Card size="sm" className="border-0 shadow-none bg-transparent">
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Utensils className="h-4 w-4 text-orange-500" />
                  <h3 className="font-semibold text-card-foreground text-sm">已同步到餐厅</h3>
                </div>
                <button
                  onClick={() => router.push(withSession("/restaurants", sessionId))}
                  className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
                >
                  选择餐厅 <ArrowRight className="h-3 w-3" />
                </button>
              </div>
              <p className="text-xs text-muted-foreground mb-3">
                {currentRestaurantRec.city || "当前"} · {currentRestaurantRec.restaurants.length} 个推荐
              </p>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {currentRestaurantRec.restaurants.slice(0, 4).map((restaurant, index) => (
                  <div key={`${restaurant.name}-${index}`} className="min-w-40 border border-border rounded-lg p-3 bg-card/50 shrink-0">
                    <p className="text-sm font-medium truncate">{restaurant.name}</p>
                    <p className="text-xs text-muted-foreground mt-1 truncate">{restaurant.address}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </MagicCard>
      )}

      {/* Diet Plan */}
      {currentDietPlan && (
        <MagicCard mode="gradient" gradientFrom="#22c55e" gradientTo="#16a34a" gradientSize={300} className="rounded-xl">
          <Card size="sm" className="border-0 shadow-none bg-transparent">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Apple className="h-4 w-4 text-green-500" />
                  <h3 className="font-semibold text-card-foreground text-sm">已同步到饮食健康</h3>
                </div>
                <button
                  onClick={() => router.push(withSession("/diet", sessionId))}
                  className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  去确认
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {(currentDietPlan.title as string) || "AI 饮食计划"} 已保存为草稿，可进入饮食计划确认。
              </p>
            </div>
          </Card>
        </MagicCard>
      )}

      {/* Cart Items */}
      {currentCartItems.length > 0 && (
        <MagicCard mode="gradient" gradientFrom="#f59e0b" gradientTo="#d97706" gradientSize={300} className="rounded-xl">
          <Card size="sm" className="border-0 shadow-none bg-transparent">
            <div className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="h-4 w-4 text-amber-500" />
                  <h3 className="font-semibold text-card-foreground text-sm">已同步到购物车</h3>
                </div>
                <button
                  onClick={() => router.push(withSession("/cart", sessionId))}
                  className="text-xs px-3 py-1.5 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  查看购物车
                </button>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                已加入 {currentCartItems.length} 件商品，可在购物车查看。
              </p>
            </div>
          </Card>
        </MagicCard>
      )}
    </div>
  );
}
