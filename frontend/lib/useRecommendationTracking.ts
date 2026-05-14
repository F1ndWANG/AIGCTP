"use client";

import { useCallback } from "react";

import { recommendation } from "@/lib/api-clients/recommendation";
import type {
  RecommendationDomain,
  RecommendationEventPayload,
  RecommendationEventType,
  RecommendationFeedbackPayload,
  RecommendationFeedItem,
} from "@/lib/types";

type TrackBase = {
  domain: RecommendationDomain;
  item_type: string;
  item_id: string | number;
  context?: Record<string, unknown>;
  session_id?: string;
  impression_id?: string;
};

export function recommendationItemKey(item: Pick<RecommendationFeedItem, "domain" | "item_type" | "item_id">): string {
  return `${item.domain}:${item.item_type}:${item.item_id}`;
}

export function useRecommendationTracking(source: string, sessionId?: string | null) {
  const track = useCallback(
    (event: TrackBase & { event_type: RecommendationEventType; weight?: number }) => {
      const payload: RecommendationEventPayload = {
        domain: event.domain,
        item_type: event.item_type,
        item_id: event.item_id,
        event_type: event.event_type,
        weight: event.weight,
        session_id: event.session_id ?? sessionId ?? undefined,
        impression_id: event.impression_id,
        context: {
          source,
          ...(event.context || {}),
        },
      };
      recommendation.trackEvent(payload).catch(() => {});
    },
    [sessionId, source]
  );

  const feedback = useCallback(
    (event: TrackBase & { feedback: RecommendationFeedbackPayload["feedback"] }) => {
      const payload: RecommendationFeedbackPayload = {
        domain: event.domain,
        item_type: event.item_type,
        item_id: event.item_id,
        feedback: event.feedback,
        session_id: event.session_id ?? sessionId ?? undefined,
        impression_id: event.impression_id,
        context: {
          source,
          ...(event.context || {}),
        },
      };
      recommendation.feedback(payload).catch(() => {});
    },
    [sessionId, source]
  );

  const trackFeedViews = useCallback(
    (items: RecommendationFeedItem[], limit = 8) => {
      const events = items.slice(0, limit).map((item) => ({
        domain: item.domain,
        item_type: item.item_type,
        item_id: item.item_id,
        event_type: "view" as RecommendationEventType,
        session_id: sessionId ?? undefined,
        impression_id: item.impression_id,
        context: { source, title: item.title, rank: item.rank, algorithm: item.algorithm },
      }));
      if (events.length) recommendation.trackEvents({ events }).catch(() => {});
    },
    [sessionId, source]
  );

  return { track, feedback, trackFeedViews };
}
