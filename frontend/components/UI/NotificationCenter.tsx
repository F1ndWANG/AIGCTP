"use client";

import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from "react";

export interface Notification {
  id: string;
  type: "reminder" | "order" | "system";
  title: string;
  message: string;
  read: boolean;
  created_at: string;
  action?: { label: string; href: string };
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (n: Omit<Notification, "id" | "read" | "created_at">) => void;
  markRead: (id: string) => void;
  markAllRead: () => void;
  clear: (id: string) => void;
  clearAll: () => void;
}

const STORAGE_KEY = "app_notifications";
const MAX_NOTIFICATIONS = 50;

function loadNotifications(): Notification[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveNotifications(ns: Notification[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ns));
  } catch { /* quota exceeded — silently ignore */ }
}

const NotificationContext = createContext<NotificationContextType>({
  notifications: [],
  unreadCount: 0,
  addNotification: () => {},
  markRead: () => {},
  markAllRead: () => {},
  clear: () => {},
  clearAll: () => {},
});

export function useNotifications() {
  return useContext(NotificationContext);
}

let _idCounter = 0;
function genId() {
  _idCounter++;
  try { return `${Date.now()}-${crypto.randomUUID().slice(0, 8)}`; } catch {
    return `${Date.now()}-${_idCounter}`;
  }
}

export function NotificationProvider({ children }: { children: ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const prevUnreadRef = useRef(0);

  // Hydrate from localStorage on mount
  useEffect(() => {
    setNotifications(loadNotifications());
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  // Flash tab title when unread count changes
  useEffect(() => {
    const prev = prevUnreadRef.current;
    prevUnreadRef.current = unreadCount;
    if (unreadCount > prev && document.title) {
      const orig = document.title;
      const interval = setInterval(() => {
        document.title = unreadCount > 0
          ? `(${unreadCount}) ${orig.replace(/^\(\d+\) /, "")}`
          : orig;
      }, 1500);
      setTimeout(() => {
        clearInterval(interval);
        document.title = orig;
      }, 6000);
    }
  }, [unreadCount]);

  const persist = useCallback((ns: Notification[]) => {
    setNotifications(ns);
    saveNotifications(ns);
  }, []);

  const addNotification = useCallback(
    (n: Omit<Notification, "id" | "read" | "created_at">) => {
      setNotifications((prev) => {
        const next: Notification = {
          ...n,
          id: genId(),
          read: false,
          created_at: new Date().toISOString(),
        };
        const updated = [next, ...prev].slice(0, MAX_NOTIFICATIONS);
        saveNotifications(updated);
        return updated;
      });
    },
    []
  );

  const markRead = useCallback(
    (id: string) => {
      persist(notifications.map((n) => (n.id === id ? { ...n, read: true } : n)));
    },
    [notifications, persist]
  );

  const markAllRead = useCallback(() => {
    persist(notifications.map((n) => ({ ...n, read: true })));
  }, [notifications, persist]);

  const clear = useCallback(
    (id: string) => {
      persist(notifications.filter((n) => n.id !== id));
    },
    [notifications, persist]
  );

  const clearAll = useCallback(() => {
    persist([]);
  }, [persist]);

  return (
    <NotificationContext.Provider
      value={{ notifications, unreadCount, addNotification, markRead, markAllRead, clear, clearAll }}
    >
      {children}
    </NotificationContext.Provider>
  );
}
