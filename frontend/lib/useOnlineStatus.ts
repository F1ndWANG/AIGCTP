"use client";

import { useEffect } from "react";

type OnlineHandler = () => void;

let listeners: OnlineHandler[] = [];

function readOnlineStatus(): boolean {
  if (typeof window === "undefined") return true;
  return typeof window.navigator.onLine === "boolean" ? window.navigator.onLine : true;
}

let _isOnline = readOnlineStatus();

function notify() {
  listeners.forEach((fn) => fn());
}

if (typeof window !== "undefined") {
  window.addEventListener("online", () => {
    _isOnline = true;
    notify();
  });
  window.addEventListener("offline", () => {
    _isOnline = false;
    notify();
  });
}

export function isOnline(): boolean {
  _isOnline = readOnlineStatus();
  return _isOnline;
}

export function useOnlineStatus(onBecomeOnline?: () => void) {
  useEffect(() => {
    const handler = () => {
      if (_isOnline && onBecomeOnline) onBecomeOnline();
    };
    listeners.push(handler);
    return () => {
      listeners = listeners.filter((h) => h !== handler);
    };
  }, [onBecomeOnline]);
}
