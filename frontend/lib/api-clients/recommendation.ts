import { request } from "../api-client";
import type {
  RecommendationDomain,
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
  feedback: (data: RecommendationFeedbackPayload) =>
    request<{ status: string; id: number }>("/recommend/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
