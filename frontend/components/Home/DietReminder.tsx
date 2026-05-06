"use client";

import { useEffect, useRef } from "react";
import { useAuth } from "@/components/Layout/AuthProvider";
import { useNotifications } from "@/components/UI/NotificationCenter";
import { diet } from "@/lib/api";

export default function DietReminder() {
  const { user } = useAuth();
  const { addNotification, notifications } = useNotifications();
  const checkedRef = useRef(false);

  useEffect(() => {
    if (!user || checkedRef.current) return;
    checkedRef.current = true;

    // Check for active diet plans and add a morning reminder
    const hasExistingReminder = notifications.some(
      (n) => n.type === "reminder" && n.title.includes("饮食")
    );
    if (hasExistingReminder) return;

    diet.getPlans().then((plans) => {
      const active = plans.find((p) => p.status === "active");
      if (active) {
        addNotification({
          type: "reminder",
          title: "饮食计划提醒",
          message: `你有一个进行中的饮食计划「${active.title}」，记得按时用餐哦`,
          action: { label: "查看计划", href: "/diet" },
        });
      }

      const draft = plans.find((p) => p.status === "draft");
      if (draft) {
        addNotification({
          type: "reminder",
          title: "待确认的饮食计划",
          message: `「${draft.title}」还未确认，去看看 AI 为你定制的方案吧`,
          action: { label: "查看计划", href: "/diet" },
        });
      }
    }).catch(() => {});
  }, [user, addNotification, notifications]);

  return null;
}
