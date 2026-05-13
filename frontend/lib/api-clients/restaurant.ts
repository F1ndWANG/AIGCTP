import { request } from "../api-client";
import type { RestaurantRecommendation, SavedRestaurantRecommendation } from "../types";

export const restaurant = {
  recommend: (city: string, cuisine?: string, session_id?: string) =>
    request<RestaurantRecommendation>("/restaurant/recommend", {
      method: "POST",
      body: JSON.stringify({ city, cuisine, session_id }),
    }),
  nearby: (lat: number, lng: number, radius?: number, session_id?: string) =>
    request<RestaurantRecommendation>("/restaurant/nearby", {
      method: "POST",
      body: JSON.stringify({ lat, lng, radius, session_id }),
    }),
  listRecommendations: (session_id?: string) =>
    request<SavedRestaurantRecommendation[]>(
      `/restaurant/recommendations${session_id ? `?session_id=${encodeURIComponent(session_id)}` : ""}`
    ),
  getRecommendation: (id: number) =>
    request<SavedRestaurantRecommendation>(`/restaurant/recommendations/${id}`),
  selectRecommendation: (id: number, restaurant: Record<string, unknown>) =>
    request<SavedRestaurantRecommendation>(`/restaurant/recommendations/${id}/select`, {
      method: "POST",
      body: JSON.stringify({ restaurant }),
    }),
  deleteRecommendation: (id: number) =>
    request<{ status: string }>(`/restaurant/recommendations/${id}`, {
      method: "DELETE",
    }),
};
