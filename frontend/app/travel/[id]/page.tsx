"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import TravelPlanCard from "@/components/TravelPlan/TravelPlanCard";
import { travel as travelApi, chat as chatApi } from "@/lib/api";
import type { TravelPlanResponse } from "@/lib/types";

export default function TravelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [sessionId, setSessionId] = useState<string | undefined>(
    () => searchParams.get("session") || undefined
  );
  const { toast } = useToast();
  const { user, loading: authLoading } = useAuth();
  const [plan, setPlan] = useState<TravelPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [adjustInput, setAdjustInput] = useState("");
  const [adjusting, setAdjusting] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.push("/"); return; }

    const id = Number(params.id);
    if (isNaN(id)) { router.push("/chat"); return; }

    travelApi
      .get(id)
      .then(setPlan)
      .catch(() => router.push("/chat"))
      .finally(() => setLoading(false));
  }, [params.id, user, authLoading, router]);

  const handleAdjust = async () => {
    if (!adjustInput.trim() || adjusting || !plan) return;
    setAdjusting(true);
    try {
      const result = await chatApi.send(adjustInput, sessionId, plan.id);
      setSessionId(result.session_id);
      setAdjustInput("");
      if (result.travel_plan) {
        setPlan(result.travel_plan);
      }
      const updated = await travelApi.get(plan.id);
      setPlan(updated);
      toast("行程已更新！", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      toast("调整失败: " + msg, "error");
    } finally {
      setAdjusting(false);
    }
  };

  const handleDelete = async () => {
    if (!plan || !confirm("确定删除这个行程吗？")) return;
    try {
      await travelApi.delete(plan.id);
      toast("行程已删除", "info");
      router.push(sessionId ? `/chat?session=${sessionId}` : "/chat");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      toast("删除失败: " + msg, "error");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!plan) return null;

  const backToChatHref = sessionId ? `/chat?session=${sessionId}` : "/chat";

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <button
            onClick={() => router.push(backToChatHref)}
            className="text-sm text-blue-600 hover:underline"
          >
            ← 返回对话
          </button>
          <button
            onClick={handleDelete}
            className="text-sm text-red-500 hover:underline"
          >
            删除
          </button>
        </div>
      </header>

      <div className="max-w-3xl mx-auto p-4 space-y-4">
        <TravelPlanCard plan={plan} />

        {/* Adjust */}
        <div className="bg-white rounded-xl border p-5">
          <h3 className="font-semibold text-gray-700 mb-3">调整行程</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={adjustInput}
              onChange={(e) => setAdjustInput(e.target.value)}
              placeholder="例如：第二天太赶了 / 预算控制在2000以内"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleAdjust}
              disabled={adjusting || !adjustInput.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {adjusting ? "处理中..." : "调整"}
            </button>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            输入你的调整需求，AI 会重新规划行程
          </p>
        </div>
      </div>
    </main>
  );
}
