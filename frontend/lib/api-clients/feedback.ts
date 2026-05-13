import { request } from "../api-client";
import type { RecommendationFeedback } from "../types";

export const feedback = {
  submit: (data: RecommendationFeedback) =>
    request<{ status: string; id: number }>("/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  stats: () =>
    request<Array<{ content_type: string; likes: number; dislikes: number }>>("/feedback/stats"),
  analytics: {
    summary: () =>
      request<{
        total_interactions: number;
        by_content_type: Record<string, { total: number; likes: number; dislikes: number }>;
      }>("/feedback/analytics/summary"),
  },
};
