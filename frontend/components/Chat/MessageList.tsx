"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";

import type { Message } from "@/lib/types";
import { feedback as feedbackApi } from "@/lib/api";

export default function MessageList({
  messages,
  loading,
  thinkingText = "",
}: {
  messages: Message[];
  loading: boolean;
  thinkingText?: string;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, "like" | "dislike">>({});

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleFeedback = async (msg: Message, type: "like" | "dislike") => {
    const msgId = msg.id || `msg-${Date.now()}`;
    if (feedbackState[msgId] === type) return;

    try {
      await feedbackApi.submit({
        content_type: "general",
        message_id: msgId,
        feedback: type,
        content_snapshot: { content: msg.content.slice(0, 200) },
      });
      setFeedbackState((prev) => ({ ...prev, [msgId]: type }));
    } catch {
      // silently fail
    }
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <div className="text-center space-y-3">
          <div className="text-5xl">🌍</div>
          <p className="text-lg">你好！我是你的 AI 生活助手</p>
          <p className="text-sm">我可以帮你规划旅行、推荐美食、提供生活建议</p>
          <div className="pt-4 space-y-2">
            <p className="text-xs text-gray-300">试试这样说：</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                "帮我规划一个成都3日游",
                "不想吃饭，推荐吃什么",
                "附近有什么好吃的",
                "推荐适合跑步的鞋子",
                "帮我买两瓶酱油",
                "分析我这周的饮食营养",
                "北京5天攻略",
                "推荐一些好用的数码产品",
              ].map((hint) => (
                <span
                  key={hint}
                  className="px-3 py-1.5 bg-gray-100 rounded-full text-xs text-gray-500"
                >
                  {hint}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.map((msg, i) => {
        const msgId = msg.id || `msg-${i}`;
        const fb = feedbackState[msgId];

        return (
          <div key={i}>
            <div
              className={clsx(
                "flex message-enter",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={clsx(
                  "max-w-[80%] rounded-2xl px-4 py-3 whitespace-pre-wrap",
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-md"
                    : "bg-white text-gray-800 rounded-bl-md shadow-sm border"
                )}
              >
                {msg.content}
              </div>
            </div>
            {msg.role === "assistant" && msg.content && (
              <div className="flex justify-start pl-2 mt-1 gap-2">
                <button
                  onClick={() => handleFeedback(msg, "like")}
                  className={clsx(
                    "text-xs transition",
                    fb === "like" ? "text-blue-600" : "text-gray-300 hover:text-gray-500"
                  )}
                  title="有用"
                >
                  👍
                </button>
                <button
                  onClick={() => handleFeedback(msg, "dislike")}
                  className={clsx(
                    "text-xs transition",
                    fb === "dislike" ? "text-red-500" : "text-gray-300 hover:text-gray-500"
                  )}
                  title="没用"
                >
                  👎
                </button>
              </div>
            )}
          </div>
        );
      })}
      {loading && (
        <div className="flex justify-start message-enter">
          <div className="bg-white rounded-2xl rounded-bl-md px-4 py-3 shadow-sm border">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
              {thinkingText && (
                <span className="text-xs text-gray-400 animate-pulse">{thinkingText}</span>
              )}
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
