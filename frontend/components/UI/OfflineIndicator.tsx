"use client";

import { useEffect, useState } from "react";
import { isOnline, useOnlineStatus } from "@/lib/useOnlineStatus";
import { getOfflineQueueSize, dequeueAllOfflineActions } from "@/lib/offline-queue";

export default function OfflineIndicator() {
  const [offline, setOffline] = useState(!isOnline());
  const [queueSize, setQueueSize] = useState(0);

  const refreshQueueSize = async () => {
    try {
      setQueueSize(await getOfflineQueueSize());
    } catch {
      // ignore
    }
  };

  useOnlineStatus(async () => {
    setOffline(false);
    const replayed = await dequeueAllOfflineActions();
    if (replayed > 0) {
      setQueueSize(0);
      window.dispatchEvent(new CustomEvent("offline-queue-replay", { detail: replayed }));
    }
  });

  useEffect(() => {
    const onStatusChange = () => {
      setOffline(!isOnline());
      if (isOnline()) refreshQueueSize();
    };
    window.addEventListener("online", onStatusChange);
    window.addEventListener("offline", onStatusChange);
    refreshQueueSize();
    return () => {
      window.removeEventListener("online", onStatusChange);
      window.removeEventListener("offline", onStatusChange);
    };
  }, []);

  if (!offline && queueSize === 0) return null;

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-50 text-center text-sm py-1.5 font-medium ${
        offline
          ? "bg-red-500 text-white"
          : "bg-yellow-400 text-yellow-900"
      }`}
    >
      {offline
        ? "网络连接已断开"
        : `离线队列中有 ${queueSize} 个待同步操作`}
    </div>
  );
}
