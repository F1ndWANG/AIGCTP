"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { diet as dietApi } from "@/lib/api";
import { chatHref } from "@/lib/session";
import MealLogCard from "@/components/Diet/MealLogCard";
import HealthProfileForm from "@/components/Diet/HealthProfileForm";
import DietPlanCard from "@/components/Diet/DietPlanCard";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/UI/tabs";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/UI/card";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Textarea } from "@/components/UI/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/UI/dialog";
import { ArrowLeft, Download, Share2, Plus, ChevronLeft } from "lucide-react";
import { motion } from "motion/react";
import type { MealRecord, HealthProfile, DietPlanListItem, DietPlan } from "@/lib/types";

type Tab = "log" | "profile" | "plans";

function formatMealType(mealType: string): string {
  if (mealType === "breakfast") return "早餐";
  if (mealType === "lunch") return "午餐";
  if (mealType === "dinner") return "晚餐";
  if (mealType === "snack") return "加餐";
  return mealType;
}

function getActivePlanDay(plan: DietPlan): number | null {
  if (!plan.activated_at || plan.status !== "active") return null;
  const activated = new Date(plan.activated_at);
  if (Number.isNaN(activated.getTime())) return null;

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  const activatedStart = new Date(activated);
  activatedStart.setHours(0, 0, 0, 0);

  const diffDays = Math.floor(
    (todayStart.getTime() - activatedStart.getTime()) / 86_400_000
  ) + 1;

  if (diffDays < 1 || diffDays > plan.duration_days) return null;
  return diffDays;
}

function TodayPlanReminder({ plan }: { plan: DietPlan }) {
  const activeDay = getActivePlanDay(plan);
  const today = activeDay
    ? plan.meals?.day_by_day?.find((day) => day.day === activeDay)
    : null;

  if (!activeDay || !today) return null;

  return (
    <Card className="border-fuchsia-200 dark:border-fuchsia-900">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-fuchsia-800 dark:text-fuchsia-300">今日饮食计划提醒</CardTitle>
            <p className="text-xs text-fuchsia-600 dark:text-fuchsia-400 mt-1">
              {plan.title} · 第 {activeDay} / {plan.duration_days} 天
            </p>
          </div>
          <Badge variant="default" className="bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900 dark:text-fuchsia-300">
            进行中
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {today.meals.map((meal, index) => (
            <div key={index} className="bg-fuchsia-50/50 dark:bg-fuchsia-950/30 rounded-lg p-3 border border-fuchsia-100 dark:border-fuchsia-900">
              <p className="text-xs font-medium text-fuchsia-700 dark:text-fuchsia-300 mb-2">
                {formatMealType(meal.meal_type)}
              </p>
              <div className="space-y-1">
                {meal.foods.map((food, foodIndex) => (
                  <p key={foodIndex} className="text-xs text-muted-foreground">
                    {food.name} ({food.amount})
                  </p>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DietPage() {
  const { user, loading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("log");

  const [meals, setMeals] = useState<MealRecord[]>([]);
  const [mealDate, setMealDate] = useState(new Date().toISOString().split("T")[0]);
  const [showAddMeal, setShowAddMeal] = useState(false);
  const [newMealType, setNewMealType] = useState("lunch");
  const [newFoodInput, setNewFoodInput] = useState("");

  const [profile, setProfile] = useState<HealthProfile | null>(null);
  const [dietPlans, setDietPlans] = useState<DietPlanListItem[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<DietPlan | null>(null);
  const [activeReminderPlan, setActiveReminderPlan] = useState<DietPlan | null>(null);

  // Delete confirmation dialog state
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const loadMeals = useCallback(async () => {
    try {
      const data = await dietApi.getMeals(mealDate);
      setMeals(data);
    } catch {
      // ignore empty state
    }
  }, [mealDate]);

  const loadProfile = useCallback(async () => {
    try {
      const data = await dietApi.getProfile();
      setProfile(data);
    } catch {
      // profile may not exist yet
    }
  }, []);

  const loadActiveReminder = useCallback(async () => {
    try {
      const plans = await dietApi.getPlans();
      const activePlan = plans.find((plan) => plan.status === "active" && plan.activated_at);
      if (!activePlan) {
        setActiveReminderPlan(null);
        return;
      }

      const fullPlan = await dietApi.getPlan(activePlan.id);
      setActiveReminderPlan(getActivePlanDay(fullPlan) ? fullPlan : null);
    } catch {
      setActiveReminderPlan(null);
    }
  }, []);

  const loadPlans = useCallback(async () => {
    try {
      const data = await dietApi.getPlans();
      setDietPlans(data);
    } catch {
      // ignore empty state
    }
  }, []);

  const refreshPlans = useCallback(async () => {
    await Promise.all([loadPlans(), loadActiveReminder()]);
  }, [loadPlans, loadActiveReminder]);

  useEffect(() => {
    if (!loading && user) loadActiveReminder();
  }, [loading, user, loadActiveReminder]);

  useEffect(() => {
    if (activeTab === "log") loadMeals();
    else if (activeTab === "profile") loadProfile();
    else if (activeTab === "plans") loadPlans();
  }, [activeTab, loadMeals, loadProfile, loadPlans]);

  if (loading) {
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

  if (!user) {
    router.push("/");
    return null;
  }

  const handleAddMeal = async () => {
    if (!newFoodInput.trim()) return;
    const foods = newFoodInput
      .split(/[,，、\n]/)
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      await dietApi.createMeal({
        date: mealDate,
        meal_type: newMealType,
        foods: foods.map((name) => ({ name, amount: "一份" })),
      });
      toast("已记录饮食", "success");
      setNewFoodInput("");
      setShowAddMeal(false);
      loadMeals();
    } catch {
      toast("记录失败", "error");
    }
  };

  const handleDeleteMeal = async (id: number) => {
    try {
      await dietApi.deleteMeal(id);
      loadMeals();
    } catch {
      toast("删除失败", "error");
    }
  };

  const handleSaveProfile = async (data: Partial<HealthProfile>) => {
    try {
      const updated = await dietApi.updateProfile(data);
      setProfile(updated);
      toast("健康档案已保存", "success");
    } catch {
      toast("保存失败", "error");
    }
  };

  const handleConfirmPlan = async (id: number) => {
    try {
      const updated = await dietApi.confirmPlan(id);
      toast("计划已确认，今日提醒已开启", "success");
      if (selectedPlan?.id === id) setSelectedPlan(updated);
      await refreshPlans();
    } catch {
      toast("确认失败", "error");
    }
  };

  const handleDeletePlan = (id: number) => {
    setDeleteConfirmId(id);
  };

  const confirmDeleteDietPlan = async () => {
    if (deleteConfirmId === null) return;
    try {
      await dietApi.deletePlan(deleteConfirmId);
      toast("饮食计划已删除", "success");
      if (selectedPlan?.id === deleteConfirmId) setSelectedPlan(null);
      await refreshPlans();
    } catch {
      toast("删除失败", "error");
    }
    setDeleteConfirmId(null);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen flex flex-col bg-background"
    >
      <Tabs
        value={activeTab}
        onValueChange={(v) => {
          setActiveTab(v as Tab);
          setSelectedPlan(null);
        }}
      >
        <div className="flex-1 max-w-4xl mx-auto w-full p-4 space-y-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push(chatHref())}
                className="mb-2 -ml-2 gap-1 text-muted-foreground"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                返回对话
              </Button>
              <h1 className="text-2xl font-bold text-foreground">饮食健康</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                记录饮食、维护健康档案，饮食计划会在生成后显示。
              </p>
            </div>
            <TabsList variant="line" className="self-start sm:self-auto">
              <TabsTrigger value="log">饮食日志</TabsTrigger>
              <TabsTrigger value="profile">健康档案</TabsTrigger>
              <TabsTrigger value="plans">饮食计划</TabsTrigger>
            </TabsList>
          </div>

          {activeReminderPlan && <TodayPlanReminder plan={activeReminderPlan} />}

          <TabsContent value="log">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <input
                  type="date"
                  value={mealDate}
                  onChange={(e) => setMealDate(e.target.value)}
                  className="border border-input rounded-lg px-3 py-1.5 text-sm bg-transparent"
                />
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => setShowAddMeal(!showAddMeal)}
                  className="gap-1"
                >
                  <Plus className="w-3.5 h-3.5" />
                  添加记录
                </Button>
              </div>

              {showAddMeal && (
                <Card size="sm">
                  <CardContent className="space-y-3 pt-3">
                    <select
                      value={newMealType}
                      onChange={(e) => setNewMealType(e.target.value)}
                      className="border border-input rounded-lg px-3 py-1.5 text-sm w-full bg-transparent"
                    >
                      <option value="breakfast">早餐</option>
                      <option value="lunch">午餐</option>
                      <option value="dinner">晚餐</option>
                      <option value="snack">加餐</option>
                    </select>
                    <Textarea
                      value={newFoodInput}
                      onChange={(e) => setNewFoodInput(e.target.value)}
                      rows={2}
                      placeholder="输入食物名称（用逗号或换行分隔），例如：米饭, 鸡胸肉, 青菜"
                    />
                    <div className="flex gap-2">
                      <Button variant="default" size="sm" onClick={handleAddMeal}>
                        保存
                      </Button>
                      <Button variant="outline" size="sm" onClick={() => setShowAddMeal(false)}>
                        取消
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {meals.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground text-sm">暂无饮食记录</p>
                  <p className="text-muted-foreground/50 text-xs mt-1">
                    点击"添加记录"开始记录今天的饮食
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {meals.map((meal) => (
                    <MealLogCard key={meal.id} record={meal} onDelete={handleDeleteMeal} />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="profile">
            <div className="max-w-lg mx-auto">
              <HealthProfileForm profile={profile} onSave={handleSaveProfile} />
            </div>
          </TabsContent>

          <TabsContent value="plans">
            <div>
              {selectedPlan ? (
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedPlan(null)}
                    className="gap-1 mb-4"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                    返回列表
                  </Button>
                  <DietPlanCard
                    plan={selectedPlan}
                    onConfirm={handleConfirmPlan}
                    onDelete={handleDeletePlan}
                  />
                </div>
              ) : dietPlans.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-muted-foreground text-sm">暂无饮食计划</p>
                  <p className="text-muted-foreground/50 text-xs mt-1">
                    在对话中告诉 AI "帮我做一周的减肥饮食计划" 来生成计划
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {dietPlans.map((plan) => (
                    <Card key={plan.id} className="hover:shadow-md transition-shadow">
                      <div onClick={async () => {
                        try {
                          const full = await dietApi.getPlan(plan.id);
                          setSelectedPlan(full);
                        } catch {
                          // ignore
                        }
                      }}>
                        <CardHeader>
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <CardTitle className="truncate">
                                {plan.title || "饮食计划"}
                              </CardTitle>
                              <p className="text-sm text-muted-foreground mt-1">
                                {plan.duration_days}天 · {plan.status === "draft" ? "草稿" : plan.status === "active" ? "进行中" : "已完成"}
                              </p>
                            </div>
                            <Badge
                              variant={plan.status === "active" ? "default" : "outline"}
                              className={plan.status === "active" ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900 dark:text-fuchsia-300" : ""}
                            >
                              {plan.status === "active" ? "进行中" : "草稿"}
                            </Badge>
                          </div>
                        </CardHeader>
                      </div>
                      <CardFooter>
                        <div className="flex gap-2 w-full">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              toast("功能即将上线", "success");
                            }}
                          >
                            <Download className="w-3.5 h-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              toast("功能即将上线", "success");
                            }}
                          >
                            <Share2 className="w-3.5 h-3.5" />
                          </Button>
                          {plan.status === "draft" && (
                            <Button
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleConfirmPlan(plan.id);
                              }}
                              className="ml-auto"
                            >
                              确认计划
                            </Button>
                          )}
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeletePlan(plan.id);
                            }}
                          >
                            删除
                          </Button>
                        </div>
                      </CardFooter>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </div>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteConfirmId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定删除这个饮食计划吗？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2 justify-end mt-2">
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDeleteDietPlan}>
              删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
