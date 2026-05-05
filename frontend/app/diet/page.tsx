"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { diet as dietApi } from "@/lib/api";
import MealLogCard from "@/components/Diet/MealLogCard";
import HealthProfileForm from "@/components/Diet/HealthProfileForm";
import DietPlanCard from "@/components/Diet/DietPlanCard";
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
    <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div>
          <p className="text-sm font-semibold text-emerald-800">今日饮食计划提醒</p>
          <p className="text-xs text-emerald-600 mt-1">
            {plan.title} · 第 {activeDay} / {plan.duration_days} 天
          </p>
        </div>
        <span className="text-xs px-2 py-1 bg-emerald-100 text-emerald-700 rounded-full">
          进行中
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {today.meals.map((meal, index) => (
          <div key={index} className="bg-white/80 rounded-lg p-3 border border-emerald-100">
            <p className="text-xs font-medium text-emerald-700 mb-2">
              {formatMealType(meal.meal_type)}
            </p>
            <div className="space-y-1">
              {meal.foods.map((food, foodIndex) => (
                <p key={foodIndex} className="text-xs text-gray-600">
                  {food.name} ({food.amount})
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
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
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-green-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  const handleAddMeal = async () => {
    if (!newFoodInput.trim()) return;
    const foods = newFoodInput
      .split(/[,，、]/)
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

  const handleDeletePlan = async (id: number) => {
    if (!confirm("确定删除这个饮食计划吗？")) return;
    try {
      await dietApi.deletePlan(id);
      toast("饮食计划已删除", "success");
      if (selectedPlan?.id === id) setSelectedPlan(null);
      await refreshPlans();
    } catch {
      toast("删除失败", "error");
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "log", label: "饮食日志" },
    { key: "profile", label: "健康档案" },
    { key: "plans", label: "饮食计划" },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg">饮食健康</h1>
            <button
              onClick={() => router.push("/chat")}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition"
            >
              返回对话
            </button>
          </div>
          <span className="text-sm text-gray-500">{user.display_name}</span>
        </div>
      </header>

      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto flex">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveTab(tab.key);
                setSelectedPlan(null);
              }}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? "text-green-600 border-green-600"
                  : "text-gray-500 border-transparent hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 max-w-4xl mx-auto w-full p-4 space-y-4">
        {activeReminderPlan && <TodayPlanReminder plan={activeReminderPlan} />}

        {activeTab === "log" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <input
                type="date"
                value={mealDate}
                onChange={(e) => setMealDate(e.target.value)}
                className="border rounded-lg px-3 py-2 text-sm"
              />
              <button
                onClick={() => setShowAddMeal(!showAddMeal)}
                className="text-sm px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
              >
                + 添加记录
              </button>
            </div>

            {showAddMeal && (
              <div className="bg-white rounded-lg border p-4 space-y-3">
                <select
                  value={newMealType}
                  onChange={(e) => setNewMealType(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm w-full"
                >
                  <option value="breakfast">早餐</option>
                  <option value="lunch">午餐</option>
                  <option value="dinner">晚餐</option>
                  <option value="snack">加餐</option>
                </select>
                <textarea
                  value={newFoodInput}
                  onChange={(e) => setNewFoodInput(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 text-sm resize-none"
                  rows={2}
                  placeholder="输入食物名称，用逗号分隔，例如：米饭, 鸡胸肉, 青菜"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleAddMeal}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                  >
                    保存
                  </button>
                  <button
                    onClick={() => setShowAddMeal(false)}
                    className="px-4 py-2 border rounded-lg text-sm text-gray-600"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}

            {meals.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 text-sm">暂无饮食记录</p>
                <p className="text-gray-300 text-xs mt-1">
                  点击“添加记录”开始记录今天的饮食
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
        )}

        {activeTab === "profile" && (
          <div className="max-w-lg mx-auto">
            <HealthProfileForm profile={profile} onSave={handleSaveProfile} />
          </div>
        )}

        {activeTab === "plans" && (
          <div>
            {selectedPlan ? (
              <div>
                <button
                  onClick={() => setSelectedPlan(null)}
                  className="text-sm text-green-600 mb-4 hover:underline"
                >
                  返回列表
                </button>
                <DietPlanCard
                  plan={selectedPlan}
                  onConfirm={handleConfirmPlan}
                  onDelete={handleDeletePlan}
                />
              </div>
            ) : dietPlans.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 text-sm">暂无饮食计划</p>
                <p className="text-gray-300 text-xs mt-1">
                  在对话中告诉 AI “帮我做一周的减肥饮食计划” 来生成计划
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dietPlans.map((plan) => (
                  <div key={plan.id} className="text-left p-4 border rounded-xl bg-white hover:shadow-md transition">
                    <button
                      onClick={async () => {
                        try {
                          const full = await dietApi.getPlan(plan.id);
                          setSelectedPlan(full);
                        } catch {
                          // ignore
                        }
                      }}
                      className="block w-full text-left"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <h3 className="font-medium text-gray-900">
                            {plan.title || "饮食计划"}
                          </h3>
                          <p className="text-sm text-gray-400 mt-1">
                            {plan.duration_days}天 · {plan.status === "draft" ? "草稿" : plan.status === "active" ? "进行中" : "已完成"}
                          </p>
                        </div>
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          plan.status === "active"
                            ? "bg-green-100 text-green-700"
                            : "bg-gray-100 text-gray-600"
                        }`}>
                          {plan.status === "active" ? "进行中" : "草稿"}
                        </span>
                      </div>
                    </button>
                    <div className="flex gap-2 mt-4">
                      {plan.status === "draft" && (
                        <button
                          onClick={() => handleConfirmPlan(plan.id)}
                          className="flex-1 py-2 text-xs text-white bg-green-600 rounded-lg hover:bg-green-700"
                        >
                          确认计划
                        </button>
                      )}
                      <button
                        onClick={() => handleDeletePlan(plan.id)}
                        className="flex-1 py-2 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
