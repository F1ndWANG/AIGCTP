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

export default function DietPage() {
  const { user, loading, logout } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<Tab>("log");

  // Meal log state
  const [meals, setMeals] = useState<MealRecord[]>([]);
  const [mealDate, setMealDate] = useState(new Date().toISOString().split("T")[0]);
  const [showAddMeal, setShowAddMeal] = useState(false);
  const [newMealType, setNewMealType] = useState("lunch");
  const [newFoodInput, setNewFoodInput] = useState("");

  // Health profile state
  const [profile, setProfile] = useState<HealthProfile | null>(null);

  // Diet plans state
  const [dietPlans, setDietPlans] = useState<DietPlanListItem[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<DietPlan | null>(null);

  const loadMeals = useCallback(async () => {
    try {
      const data = await dietApi.getMeals(mealDate);
      setMeals(data);
    } catch { /* ignore */ }
  }, [mealDate]);

  const loadProfile = useCallback(async () => {
    try {
      const data = await dietApi.getProfile();
      setProfile(data);
    } catch { /* no profile yet */ }
  }, []);

  const loadPlans = useCallback(async () => {
    try {
      const data = await dietApi.getPlans();
      setDietPlans(data);
    } catch { /* ignore */ }
  }, []);

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
    const foods = newFoodInput.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
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

  const tabs: { key: Tab; label: string }[] = [
    { key: "log", label: "饮食日志" },
    { key: "profile", label: "健康档案" },
    { key: "plans", label: "饮食计划" },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="font-bold text-lg">饮食健康</h1>
            <button
              onClick={() => router.push("/chat")}
              className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition"
            >
              ← 返回对话
            </button>
          </div>
          <span className="text-sm text-gray-500">{user.display_name}</span>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto flex">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => { setActiveTab(tab.key); setSelectedPlan(null); }}
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

      {/* Content */}
      <div className="flex-1 max-w-4xl mx-auto w-full p-4">
        {activeTab === "log" && (
          <div className="space-y-4">
            {/* Date Picker + Add Button */}
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

            {/* Add Meal Form */}
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
                  placeholder="输入食物名称，用逗号分隔，例如：米饭, 红烧肉, 青菜"
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

            {/* Meal Records */}
            {meals.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 text-sm">暂无饮食记录</p>
                <p className="text-gray-300 text-xs mt-1">点击「添加记录」开始记录今天的饮食</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {meals.map((meal) => (
                  <MealLogCard
                    key={meal.id}
                    record={meal}
                    onDelete={handleDeleteMeal}
                  />
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
                  ← 返回列表
                </button>
                <DietPlanCard plan={selectedPlan} />
              </div>
            ) : dietPlans.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 text-sm">暂无饮食计划</p>
                <p className="text-gray-300 text-xs mt-1">
                  在对话中告诉 AI "帮我做一周的减肥饮食计划" 来生成计划
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {dietPlans.map((plan) => (
                  <button
                    key={plan.id}
                    onClick={async () => {
                      try {
                        const full = await dietApi.getPlan(plan.id);
                        setSelectedPlan(full);
                      } catch { /* ignore */ }
                    }}
                    className="text-left p-4 border rounded-xl bg-white hover:shadow-md transition"
                  >
                    <h3 className="font-medium text-gray-900">{plan.title || "饮食计划"}</h3>
                    <p className="text-sm text-gray-400 mt-1">
                      {plan.duration_days}天 · {plan.status === "draft" ? "草稿" : "进行中"}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
