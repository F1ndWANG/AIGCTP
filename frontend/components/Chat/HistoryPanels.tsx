"use client";

import { useRouter } from "next/navigation";
import type { TravelPlanListItem, ChatSession } from "@/lib/types";

interface HistoryPanelsProps {
  showHistory: boolean;
  history: TravelPlanListItem[];
  showChatHistory: boolean;
  chatSessions: ChatSession[];
  sessionId?: string;
  onViewTravelPlan: (planId: number) => void;
  onRestoreSession: (sessionId: string) => void;
  onDeleteSession: (sessionId: string) => void;
}

export default function HistoryPanels({
  showHistory,
  history,
  showChatHistory,
  chatSessions,
  sessionId,
  onViewTravelPlan,
  onRestoreSession,
  onDeleteSession,
}: HistoryPanelsProps) {
  return (
    <>
      {showHistory && (
        <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 max-h-60 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-4">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
              历史行程 ({history.length})
            </h3>
            {history.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">暂无历史行程</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {history.map((plan) => (
                  <button
                    key={plan.id}
                    onClick={() => onViewTravelPlan(plan.id)}
                    className="text-left p-3 border rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition"
                  >
                    <p className="font-medium text-sm">{plan.destination}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      {plan.days}天 · {plan.status}
                    </p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {showChatHistory && (
        <div className="bg-white dark:bg-slate-800 border-b dark:border-slate-700 max-h-60 overflow-y-auto">
          <div className="max-w-4xl mx-auto p-4">
            <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
              历史对话 ({chatSessions.length})
            </h3>
            {chatSessions.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">暂无历史对话</p>
            ) : (
              <div className="space-y-1">
                {chatSessions.map((session) => (
                  <div
                    key={session.session_id}
                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 group"
                  >
                    <button
                      onClick={() => onRestoreSession(session.session_id)}
                      className="flex-1 text-left min-w-0"
                    >
                      <p className="text-sm font-medium truncate">
                        {session.title || "未命名对话"}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 truncate">
                        {session.last_preview}
                      </p>
                      <p className="text-xs text-gray-300">
                        {new Date(session.updated_at).toLocaleDateString("zh-CN")}
                        · {session.message_count} 条消息
                      </p>
                    </button>
                    <button
                      onClick={() => onDeleteSession(session.session_id)}
                      className="text-xs text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition flex-shrink-0"
                    >
                      删除
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
