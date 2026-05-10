"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useToast } from "@/components/UI/Toast";
import { travel as travelApi } from "@/lib/api";
import { chatHref, withSession } from "@/lib/session";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/UI/card";
import { Badge } from "@/components/UI/badge";
import { Button } from "@/components/UI/button";
import { Skeleton } from "@/components/UI/Skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/UI/dialog";
import { ArrowLeft, Map, Trash2 } from "lucide-react";
import { motion } from "motion/react";
import type { TravelPlanListItem } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  confirmed: "已确认",
  completed: "已完成",
};

const STATUS_BADGE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  draft: "outline",
  confirmed: "default",
  completed: "secondary",
};

export default function PlansPage() {
  const { user, loading: authLoading } = useAuth();
  const { toast } = useToast();
  const router = useRouter();
  const [plans, setPlans] = useState<TravelPlanListItem[]>([]);
  const [loading, setLoading] = useState(true);

  // Delete confirmation dialog state
  const [deleteConfirmId, setDeleteConfirmId] = useState<number | null>(null);

  const loadPlans = useCallback(async () => {
    setLoading(true);
    try {
      const data = await travelApi.list();
      setPlans(data);
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { if (!authLoading && user) loadPlans(); }, [authLoading, user, loadPlans]);

  const handleDelete = (id: number) => {
    setDeleteConfirmId(id);
  };

  const confirmDelete = async () => {
    if (deleteConfirmId === null) return;
    try {
      await travelApi.delete(deleteConfirmId);
      setPlans((prev) => prev.filter((p) => p.id !== deleteConfirmId));
      toast("已删除", "success");
    } catch { toast("删除失败", "error"); }
    setDeleteConfirmId(null);
  };

  if (authLoading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="min-h-screen flex items-center justify-center"
      >
        <div className="animate-spin w-8 h-8 border-2 border-fuchsia-600 border-t-transparent rounded-full" />
      </motion.div>
    );
  }

  if (!user) {
    router.push("/");
    return null;
  }

  const totalDestinations = new Set(plans.map((p) => p.destination)).size;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="min-h-screen bg-background"
    >
      <div className="bg-card border-b border-border">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push(chatHref())}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
          >
            <ArrowLeft className="w-4 h-4" />
            返回对话
          </button>
          <h1 className="text-lg font-bold text-foreground">我的行程</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Card key={i}>
                <CardContent className="pt-4 space-y-2">
                  <Skeleton className="h-5 w-1/3" />
                  <Skeleton className="h-4 w-1/4" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : plans.length === 0 ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center py-16"
          >
            <Map className="w-12 h-12 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground text-sm mb-1">暂无行程</p>
            <p className="text-muted-foreground/50 text-xs">去 AI 对话让智能助手帮你规划吧！</p>
            <Button
              onClick={() => router.push(chatHref())}
              className="mt-4"
            >
              去 AI 对话
            </Button>
          </motion.div>
        ) : (
          <>
            {/* Stats */}
            <div className="flex items-center gap-4 mb-4 text-sm text-muted-foreground">
              <span>共 {plans.length} 个行程</span>
              <span>{totalDestinations} 个目的地</span>
            </div>

            {/* Plan cards */}
            <div className="space-y-3">
              {plans.map((plan) => (
                <motion.div
                  key={plan.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <Card
                    className="hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => router.push(withSession(`/travel/${plan.id}`))}
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <CardTitle className="truncate">{plan.destination}</CardTitle>
                            <Badge
                              variant={STATUS_BADGE_VARIANT[plan.status] || "outline"}
                              className={
                                plan.status === "confirmed"
                                  ? "bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900 dark:text-fuchsia-300"
                                  : plan.status === "completed"
                                  ? "bg-fuchsia-50 text-fuchsia-600 dark:bg-fuchsia-950/50 dark:text-fuchsia-400"
                                  : ""
                              }
                            >
                              {STATUS_LABELS[plan.status] || plan.status}
                            </Badge>
                          </div>
                          <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                            <span>{plan.days} 天</span>
                            <span>{new Date(plan.created_at).toLocaleDateString("zh-CN")}</span>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={(e) => { e.stopPropagation(); handleDelete(plan.id); }}
                          className="text-destructive hover:text-destructive ml-4 flex-shrink-0"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </CardHeader>
                  </Card>
                </motion.div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmId !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteConfirmId(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定删除此行程？此操作不可撤销。
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2 justify-end mt-2">
            <Button variant="outline" onClick={() => setDeleteConfirmId(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              删除
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  );
}
