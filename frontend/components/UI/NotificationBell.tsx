"use client";

import { useState, useRef, useEffect } from "react";
import { useNotifications, type Notification } from "@/components/UI/NotificationCenter";

export default function NotificationBell() {
  const { notifications, unreadCount, markRead, markAllRead, clear } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 transition"
        aria-label={`通知${unreadCount > 0 ? `，${unreadCount}条未读` : ""}`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-800 rounded-xl shadow-xl border dark:border-slate-700 z-50 max-h-96 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b dark:border-slate-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">通知</h3>
            {unreadCount > 0 && (
              <button onClick={markAllRead} className="text-xs text-blue-600 hover:text-blue-500 transition">
                全部标为已读
              </button>
            )}
          </div>

          {/* List */}
          <div className="overflow-y-auto flex-1">
            {notifications.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-300 text-2xl mb-2">🔔</p>
                <p className="text-xs text-gray-400 dark:text-gray-500">暂无通知</p>
              </div>
            ) : (
              notifications.slice(0, 20).map((n) => (
                <NotificationItem key={n.id} notification={n} onMarkRead={markRead} onClear={clear} />
              ))
            )}
          </div>

          {/* Clear all */}
          {notifications.length > 0 && (
            <div className="border-t dark:border-slate-700 px-4 py-2">
              <button
                onClick={() => { markAllRead(); /* clear after a brief delay so user can see */ setTimeout(() => { /* noop */ }, 100); }}
                className="w-full text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-center py-1 transition"
              >
                清空通知
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function NotificationItem({
  notification,
  onMarkRead,
  onClear,
}: {
  notification: Notification;
  onMarkRead: (id: string) => void;
  onClear: (id: string) => void;
}) {
  const iconMap = {
    reminder: "⏰",
    order: "📦",
    system: "ℹ️",
  };

  return (
    <div
      className={`px-4 py-3 border-b dark:border-slate-700 last:border-0 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition cursor-pointer ${
        !notification.read ? "bg-blue-50/50 dark:bg-blue-900/10" : ""
      }`}
      onClick={() => {
        onMarkRead(notification.id);
        if (notification.action) {
          // Use router push for internal links
          window.location.href = notification.action.href;
        }
      }}
    >
      <div className="flex items-start gap-2">
        <span className="text-base mt-0.5">{iconMap[notification.type] || "ℹ️"}</span>
        <div className="flex-1 min-w-0">
          <p className={`text-sm ${!notification.read ? "font-semibold text-gray-900 dark:text-gray-100" : "text-gray-700 dark:text-gray-300"}`}>
            {notification.title}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">{notification.message}</p>
          <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-1">{formatTime(notification.created_at)}</p>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onClear(notification.id); }}
          className="text-gray-300 dark:text-gray-600 hover:text-gray-500 dark:hover:text-gray-400 text-xs flex-shrink-0 p-0.5"
          aria-label="删除通知"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function formatTime(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return "刚刚";
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}
