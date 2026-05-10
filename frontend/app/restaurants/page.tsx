"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { restaurant as restaurantApi } from "@/lib/api";
import RestaurantList from "@/components/Restaurant/RestaurantList";
import { useToast } from "@/components/UI/Toast";
import { chatHref, getActiveSessionId, setActiveSessionId } from "@/lib/session";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/UI/card";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Input } from "@/components/UI/input";
import { ArrowLeft, UtensilsCrossed, MapPin, Star, Navigation, Search } from "lucide-react";
import { motion } from "motion/react";
import type { Restaurant, SavedRestaurantRecommendation } from "@/lib/types";

const CITIES = ["成都", "北京", "上海", "广州", "深圳", "杭州", "西安", "重庆", "南京", "武汉", "长沙", "厦门"];

function RestaurantsPageContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [city, setCity] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [response, setResponse] = useState("");
  const [recommendationId, setRecommendationId] = useState<number | null>(null);
  const [savedRecommendations, setSavedRecommendations] = useState<SavedRestaurantRecommendation[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    const sid = searchParams.get("session") || getActiveSessionId();
    setSessionId(sid);
    if (sid) setActiveSessionId(sid);
  }, [searchParams]);

  useEffect(() => {
    if (!user) return;
    restaurantApi
      .listRecommendations(sessionId || undefined)
      .then((items) => {
        setSavedRecommendations(items);
        const latest = items[0];
        if (latest) {
          setRecommendationId(latest.id);
          setRestaurants(latest.restaurants || []);
          setResponse(latest.response || "");
          setCity(latest.city || "");
          setSelectedRestaurant(latest.selected_restaurant || null);
          setSearched(true);
        }
      })
      .catch(() => {});
  }, [user, sessionId]);

  if (authLoading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex items-center justify-center"
      >
        <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
      </motion.div>
    );
  }

  if (!user) { router.push("/"); return null; }

  const handleSearch = async (c?: string) => {
    const targetCity = c || city;
    if (!targetCity.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const data = await restaurantApi.recommend(targetCity, cuisine || undefined, sessionId || undefined);
      setRestaurants(data.restaurants || []);
      setResponse(data.response || "");
      setRecommendationId(data.recommendation_id || null);
      setSelectedRestaurant(null);
      if (data.recommendation_id) {
        const saved = await restaurantApi.getRecommendation(data.recommendation_id);
        setSavedRecommendations((prev) => [saved, ...prev.filter((item) => item.id !== saved.id)]);
      }
    } catch {
      toast("搜索餐厅失败", "error");
    }
    setLoading(false);
  };

  const handleSelectRestaurant = async (restaurant: Restaurant) => {
    if (!recommendationId) {
      setSelectedRestaurant(restaurant);
      return;
    }
    try {
      const saved = await restaurantApi.selectRecommendation(recommendationId, restaurant as unknown as Record<string, unknown>);
      setSelectedRestaurant(saved.selected_restaurant || restaurant);
      setSavedRecommendations((prev) => prev.map((item) => item.id === saved.id ? saved : item));
      toast("已同步到餐厅页", "success");
    } catch {
      toast("选择餐厅失败", "error");
    }
  };

  const loadSavedRecommendation = (item: SavedRestaurantRecommendation) => {
    setRecommendationId(item.id);
    setRestaurants(item.restaurants || []);
    setResponse(item.response || "");
    setCity(item.city || "");
    setSelectedRestaurant(item.selected_restaurant || null);
    setSearched(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      {/* Header */}
      <div className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push(chatHref(sessionId))}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
          >
            <ArrowLeft className="w-4 h-4" />
            返回对话
          </button>
          <h1 className="text-lg font-bold text-foreground">餐厅推荐</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {savedRecommendations.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>AI 对话同步的餐厅推荐</CardTitle>
              <CardDescription>选择餐厅后会保存在当前推荐记录中。</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {savedRecommendations.slice(0, 6).map((item) => (
                  <button
                    key={item.id}
                    onClick={() => loadSavedRecommendation(item)}
                    className={`text-left min-w-44 rounded-lg border p-3 transition flex-shrink-0 ${
                      recommendationId === item.id
                        ? "border-fuchsia-300 bg-fuchsia-50 dark:border-fuchsia-700 dark:bg-fuchsia-950/30"
                        : "border-border hover:bg-muted"
                    }`}
                  >
                    <p className="text-sm font-medium text-foreground truncate">{item.city || "餐厅推荐"}</p>
                    <p className="text-xs text-muted-foreground mt-1">{item.restaurants.length} 个餐厅</p>
                    {item.selected_restaurant && (
                      <p className="text-xs text-fuchsia-600 dark:text-fuchsia-400 mt-1 truncate">
                        已选: {item.selected_restaurant.name}
                      </p>
                    )}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {selectedRestaurant && (
          <Card className="border-fuchsia-200 dark:border-fuchsia-900">
            <CardContent className="flex items-start gap-3 pt-4">
              <MapPin className="w-5 h-5 text-fuchsia-600 dark:text-fuchsia-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-fuchsia-800 dark:text-fuchsia-300">当前已选餐厅</p>
                <p className="text-sm text-fuchsia-700 dark:text-fuchsia-400 mt-1">{selectedRestaurant.name}</p>
                <p className="text-xs text-fuchsia-600 dark:text-fuchsia-500 mt-1">{selectedRestaurant.address}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Search */}
        <Card>
          <CardContent className="pt-4 space-y-4">
            <div className="flex gap-2">
              <Input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="输入城市名..."
                className="flex-1"
              />
              <Input
                type="text"
                value={cuisine}
                onChange={(e) => setCuisine(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="菜系（可选）"
                className="w-28"
              />
              <Button
                onClick={() => handleSearch()}
                disabled={loading}
                className="gap-1"
              >
                <Search className="w-3.5 h-3.5" />
                {loading ? "搜索中..." : "搜索"}
              </Button>
            </div>

            {/* Hot Cities */}
            <div className="flex flex-wrap gap-1.5">
              {CITIES.map((c) => (
                <button
                  key={c}
                  onClick={() => { setCity(c); handleSearch(c); }}
                  className="text-xs px-2.5 py-1 bg-muted text-muted-foreground rounded-full hover:bg-fuchsia-100 hover:text-fuchsia-700 dark:hover:bg-fuchsia-900/30 dark:hover:text-fuchsia-300 transition"
                >
                  {c}
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Response */}
        {response && (
          <Card className="bg-fuchsia-50/50 dark:bg-fuchsia-950/20 border-fuchsia-100 dark:border-fuchsia-900">
            <CardContent className="pt-4 text-sm text-foreground whitespace-pre-wrap">
              {response}
            </CardContent>
          </Card>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
          </div>
        )}

        {/* Results */}
        {!loading && searched && restaurants.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <UtensilsCrossed className="mx-auto text-muted-foreground/40 w-9 h-9 mb-3" />
            <p className="text-muted-foreground text-sm">未找到餐厅</p>
            <p className="text-muted-foreground/50 text-xs mt-1">试试其他城市或取消菜系筛选</p>
          </motion.div>
        )}

        {!loading && restaurants.length > 0 && (
          <RestaurantList
            restaurants={restaurants}
            city={city}
            onSelect={handleSelectRestaurant}
            selectedName={selectedRestaurant?.name}
          />
        )}

        {!searched && !loading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-20"
          >
            <UtensilsCrossed className="mx-auto text-muted-foreground/40 w-12 h-12 mb-4" />
            <p className="text-muted-foreground text-sm">输入城市名搜索当地餐厅推荐</p>
            <p className="text-muted-foreground/50 text-xs mt-1">支持热门城市快速选择</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

export default function RestaurantsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
        </div>
      }
    >
      <RestaurantsPageContent />
    </Suspense>
  );
}
