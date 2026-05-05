"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { restaurant as restaurantApi } from "@/lib/api";
import RestaurantList from "@/components/Restaurant/RestaurantList";
import { useToast } from "@/components/UI/Toast";
import type { Restaurant } from "@/lib/types";

const CITIES = ["成都", "北京", "上海", "广州", "深圳", "杭州", "西安", "重庆", "南京", "武汉", "长沙", "厦门"];

export default function RestaurantsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { toast } = useToast();
  const [city, setCity] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

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
      const data = await restaurantApi.recommend(targetCity, cuisine || undefined);
      setRestaurants(data.restaurants || []);
      setResponse(data.response || "");
    } catch {
      toast("搜索餐厅失败", "error");
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push("/chat")} className="text-sm text-gray-400 hover:text-gray-600">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900">餐厅推荐</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Search */}
        <div className="bg-white rounded-xl border p-5 mb-6">
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
                className="text-xs px-2.5 py-1 bg-gray-100 text-gray-600 rounded-full hover:bg-blue-50 hover:text-blue-600 transition"
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {/* Response */}
        {response && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 mb-6 text-sm text-gray-700 whitespace-pre-wrap">
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
            <p className="text-gray-400 text-sm">未找到餐厅</p>
            <p className="text-gray-300 text-xs mt-1">试试其他城市或取消菜系筛选</p>
          </div>
        )}

        {!loading && restaurants.length > 0 && (
          <RestaurantList restaurants={restaurants} city={city} />
        )}

        {!searched && !loading && (
          <div className="text-center py-20">
            <p className="text-gray-300 text-5xl mb-4">🍜</p>
            <p className="text-gray-400 text-sm">输入城市名搜索当地餐厅推荐</p>
            <p className="text-gray-300 text-xs mt-1">支持热门城市快速选择</p>
          </div>
        )}
      </div>
    </div>
  );
}
