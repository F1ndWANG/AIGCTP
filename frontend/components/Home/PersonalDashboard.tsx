"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { travel, diet, chat as chatApi, commerce } from "@/lib/api";
import { setActiveSessionId } from "@/lib/session";
import type { TravelPlanListItem, DietPlanListItem, ChatSession, Cart } from "@/lib/types";

export default function PersonalDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [travelPlans, setTravelPlans] = useState<TravelPlanListItem[]>([]);
  const [dietPlans, setDietPlans] = useState<DietPlanListItem[]>([]);
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    Promise.allSettled([
      travel.list().then(setTravelPlans).catch(() => {}),
      diet.getPlans().then(setDietPlans).catch(() => {}),
      chatApi.listSessions().then(setChatSessions).catch(() => {}),
      commerce.getCart().then(setCart).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [user]);

  const activeTravel = travelPlans.filter((p) => p.status !== "completed");
  const activeDiet = dietPlans.filter((p) => p.status !== "completed");
  const recentChats = chatSessions.slice(0, 4);

  if (!user) return null;

  const startNewChat = () => {
    setActiveSessionId(null);
    router.push("/chat");
  };

  const restoreChat = (sid: string) => {
    setActiveSessionId(sid);
    router.push(`/chat?session=${sid}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900">
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Greeting */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            你好，{user.display_name}
          </h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            今天想做什么？
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {/* Quick Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
              <StatCard
                icon="🗺️"
                label="进行中的行程"
                value={activeTravel.length}
                onClick={() => router.push("/plans")}
              />
              <StatCard
                icon="🥗"
                label="饮食计划"
                value={activeDiet.length}
                onClick={() => router.push("/diet")}
              />
              <StatCard
                icon="💬"
                label="最近对话"
                value={chatSessions.length}
                onClick={() => router.push("/chat")}
              />
              <StatCard
                icon="🛒"
                label="购物车"
                value={cart?.items?.length || 0}
                onClick={() => router.push("/cart")}
              />
            </div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Active Travel Plan */}
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-5">
                <SectionHeader
                  title="进行中的行程"
                  icon="🗺️"
                  onViewAll={() => router.push("/plans")}
                />
                {activeTravel.length === 0 ? (
                  <EmptyState
                    message="暂无进行中的行程"
                    action="找 AI 规划行程"
                    onClick={startNewChat}
                  />
                ) : (
                  <ul className="space-y-2">
                    {activeTravel.slice(0, 3).map((p) => (
                      <li key={p.id}>
                        <button
                          onClick={() => router.push(`/travel/${p.id}`)}
                          className="w-full text-left flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50 transition"
                        >
                          <div>
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{p.destination}</p>
                            <p className="text-xs text-gray-400 dark:text-gray-500">{p.days} 天 · {formatDate(p.created_at)}</p>
                          </div>
                          <Badge status={p.status} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Active Diet Plan */}
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-5">
                <SectionHeader
                  title="饮食计划"
                  icon="🥗"
                  onViewAll={() => router.push("/diet")}
                />
                {activeDiet.length === 0 ? (
                  <EmptyState
                    message="暂无饮食计划"
                    action="找 AI 定制饮食"
                    onClick={startNewChat}
                  />
                ) : (
                  <ul className="space-y-2">
                    {activeDiet.slice(0, 3).map((p) => (
                      <li key={p.id}>
                        <button
                          onClick={() => router.push(`/diet`)}
                          className="w-full text-left flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50 transition"
                        >
                          <div>
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{p.title}</p>
                            <p className="text-xs text-gray-400 dark:text-gray-500">{p.duration_days} 天计划</p>
                          </div>
                          <Badge status={p.status === "active" ? "进行中" : p.status} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Recent Chat Sessions */}
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-5">
                <SectionHeader
                  title="最近对话"
                  icon="💬"
                  onViewAll={() => router.push("/chat")}
                />
                {recentChats.length === 0 ? (
                  <EmptyState
                    message="暂无对话记录"
                    action="开始新对话"
                    onClick={startNewChat}
                  />
                ) : (
                  <ul className="space-y-2">
                    {recentChats.map((s) => (
                      <li key={s.session_id}>
                        <button
                          onClick={() => restoreChat(s.session_id)}
                          className="w-full text-left p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50 transition"
                        >
                          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{s.title || "未命名对话"}</p>
                          <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">{s.last_preview}</p>
                          <p className="text-xs text-gray-300 dark:text-gray-600 mt-0.5">{formatDate(s.updated_at)}</p>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Cart Summary */}
              <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-5">
                <SectionHeader
                  title="购物车"
                  icon="🛒"
                  onViewAll={() => router.push("/cart")}
                />
                {!cart || cart.items.length === 0 ? (
                  <EmptyState
                    message="购物车是空的"
                    action="去逛逛商品"
                    onClick={() => router.push("/products")}
                  />
                ) : (
                  <div>
                    <ul className="space-y-2">
                      {cart.items.slice(0, 3).map((item) => (
                        <li key={item.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50">
                          <div className="w-10 h-10 bg-gray-100 dark:bg-slate-700 rounded-lg overflow-hidden flex-shrink-0">
                            {item.product_image && (
                              <img src={item.product_image} alt={item.product_name} className="w-full h-full object-cover" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{item.product_name}</p>
                            <p className="text-xs text-gray-400 dark:text-gray-500">
                              ¥{item.price} × {item.quantity}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ul>
                    {cart.items.length > 3 && (
                      <p className="text-xs text-gray-400 text-center mt-2">
                        还有 {cart.items.length - 3} 件商品
                      </p>
                    )}
                    <div className="flex justify-between items-center mt-3 pt-3 border-t dark:border-slate-700">
                      <span className="text-sm text-gray-500 dark:text-gray-400">合计</span>
                      <span className="text-sm font-bold text-gray-900 dark:text-gray-100">¥{cart.total_amount}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="mt-8">
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">快捷操作</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <ActionButton icon="💬" label="新对话" onClick={startNewChat} />
                <ActionButton icon="🗺️" label="规划行程" onClick={startNewChat} />
                <ActionButton icon="🥗" label="饮食计划" onClick={() => router.push("/diet")} />
                <ActionButton icon="🛍️" label="浏览商品" onClick={() => router.push("/products")} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/* Sub-components */

function StatCard({ icon, label, value, onClick }: { icon: string; label: string; value: number; onClick: () => void }) {
  return (
    <button onClick={onClick} className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-4 text-center hover:shadow-md transition">
      <p className="text-2xl mb-1">{icon}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
      <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">{label}</p>
    </button>
  );
}

function SectionHeader({ title, icon, onViewAll }: { title: string; icon: string; onViewAll: () => void }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-semibold text-gray-900 dark:text-gray-100">
        <span className="mr-1.5">{icon}</span>
        {title}
      </h3>
      <button onClick={onViewAll} className="text-xs text-blue-600 hover:text-blue-500 transition">
        查看全部 →
      </button>
    </div>
  );
}

function EmptyState({ message, action, onClick }: { message: string; action: string; onClick: () => void }) {
  return (
    <div className="text-center py-8">
      <p className="text-gray-400 dark:text-gray-500 text-sm">{message}</p>
      <button
        onClick={onClick}
        className="mt-2 text-xs px-3 py-1.5 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full hover:bg-blue-100 dark:hover:bg-blue-900/50 transition"
      >
        {action}
      </button>
    </div>
  );
}

function Badge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
    active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    confirmed: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    completed: "bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-gray-400",
    进行中: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  };
  const labelMap: Record<string, string> = {
    draft: "草稿",
    active: "进行中",
    confirmed: "已确认",
    completed: "已完成",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${colorMap[status] || "bg-gray-100 text-gray-600"}`}>
      {labelMap[status] || status}
    </span>
  );
}

function ActionButton({ icon, label, onClick }: { icon: string; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border dark:border-slate-700 p-4 text-center hover:shadow-md hover:border-blue-200 dark:hover:border-blue-700 transition"
    >
      <p className="text-xl mb-1">{icon}</p>
      <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</p>
    </button>
  );
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diff === 0) return "今天";
  if (diff === 1) return "昨天";
  if (diff < 7) return `${diff} 天前`;
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}
