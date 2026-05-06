"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { restaurant as restaurantApi } from "@/lib/api";
import RestaurantList from "@/components/Restaurant/RestaurantList";
import { useToast } from "@/components/UI/Toast";
import { chatHref, getActiveSessionId, setActiveSessionId } from "@/lib/session";
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
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
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push(chatHref(sessionId))} className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">餐厅推荐</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {savedRecommendations.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">AI 对话同步的餐厅推荐</h2>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">选择餐厅后会保存在当前推荐记录中。</p>
              </div>
            </div>
            <div className="flex gap-2 overflow-x-auto">
              {savedRecommendations.slice(0, 6).map((item) => (
                <button
                  key={item.id}
                  onClick={() => loadSavedRecommendation(item)}
                  className={`text-left min-w-44 rounded-lg border p-3 transition ${
                    recommendationId === item.id ? "border-blue-300 bg-blue-50" : "hover:bg-gray-50"
                  }`}
                >
                  <p className="text-sm font-medium truncate">{item.city || "餐厅推荐"}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{item.restaurants.length} 个餐厅</p>
                  {item.selected_restaurant && (
                    <p className="text-xs text-green-600 mt-1 truncate">已选: {item.selected_restaurant.name}</p>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {selectedRestaurant && (
          <div className="bg-green-50 border border-green-100 rounded-xl p-4 mb-6">
            <p className="text-sm font-semibold text-green-900">当前已选餐厅</p>
            <p className="text-sm text-green-800 mt-1">{selectedRestaurant.name}</p>
            <p className="text-xs text-green-700 mt-1">{selectedRestaurant.address}</p>
          </div>
        )}

        {/* Search */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-5 mb-6">
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="输入城市名..."
              className="flex-1 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
            <input
              type="text"
              value={cuisine}
              onChange={(e) => setCuisine(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="菜系（可选）"
              className="w-28 px-3 py-2 text-sm border rounded-lg focus:outline-none focus:border-blue-400"
            />
            <button
              onClick={() => handleSearch()}
              disabled={loading}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "搜索中..." : "搜索"}
            </button>
          </div>

          {/* Hot Cities */}
          <div className="flex flex-wrap gap-1.5">
            {CITIES.map((c) => (
              <button
                key={c}
                onClick={() => { setCity(c); handleSearch(c); }}
                className="text-xs px-2.5 py-1 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-blue-50 hover:text-blue-600 transition"
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Response */}
        {response && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
            {response}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
          </div>
        )}

        {/* Results */}
        {!loading && searched && restaurants.length === 0 && (
          <div className="text-center py-16">
            <p className="text-gray-300 text-4xl mb-3">🍽️</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">未找到餐厅</p>
            <p className="text-gray-300 text-xs mt-1">试试其他城市或取消菜系筛选</p>
          </div>
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
          <div className="text-center py-20">
            <p className="text-gray-300 text-5xl mb-4">🍜</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">输入城市名搜索当地餐厅推荐</p>
            <p className="text-gray-300 text-xs mt-1">支持热门城市快速选择</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function RestaurantsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
        </div>
      }
    >
      <RestaurantsPageContent />
    </Suspense>
  );
}
