"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "motion/react";
import {
  Map,
  Apple,
  MessageCircle,
  ShoppingCart,
  Plus,
  Sparkles,
  ArrowRight,
  Package,
} from "lucide-react";

import { useAuth } from "@/components/Layout/AuthProvider";
import { travel, diet, chat as chatApi, commerce } from "@/lib/api";
import { setActiveSessionId } from "@/lib/session";
import { Card } from "@/components/UI/card";
import { Badge } from "@/components/UI/badge";
import { MagicCard } from "@/components/UI/magic-card";
import { NumberTicker } from "@/components/UI/number-ticker";
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
  const recentChats = chatSessions.slice(0, 5);

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
    <div className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Greeting */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h2 className="text-2xl font-bold text-foreground">
            你好，{user.display_name}
          </h2>
          <p className="text-muted-foreground text-sm mt-1">
            今天想做什么？
          </p>
        </motion.div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {/* Quick Stats */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8"
            >
              <StatCard
                icon={<Map className="h-5 w-5 text-fuchsia-500" />}
                label="进行中的行程"
                value={activeTravel.length}
                onClick={() => router.push("/plans")}
              />
              <StatCard
                icon={<Apple className="h-5 w-5 text-green-500" />}
                label="饮食计划"
                value={activeDiet.length}
                onClick={() => router.push("/diet")}
              />
              <StatCard
                icon={<MessageCircle className="h-5 w-5 text-blue-500" />}
                label="最近对话"
                value={chatSessions.length}
                onClick={() => router.push("/chat")}
              />
              <StatCard
                icon={<ShoppingCart className="h-5 w-5 text-amber-500" />}
                label="购物车"
                value={cart?.items?.length || 0}
                onClick={() => router.push("/cart")}
              />
            </motion.div>

            {/* Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Active Travel Plan */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <Card size="default" className="p-0">
                  <div className="p-5">
                    <SectionHeader
                      title="进行中的行程"
                      icon={<Map className="h-4 w-4 text-fuchsia-500" />}
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
                        {activeTravel.slice(0, 3).map((p, i) => (
                          <motion.li
                            key={p.id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.2 + i * 0.05 }}
                          >
                            <button
                              onClick={() => router.push(`/travel/${p.id}`)}
                              className="w-full text-left flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition"
                            >
                              <div>
                                <p className="text-sm font-medium text-foreground">{p.destination}</p>
                                <p className="text-xs text-muted-foreground">{p.days} 天 · {formatDate(p.created_at)}</p>
                              </div>
                              <Badge variant={statusToBadge(p.status)}>{statusLabel(p.status)}</Badge>
                            </button>
                          </motion.li>
                        ))}
                      </ul>
                    )}
                  </div>
                </Card>
              </motion.div>

              {/* Active Diet Plan */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
              >
                <Card size="default" className="p-0">
                  <div className="p-5">
                    <SectionHeader
                      title="饮食计划"
                      icon={<Apple className="h-4 w-4 text-green-500" />}
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
                        {activeDiet.slice(0, 3).map((p, i) => (
                          <motion.li
                            key={p.id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.25 + i * 0.05 }}
                          >
                            <button
                              onClick={() => router.push(`/diet`)}
                              className="w-full text-left flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 transition"
                            >
                              <div>
                                <p className="text-sm font-medium text-foreground">{p.title}</p>
                                <p className="text-xs text-muted-foreground">{p.duration_days} 天计划</p>
                              </div>
                              <Badge variant={p.status === "active" ? "default" : "secondary"}>
                                {p.status === "active" ? "进行中" : p.status}
                              </Badge>
                            </button>
                          </motion.li>
                        ))}
                      </ul>
                    )}
                  </div>
                </Card>
              </motion.div>

              {/* Recent Chat Sessions */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.25 }}
              >
                <Card size="default" className="p-0">
                  <div className="p-5">
                    <SectionHeader
                      title="最近对话"
                      icon={<MessageCircle className="h-4 w-4 text-blue-500" />}
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
                        {recentChats.map((s, i) => (
                          <motion.li
                            key={s.session_id}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 + i * 0.03 }}
                          >
                            <button
                              onClick={() => restoreChat(s.session_id)}
                              className="w-full text-left p-3 rounded-lg hover:bg-muted/50 transition"
                            >
                              <p className="text-sm font-medium text-foreground truncate">{s.title || "未命名对话"}</p>
                              <p className="text-xs text-muted-foreground mt-0.5 truncate">{s.last_preview}</p>
                              <p className="text-xs text-muted-foreground/50 mt-0.5">{formatDate(s.updated_at)}</p>
                            </button>
                          </motion.li>
                        ))}
                      </ul>
                    )}
                  </div>
                </Card>
              </motion.div>

              {/* Cart Summary */}
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <Card size="default" className="p-0">
                  <div className="p-5">
                    <SectionHeader
                      title="购物车"
                      icon={<ShoppingCart className="h-4 w-4 text-amber-500" />}
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
                            <li key={item.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-muted/50 transition">
                              <div className="w-10 h-10 bg-muted rounded-lg overflow-hidden flex-shrink-0">
                                {item.product_image && (
                                  <img src={item.product_image} alt={item.product_name} className="w-full h-full object-cover" />
                                )}
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-foreground truncate">{item.product_name}</p>
                                <p className="text-xs text-muted-foreground">
                                  ¥{item.price} × {item.quantity}
                                </p>
                              </div>
                            </li>
                          ))}
                        </ul>
                        {cart.items.length > 3 && (
                          <p className="text-xs text-muted-foreground text-center mt-2">
                            还有 {cart.items.length - 3} 件商品
                          </p>
                        )}
                        <div className="flex justify-between items-center mt-3 pt-3 border-t border-border">
                          <span className="text-sm text-muted-foreground">合计</span>
                          <span className="text-sm font-bold text-foreground">¥{cart.total_amount}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              </motion.div>
            </div>

            {/* Quick Actions */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              className="mt-8"
            >
              <h3 className="text-sm font-medium text-muted-foreground mb-3">快捷操作</h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <ActionButton icon={<MessageCircle className="h-5 w-5 text-fuchsia-500" />} label="新对话" onClick={startNewChat} />
                <ActionButton icon={<Map className="h-5 w-5 text-violet-500" />} label="规划行程" onClick={startNewChat} />
                <ActionButton icon={<Apple className="h-5 w-5 text-green-500" />} label="饮食计划" onClick={() => router.push("/diet")} />
                <ActionButton icon={<Package className="h-5 w-5 text-amber-500" />} label="浏览商品" onClick={() => router.push("/products")} />
              </div>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Sub-components ── */

function StatCard({
  icon,
  label,
  value,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-card rounded-xl border border-border p-4 text-center hover:shadow-md hover:-translate-y-0.5 transition-all"
    >
      <div className="mx-auto mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-muted">
        {icon}
      </div>
      <div className="flex min-h-[32px] items-center justify-center">
        <NumberTicker
          value={value}
          className="text-3xl font-bold leading-none text-foreground"
          direction="up"
        />
      </div>
      <p className="mt-3 text-xs text-muted-foreground">{label}</p>
    </button>
  );
}

function SectionHeader({
  title,
  icon,
  onViewAll,
}: {
  title: string;
  icon: React.ReactNode;
  onViewAll: () => void;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-semibold text-foreground flex items-center gap-1.5">
        {icon}
        {title}
      </h3>
      <button
        onClick={onViewAll}
        className="inline-flex items-center gap-0.5 text-xs text-primary hover:text-primary/80 transition-colors"
      >
        查看全部 <ArrowRight className="h-3 w-3" />
      </button>
    </div>
  );
}

function EmptyState({
  message,
  action,
  onClick,
}: {
  message: string;
  action: string;
  onClick: () => void;
}) {
  return (
    <div className="text-center py-8">
      <p className="text-muted-foreground text-sm">{message}</p>
      <button
        onClick={onClick}
        className="mt-2 inline-flex items-center gap-1 text-xs px-3 py-1.5 bg-primary/10 text-primary rounded-full hover:bg-primary/20 transition-colors"
      >
        <Plus className="h-3 w-3" /> {action}
      </button>
    </div>
  );
}

function ActionButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-card rounded-xl border border-border p-4 text-center hover:shadow-md hover:border-primary/20 hover:-translate-y-0.5 transition-all"
    >
      <div className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-muted mb-2 mx-auto">
        {icon}
      </div>
      <p className="text-sm font-medium text-foreground">{label}</p>
    </button>
  );
}

/* ── Helpers ── */

function statusToBadge(status: string): "default" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    draft: "secondary",
    active: "default",
    confirmed: "default",
    completed: "outline",
  };
  return map[status] || "secondary";
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: "草稿",
    active: "进行中",
    confirmed: "已确认",
    completed: "已完成",
  };
  return map[status] || status;
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
