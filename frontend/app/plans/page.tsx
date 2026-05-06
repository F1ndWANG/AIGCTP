"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { travel as travelApi } from "@/lib/api";
import { chatHref, withSession } from "@/lib/session";
import type { TravelPlanListItem } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  confirmed: "已确认",
  completed: "已完成",
};

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300",
  confirmed: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
};

export default function PlansPage() {
  const { user, loading: authLoading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [plans, setPlans] = useState<TravelPlanListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadPlans = useCallback(async () => {
    setLoading(true);
    try {
      const data = await travelApi.list();
      setPlans(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { if (!authLoading && user) loadPlans(); }, [authLoading, user, loadPlans]);

  const handleDelete = async (id: number) => {
    if (!confirm("确定删除此行程？")) return;
    try {
      await travelApi.delete(id);
      setPlans((prev) => prev.filter((p) => p.id !== id));
      toast("已删除", "success");
    } catch { toast("删除失败", "error"); }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  const totalDestinations = new Set(plans.map((p) => p.destination)).size;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button onClick={() => router.push(chatHref())} className="text-sm text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">
            ← 返回对话
          </button>
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">我的行程</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4 animate-pulse space-y-2">
                <div className="h-5 bg-gray-100 rounded w-1/3" />
                <div className="h-4 bg-gray-100 rounded w-1/4" />
              </div>
            ))}
          </div>
        ) : plans.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-300 text-5xl mb-4">🗺️</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm mb-1">暂无行程</p>
            <p className="text-gray-300 text-xs">去 AI 对话让智能助手帮你规划吧！</p>
            <button
              onClick={() => router.push(chatHref())}
              className="mt-4 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              去 AI 对话
            </button>
          </div>
        ) : (
          <>
            {/* Stats */}
            <div className="flex items-center gap-4 mb-4 text-sm text-gray-500 dark:text-gray-400">
              <span>共 {plans.length} 个行程</span>
              <span>{totalDestinations} 个目的地</span>
            </div>

            {/* Plan cards */}
            <div className="space-y-3">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  className="bg-white dark:bg-slate-800 rounded-lg border dark:border-slate-700 p-4 hover:shadow-md transition cursor-pointer"
                  onClick={() => router.push(withSession(`/travel/${plan.id}`))}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900 dark:text-gray-100">{plan.destination}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[plan.status] || STATUS_COLORS.draft}`}>
                          {STATUS_LABELS[plan.status] || plan.status}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-gray-400 dark:text-gray-500">
                        <span>{plan.days} 天</span>
                        <span>{new Date(plan.created_at).toLocaleDateString("zh-CN")}</span>
                      </div>
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(plan.id); }}
                      className="text-xs text-red-400 hover:text-red-600 ml-4 flex-shrink-0"
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
