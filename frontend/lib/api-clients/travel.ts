import { request } from "../api-client";
import type { RouteResponse, TravelPlanListItem, TravelPlanResponse } from "../types";

export const travel = {
  list: () => request<TravelPlanListItem[]>("/travel/plans"),
  get: (id: number) => request<TravelPlanResponse>(`/travel/plans/${id}`),
  confirm: (id: number) =>
    request<TravelPlanResponse>(`/travel/plans/${id}/confirm`, {
      method: "POST",
    }),
  delete: (id: number) =>
    request<{ status: string }>(`/travel/plans/${id}`, {
      method: "DELETE",
    }),
};

export const route = {
  get: (params: {
    destination_name: string;
    destination_lat?: number;
    destination_lng?: number;
    origin_lat: number;
    origin_lng: number;
    city?: string;
    mode?: string;
  }) =>
    request<RouteResponse>("/route", {
      method: "POST",
      body: JSON.stringify({ ...params, mode: params.mode || "transit" }),
    }),
};
