"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "motion/react";
import { ArrowLeft, Bookmark, Heart, MessageCircle, Send, Share2 } from "lucide-react";

import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Card, CardContent } from "@/components/UI/card";
import { shares } from "@/lib/api";
import type { TravelNote } from "@/lib/types";

export default function TravelNoteDetailPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const { toast } = useToast();
  const [note, setNote] = useState<TravelNote | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const noteId = Number(params.id);

  useEffect(() => {
    if (!user || !noteId) return;
    shares.getNote(noteId)
      .then(setNote)
      .catch(() => toast("加载笔记失败", "error"))
      .finally(() => setLoading(false));
  }, [user, noteId, toast]);

  if (authLoading || loading) {
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

  if (!note) {
    return <div className="min-h-screen py-16 text-center text-sm text-muted-foreground">笔记不存在</div>;
  }

  async function toggle(type: "like" | "save") {
    if (!note) return;
    const active = !note.viewer_interactions?.[type];
    const previous = note;
    setNote(optimisticInteraction(note, type, active));
    try {
      setNote(await shares.interact(note.id, type, active));
    } catch {
      setNote(previous);
      toast("操作失败", "error");
    }
  }

  async function shareNote() {
    if (!note) return;
    const text = `${note.title}\n\n${note.content.slice(0, 140)}...`;
    try {
      if (navigator.share) {
        await navigator.share({ title: note.title, text });
      } else {
        await navigator.clipboard.writeText(text);
        toast("笔记摘要已复制", "success");
      }
      setNote(await shares.interact(note.id, "share", true));
    } catch {
      // Native share cancellation should not show an error.
    }
  }

  async function submitComment() {
    if (!comment.trim() || !note) return;
    try {
      setNote(await shares.comment(note.id, comment.trim()));
      setComment("");
    } catch {
      toast("评论失败", "error");
    }
  }

  return (
    <motion.main initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
        <button onClick={() => router.push("/shares")} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          返回分享广场
        </button>

        <Card>
          <CardContent className="p-5 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {note.destination && <Badge variant="secondary">{note.destination}</Badge>}
              {note.tags.slice(0, 6).map((tag) => <span key={tag} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">{tag}</span>)}
            </div>
            <h1 className="text-2xl font-bold text-foreground">{note.title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {note.author.display_name} · {new Date(note.created_at).toLocaleDateString("zh-CN")}
            </p>

            <article className="mt-6 whitespace-pre-wrap text-sm leading-7 text-foreground">
              {note.content}
            </article>

            <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border pt-4">
              <ActionButton active={!!note.viewer_interactions.like} onClick={() => toggle("like")} icon={<Heart className="h-4 w-4" />} label={`喜欢 ${note.like_count}`} />
              <ActionButton active={!!note.viewer_interactions.save} onClick={() => toggle("save")} icon={<Bookmark className="h-4 w-4" />} label={`收藏 ${note.save_count}`} />
              <ActionButton active={false} onClick={shareNote} icon={<Share2 className="h-4 w-4" />} label={`分享 ${note.share_count}`} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5 space-y-4">
            <h2 className="flex items-center gap-2 font-semibold text-foreground">
              <MessageCircle className="h-4 w-4 text-fuchsia-500" />
              互动评论
            </h2>
            <div className="flex gap-2">
              <input
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && submitComment()}
                placeholder="写下你的问题或补充..."
                className="h-9 flex-1 rounded-lg border border-border bg-background px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              />
              <Button onClick={submitComment} className="gap-1.5">
                <Send className="h-4 w-4" />
                发送
              </Button>
            </div>
            {note.comments.length === 0 ? (
              <p className="rounded-lg bg-muted py-6 text-center text-sm text-muted-foreground">还没有评论</p>
            ) : (
              <div className="space-y-3">
                {note.comments.map((item) => (
                  <div key={item.id} className="rounded-lg bg-muted/60 p-3">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">{item.author.display_name}</span>
                      <span className="text-xs text-muted-foreground">{new Date(item.created_at).toLocaleString("zh-CN")}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{item.content}</p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </motion.main>
  );
}

function ActionButton({
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
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition ${
        active ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-950/50 dark:text-fuchsia-300" : "bg-muted text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function optimisticInteraction(note: TravelNote, type: "like" | "save", active: boolean): TravelNote {
  const countKey = `${type}_count` as "like_count" | "save_count";
  return {
    ...note,
    [countKey]: Math.max(0, (note[countKey] || 0) + (active ? 1 : -1)),
    viewer_interactions: { ...note.viewer_interactions, [type]: active },
  };
}
