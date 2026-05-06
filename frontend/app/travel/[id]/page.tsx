"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import TravelPlanCard from "@/components/TravelPlan/TravelPlanCard";
import { travel as travelApi, chat as chatApi } from "@/lib/api";
import { chatHref, setActiveSessionId } from "@/lib/session";
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
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    if (sessionId) setActiveSessionId(sessionId);
  }, [sessionId]);

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
      setActiveSessionId(result.session_id);
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
      router.push(chatHref(sessionId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      toast("删除失败: " + msg, "error");
    }
  };

  const handleConfirm = async () => {
    if (!plan || confirming) return;
    setConfirming(true);
    try {
      const confirmed = await travelApi.confirm(plan.id);
      setPlan(confirmed);
      toast("最终行程已确认", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "未知错误";
      toast("确认失败: " + msg, "error");
    } finally {
      setConfirming(false);
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

  const backToChatHref = chatHref(sessionId);

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-slate-900">
      {/* Header */}
      <header className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 px-4 py-3">
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
        <TravelPlanCard
          plan={plan}
          onConfirm={handleConfirm}
          confirming={confirming}
        />

        {/* Adjust */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border dark:border-slate-700 p-5">
          <div className="mb-3">
            <h3 className="font-semibold text-gray-700 dark:text-gray-300">调整行程</h3>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {plan.status === "confirmed"
                ? "已确认的行程再次调整后会回到草稿状态，需要重新确认。"
                : "当前是草稿，可继续通过 AI 对话修改，满意后确认最终行程。"}
            </p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={adjustInput}
              onChange={(e) => setAdjustInput(e.target.value)}
              placeholder="例如：第二天太赶了 / 预算控制在2000以内"
              className="flex-1 px-4 py-2 border border-gray-300 dark:border-slate-700 rounded-lg outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={handleAdjust}
              disabled={adjusting || !adjustInput.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {adjusting ? "处理中..." : "调整"}
            </button>
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
            输入你的调整需求，AI 会重新规划行程
          </p>
        </div>
      </div>
    </main>
  );
}
