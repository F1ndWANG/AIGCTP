"use client";

import { useEffect, useMemo, useRef } from "react";
import { Activity, Apple, ArrowRight, HeartPulse, Map as MapIcon, Package, Sparkles, UtensilsCrossed, X } from "lucide-react";

import { Card } from "@/components/UI/card";
import type { RecommendationFeedItem, RecommendationProfile } from "@/lib/types";

export function RecommendationStrip({
  items,
  onOpen,
  onHide,
  onView,
}: {
  items: RecommendationFeedItem[];
  onOpen: (item: RecommendationFeedItem) => void;
  onHide: (item: RecommendationFeedItem) => void;
  onView?: (items: RecommendationFeedItem[]) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewedKeysRef = useRef<Set<string>>(new Set());
  const itemByKey = useMemo(() => {
    return new Map(items.map((item) => [recommendationKey(item), item]));
  }, [items]);

  useEffect(() => {
    if (!onView || !containerRef.current || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible: RecommendationFeedItem[] = [];
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const key = (entry.target as HTMLElement).dataset.recKey;
          if (!key || viewedKeysRef.current.has(key)) return;
          const item = itemByKey.get(key);
          if (!item) return;
          viewedKeysRef.current.add(key);
          visible.push(item);
          observer.unobserve(entry.target);
        });
        if (visible.length) onView(visible);
      },
      { threshold: 0.6 }
    );
    const nodes = containerRef.current.querySelectorAll<HTMLElement>("[data-rec-key]");
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, [itemByKey, onView]);

  return (
    <Card size="default" className="p-0 overflow-hidden">
      <div className="p-5">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="flex items-center gap-1.5 font-semibold text-foreground">
              <Sparkles className="h-4 w-4 text-fuchsia-500" />
              为你推荐
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">根据你的对话、选择和收藏动态排序</p>
          </div>
        </div>
        <div ref={containerRef} className="flex gap-3 overflow-x-auto pb-1">
          {items.slice(0, 10).map((item) => (
            <RecommendationCard
              key={`${item.domain}:${item.item_type}:${item.item_id}`}
              item={item}
              onOpen={() => onOpen(item)}
              onHide={() => onHide(item)}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}

export function RecommendationProfilePanel({ profile }: { profile: RecommendationProfile }) {
  const topTerms = profile.top_terms.filter((item) => !isInternalProfileTerm(item.term)).slice(0, 10);
  return (
    <Card size="default" className="p-0 overflow-hidden">
      <div className="p-5">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h3 className="flex items-center gap-1.5 font-semibold text-foreground">
              <Activity className="h-4 w-4 text-fuchsia-500" />
              推荐画像
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              已学习 {profile.event_count} 个行为信号，隐藏 {profile.negative_item_count} 个不感兴趣项
            </p>
          </div>
        </div>
        {topTerms.length === 0 ? (
          <div className="rounded-lg bg-muted/60 px-3 py-3 text-sm text-muted-foreground">
            和 AI 多聊几次、浏览商品或分享游记后，这里会出现你的兴趣关键词。
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {topTerms.map((item) => (
              <span
                key={item.term}
                className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground"
                title={`权重 ${item.weight}`}
              >
                {item.term}
              </span>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function isInternalProfileTerm(term: string): boolean {
  const normalized = term.toLowerCase();
  const hidden = new Set([
    "source",
    "dashboard_feed",
    "title",
    "rank",
    "algorithm",
    "hybrid_v2",
    "item_id",
    "item_type",
    "domain",
  ]);
  return hidden.has(normalized);
}

export function recommendationFallbackUrl(domain: RecommendationFeedItem["domain"]): string {
  const map: Record<RecommendationFeedItem["domain"], string> = {
    home: "/chat",
    commerce: "/products",
    restaurant: "/restaurants",
    travel: "/plans",
    diet: "/diet",
  };
  return map[domain];
}

function RecommendationCard({
  item,
  onOpen,
  onHide,
}: {
  item: RecommendationFeedItem;
  onOpen: () => void;
  onHide: () => void;
}) {
  const Icon = domainIcon(item.domain);
  return (
    <div
      data-rec-key={recommendationKey(item)}
      className="group relative min-w-[220px] max-w-[220px] rounded-xl border border-border bg-background p-4 transition-all hover:-translate-y-0.5 hover:border-fuchsia-200 hover:shadow-md"
    >
      <button
        type="button"
        onClick={(event) => {
          event.stopPropagation();
          onHide();
        }}
        className="absolute right-2 top-2 inline-flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground opacity-0 transition hover:bg-muted hover:text-foreground group-hover:opacity-100"
        aria-label="不感兴趣"
        title="不感兴趣"
      >
        <X className="h-3.5 w-3.5" />
      </button>
      <button type="button" onClick={onOpen} className="block w-full text-left">
        <div className="mb-3 flex items-center gap-2">
          <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-950/40 dark:text-fuchsia-300">
            <Icon className="h-4 w-4" />
          </span>
          <span className="text-xs text-muted-foreground">{domainLabel(item.domain)}</span>
        </div>
        <p className="line-clamp-2 min-h-[40px] text-sm font-semibold text-foreground">{item.title}</p>
        {item.subtitle && <p className="mt-1 truncate text-xs text-muted-foreground">{item.subtitle}</p>}
        <p className="mt-3 line-clamp-2 min-h-[34px] text-xs text-muted-foreground">{item.reason}</p>
        <div className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-primary">
          查看 <ArrowRight className="h-3 w-3" />
        </div>
      </button>
    </div>
  );
}

function recommendationKey(item: Pick<RecommendationFeedItem, "domain" | "item_type" | "item_id">): string {
  return `${item.domain}:${item.item_type}:${item.item_id}`;
}

function domainLabel(domain: RecommendationFeedItem["domain"]): string {
  const map: Record<RecommendationFeedItem["domain"], string> = {
    home: "综合",
    commerce: "商品",
    restaurant: "餐厅",
    travel: "行程",
    diet: "饮食",
  };
  return map[domain];
}

function domainIcon(domain: RecommendationFeedItem["domain"]) {
  const map = {
    home: Sparkles,
    commerce: Package,
    restaurant: UtensilsCrossed,
    travel: MapIcon,
    diet: HeartPulse,
  };
  return map[domain] || Apple;
}
