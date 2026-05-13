import { request } from "../api-client";
import type { DietPlan, DietPlanListItem, HealthProfile, MealRecord, MealSummary } from "../types";

export const diet = {
  getProfile: () => request<HealthProfile>("/diet/profile"),
  updateProfile: (data: Partial<HealthProfile>) =>
    request<HealthProfile>("/diet/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  getMeals: (meal_date?: string) =>
    request<MealRecord[]>(`/diet/meals${meal_date ? `?meal_date=${meal_date}` : ""}`),
  getMealSummary: (meal_date?: string) =>
    request<MealSummary>(`/diet/meals/summary${meal_date ? `?meal_date=${meal_date}` : ""}`),
  createMeal: (data: {
    date: string;
    meal_type: string;
    foods: Array<{ name: string; amount: string }>;
    notes?: string;
  }) =>
    request<MealRecord>("/diet/meals", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  deleteMeal: (id: number) =>
    request<{ status: string }>(`/diet/meals/${id}`, {
      method: "DELETE",
    }),
  getPlans: () => request<DietPlanListItem[]>("/diet/plans"),
  getPlan: (id: number) => request<DietPlan>(`/diet/plans/${id}`),
  confirmPlan: (id: number) =>
    request<DietPlan>(`/diet/plans/${id}/confirm`, {
      method: "POST",
    }),
  deletePlan: (id: number) =>
    request<{ status: string }>(`/diet/plans/${id}`, {
      method: "DELETE",
    }),
};
