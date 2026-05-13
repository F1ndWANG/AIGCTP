"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "motion/react";
import { ArrowRight, BookOpenText, Heart, MessageCircle, Plus, Search, Send, Share2, Star, Bookmark } from "lucide-react";

import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/UI/card";
import { Input } from "@/components/UI/input";
import { shares, travel } from "@/lib/api";
import type { TravelNote, TravelPlanResponse } from "@/lib/types";

function SharesPageContent() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { toast } = useToast();
  const [notes, setNotes] = useState<TravelNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [destination, setDestination] = useState("");
  const [tag, setTag] = useState("");
  const [mine, setMine] = useState(false);
  const [composeOpen, setComposeOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    title: "",
    content: "",
    destination: "",
    tags: "",
    visibility: "public" as "public" | "private",
    travel_plan_id: undefined as number | undefined,
  });

  const planId = Number(searchParams.get("planId") || 0);

  useEffect(() => {
    if (!user) return;
    loadNotes();
  }, [user, mine]);

  useEffect(() => {
    if (!user || !planId) return;
    travel.get(planId).then((plan) => {
      setComposeOpen(true);
      setForm(planToNoteForm(plan));
    }).catch(() => {});
  }, [user, planId]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  async function loadNotes(params?: { destination?: string; tag?: string }) {
    setLoading(true);
    try {
      const data = await shares.listNotes({
        destination: params?.destination ?? (destination || undefined),
        tag: params?.tag ?? (tag || undefined),
        mine,
        limit: 30,
      });
      setNotes(data);
    } catch {
      toast("加载分享内容失败", "error");
    } finally {
      setLoading(false);
    }
  }

  async function publishNote() {
    if (!form.title.trim() || !form.content.trim()) {
      toast("请填写标题和正文", "error");
      return;
    }
    setSubmitting(true);
    try {
      const note = await shares.createNote({
        title: form.title,
        content: form.content,
        destination: form.destination,
        tags: splitTags(form.tags),
        visibility: form.visibility,
        travel_plan_id: form.travel_plan_id,
      });
      setNotes((prev) => [note, ...prev]);
      setComposeOpen(false);
      setForm({ title: "", content: "", destination: "", tags: "", visibility: "public", travel_plan_id: undefined });
      toast("旅行笔记已发布", "success");
    } catch {
      toast("发布失败", "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleInteraction(note: TravelNote, type: "like" | "save") {
    const active = !note.viewer_interactions?.[type];
    setNotes((prev) => prev.map((item) => item.id === note.id ? optimisticInteraction(item, type, active) : item));
    try {
      const updated = await shares.interact(note.id, type, active);
      setNotes((prev) => prev.map((item) => item.id === note.id ? updated : item));
    } catch {
      setNotes((prev) => prev.map((item) => item.id === note.id ? note : item));
      toast("操作失败", "error");
    }
  }

  const hotTags = useMemo(() => {
    const counts = new Map<string, number>();
    notes.forEach((note) => note.tags.forEach((item) => counts.set(item, (counts.get(item) || 0) + 1)));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([name]) => name);
  }, [notes]);

  return (
    <motion.main initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="min-h-screen bg-background">
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-fuchsia-50 px-3 py-1 text-xs font-medium text-fuchsia-700 dark:bg-fuchsia-950/30 dark:text-fuchsia-300">
              <BookOpenText className="h-3.5 w-3.5" />
              旅行笔记社区
            </div>
            <h1 className="mt-3 text-2xl font-bold text-foreground">分享你的旅行灵感</h1>
            <p className="mt-1 text-sm text-muted-foreground">把已确认行程、真实体验和避坑建议沉淀下来，也会反哺你的推荐系统。</p>
          </div>
          <Button onClick={() => setComposeOpen((open) => !open)} className="gap-1.5">
            <Plus className="h-4 w-4" />
            写笔记
          </Button>
        </section>

        {composeOpen && (
          <Card className="border-fuchsia-200 dark:border-fuchsia-900">
            <CardHeader>
              <CardTitle>发布旅行笔记</CardTitle>
              <CardDescription>可以关联你的行程，也可以独立写一篇游记。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-[1fr_180px]">
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="标题，例如：天坛到南门涮肉的一日路线" />
                <Input value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} placeholder="目的地" />
              </div>
              <textarea
                value={form.content}
                onChange={(e) => setForm({ ...form, content: e.target.value })}
                placeholder="写下路线、餐厅、预算、注意事项、适合人群..."
                className="min-h-36 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <div className="grid gap-3 sm:grid-cols-[1fr_140px]">
                <Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="标签，用逗号分隔，例如：亲子,美食,citywalk" />
                <select
                  value={form.visibility}
                  onChange={(e) => setForm({ ...form, visibility: e.target.value as "public" | "private" })}
                  className="rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                >
                  <option value="public">公开</option>
                  <option value="private">仅自己可见</option>
                </select>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setComposeOpen(false)}>取消</Button>
                <Button onClick={publishNote} disabled={submitting} className="gap-1.5">
                  <Send className="h-4 w-4" />
                  {submitting ? "发布中..." : "发布"}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="pt-4 space-y-3">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input value={destination} onChange={(e) => setDestination(e.target.value)} placeholder="按目的地搜索" className="flex-1" />
              <Input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="标签" className="sm:w-36" />
              <Button onClick={() => loadNotes()} className="gap-1.5">
                <Search className="h-4 w-4" />
                搜索
              </Button>
              <Button variant={mine ? "default" : "outline"} onClick={() => setMine((value) => !value)}>
                我的
              </Button>
            </div>
            {hotTags.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {hotTags.map((item) => (
                  <button
                    key={item}
                    onClick={() => { setTag(item); loadNotes({ tag: item }); }}
                    className="rounded-full bg-muted px-2.5 py-1 text-xs text-muted-foreground transition hover:bg-fuchsia-100 hover:text-fuchsia-700 dark:hover:bg-fuchsia-950/40 dark:hover:text-fuchsia-300"
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
          </div>
        ) : notes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border py-16 text-center">
            <BookOpenText className="mx-auto mb-3 h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">暂无旅行笔记</p>
            <Button size="sm" className="mt-4" onClick={() => setComposeOpen(true)}>写第一篇</Button>
          </div>
        ) : (
          <div className="grid gap-4">
            {notes.map((note, index) => (
              <NoteCard
                key={note.id}
                note={note}
                index={index}
                onOpen={() => router.push(`/shares/${note.id}`)}
                onLike={() => toggleInteraction(note, "like")}
                onSave={() => toggleInteraction(note, "save")}
              />
            ))}
          </div>
        )}
      </div>
    </motion.main>
  );
}

function NoteCard({
  note,
  index,
  onOpen,
  onLike,
  onSave,
}: {
  note: TravelNote;
  index: number;
  onOpen: () => void;
  onLike: () => void;
  onSave: () => void;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className="rounded-xl border border-border bg-card p-4 transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <button onClick={onOpen} className="block w-full text-left">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              {note.destination && <Badge variant="secondary">{note.destination}</Badge>}
              {note.is_featured && <Badge><Star className="mr-1 h-3 w-3" />精选</Badge>}
              <span className="text-xs text-muted-foreground">{note.author.display_name}</span>
            </div>
            <h2 className="text-lg font-semibold text-foreground">{note.title}</h2>
            <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{note.content}</p>
          </div>
          <ArrowRight className="mt-8 h-4 w-4 shrink-0 text-muted-foreground" />
        </div>
      </button>
      {note.tags.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {note.tags.slice(0, 6).map((tag) => <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{tag}</span>)}
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <InteractionButton active={!!note.viewer_interactions.like} icon={<Heart className="h-3.5 w-3.5" />} label={String(note.like_count)} onClick={onLike} />
        <InteractionButton active={!!note.viewer_interactions.save} icon={<Bookmark className="h-3.5 w-3.5" />} label={String(note.save_count)} onClick={onSave} />
        <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1"><MessageCircle className="h-3.5 w-3.5" />{note.comment_count}</span>
        <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1"><Share2 className="h-3.5 w-3.5" />{note.share_count}</span>
      </div>
    </motion.article>
  );
}

function InteractionButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 transition ${
        active ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950/50 dark:text-fuchsia-300" : "bg-muted hover:bg-muted/70"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function splitTags(value: string): string[] {
  return value.split(/[,，\s]+/).map((item) => item.trim()).filter(Boolean).slice(0, 12);
}

function planToNoteForm(plan: TravelPlanResponse) {
  const itinerary = plan.itinerary;
  const days = itinerary?.day_by_day || [];
  const route = days.map((day) => {
    const acts = day.activities?.map((act) => act.poi).filter(Boolean).join(" -> ");
    return `第 ${day.day} 天：${day.theme || acts || "自由探索"}${acts ? `\n${acts}` : ""}`;
  }).join("\n\n");
  return {
    title: `${plan.destination}${plan.days}天旅行笔记`,
    content: route || `${plan.destination}${plan.days}天行程体验记录。`,
    destination: plan.destination,
    tags: ["行程", plan.destination, itinerary?.theme].filter(Boolean).join(","),
    visibility: "public" as const,
    travel_plan_id: plan.id,
  };
}

function optimisticInteraction(note: TravelNote, type: "like" | "save", active: boolean): TravelNote {
  const countKey = `${type}_count` as "like_count" | "save_count";
  const current = note[countKey] || 0;
  return {
    ...note,
    [countKey]: Math.max(0, current + (active ? 1 : -1)),
    viewer_interactions: { ...note.viewer_interactions, [type]: active },
  };
}

export default function SharesPage() {
  return (
    <Suspense>
      <SharesPageContent />
    </Suspense>
  );
}
