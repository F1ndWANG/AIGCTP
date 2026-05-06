"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { feedback as feedbackApi } from "@/lib/api";

interface StatsSummary {
  total_interactions: number;
  by_content_type: Record<string, { total: number; likes: number; dislikes: number }>;
}

const TYPE_LABELS: Record<string, string> = {
  travel_plan: "旅行规划",
  diet: "饮食推荐",
  restaurant: "餐厅推荐",
  commerce: "商品推荐",
  general: "通用对话",
};

const TYPE_ICONS: Record<string, string> = {
  travel_plan: "🗺️",
  diet: "🥗",
  restaurant: "🍽️",
  commerce: "🛍️",
  general: "💬",
};

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [summary, setSummary] = useState<StatsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }
    feedbackApi.analytics.summary()
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, authLoading, router]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
        <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
          <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
            <button onClick={() => router.push("/chat")} className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
              ← 返回对话
            </button>
            <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">数据概览</h1>
          </div>
        </div>
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <p className="text-gray-300 text-5xl mb-4">📊</p>
          <p className="text-gray-400 dark:text-gray-500 text-sm mb-2">加载数据失败</p>
          <p className="text-gray-300 text-xs mb-4">无法获取统计数据，请检查网络后重试</p>
          <button
            onClick={() => {
              setLoading(true);
              setSummary(null);
              feedbackApi.analytics.summary()
                .then(setSummary)
                .catch(() => {})
                .finally(() => setLoading(false));
            }}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  const types = Object.entries(summary.by_content_type);
  const totalLikes = types.reduce((s, [, v]) => s + v.likes, 0);
  const totalDislikes = types.reduce((s, [, v]) => s + v.dislikes, 0);
  const satisfactionRate = summary.total_interactions > 0
    ? ((totalLikes / summary.total_interactions) * 100).toFixed(1)
    : "0";

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push("/chat")} className="text-sm text-gray-400 hover:text-gray-600">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900">数据概览</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Summary Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4 text-center">
            <p className="text-2xl font-bold text-gray-800 dark:text-gray-200">{summary.total_interactions}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">总交互次数</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{totalLikes}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">👍 点赞</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4 text-center">
            <p className="text-2xl font-bold text-red-500">{totalDislikes}</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">👎 点踩</p>
          </div>
          <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{satisfactionRate}%</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">满意度</p>
          </div>
        </div>

        {/* Per-Type Breakdown */}
        {types.length === 0 ? (
          <div className="text-center py-16 bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700">
            <p className="text-gray-300 text-4xl mb-3">📊</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm">暂无数据</p>
            <p className="text-gray-300 text-xs mt-1">在对话中点赞或点踩后，数据会在这里展示</p>
          </div>
        ) : (
          <div className="space-y-3">
            <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400">各领域反馈</h2>
            {types.map(([type, data]) => (
              <div key={type} className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span>{TYPE_ICONS[type] || "📌"}</span>
                    <span className="font-medium text-sm">{TYPE_LABELS[type] || type}</span>
                  </div>
                  <span className="text-xs text-gray-400 dark:text-gray-500">{data.total} 次</span>
                </div>
                <div className="flex gap-3 text-sm">
                  <div className="flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg p-3">
                    <p className="text-lg font-bold text-green-600">{data.likes}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">👍 赞</p>
                  </div>
                  <div className="flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg p-3">
                    <p className="text-lg font-bold text-red-500">{data.dislikes}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">👎 踩</p>
                  </div>
                  <div className="flex-1 bg-gray-50 dark:bg-slate-900 rounded-lg p-3">
                    <p className="text-lg font-bold text-blue-600">
                      {data.total > 0 ? ((data.likes / data.total) * 100).toFixed(0) : 0}%
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">满意率</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
