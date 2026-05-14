import { request } from "../api-client";
import type {
  RecommendationDomain,
  RecommendationEventBatchPayload,
  RecommendationEventPayload,
  RecommendationFeedbackPayload,
  RecommendationFeedResponse,
  RecommendationProfile,
} from "../types";

export const recommendation = {
  getFeed: (domain: RecommendationDomain = "home", limit = 12) =>
    request<RecommendationFeedResponse>(
      `/recommend/feed?domain=${encodeURIComponent(domain)}&limit=${limit}`
    ),
  getProfile: () => request<RecommendationProfile>("/recommend/profile"),
  trackEvent: (data: RecommendationEventPayload) =>
    request<{ status: string; id: number }>("/recommend/events", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  trackEvents: (data: RecommendationEventBatchPayload) =>
    request<{ status: string; count: number; ids: number[] }>("/recommend/events/batch", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  feedback: (data: RecommendationFeedbackPayload) =>
    request<{ status: string; id: number }>("/recommend/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  rebuildCatalog: (domain?: RecommendationDomain) =>
    request<{ status: string; synced: number; algorithm: string }>("/recommend/catalog/rebuild", {
      method: "POST",
      body: JSON.stringify({ domain: domain === "home" ? undefined : domain }),
    }),
  refreshFeatures: (domain?: RecommendationDomain) =>
    request<{ status: string; snapshots: number; algorithm: string }>("/recommend/features/refresh", {
      method: "POST",
      body: JSON.stringify({ domain: domain === "home" ? undefined : domain }),
    }),
};
