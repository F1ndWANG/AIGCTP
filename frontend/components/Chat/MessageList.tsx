"use client";

import { useRef, useState, useCallback } from "react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { feedback as feedbackApi } from "@/lib/api";
import type { Message } from "@/lib/types";

export default function MessageList({
  messages,
  loading,
  thinkingText = "",
  onRetry,
  failedMessages,
}: {
  messages: Message[];
  loading: boolean;
  thinkingText?: string;
  onRetry?: (message: string) => void;
  failedMessages?: Set<number>;
}) {
  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const [feedbackState, setFeedbackState] = useState<Record<string, "like" | "dislike">>({});

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
      // Ignore feedback failures in chat UI.
    }
  };

  const handleCopy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // fallback
    }
  }, []);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
        <div className="text-center space-y-3">
          <div className="text-5xl">🍀</div>
          <p className="text-lg">你好！我是你的 AI 生活助手</p>
          <p className="text-sm">我可以帮你规划旅行、推荐美食、挑选商品和提供生活建议。</p>
          <div className="pt-4 space-y-2">
            <p className="text-xs text-gray-300">可以试试这样问我：</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {[
                "帮我规划一个成都一日游",
                "不想吃饭，推荐点清淡的",
                "附近有什么好吃的",
                "推荐适合跑步的鞋子",
                "帮我买两瓶酱油",
                "分析我这周的饮食营养",
                "北京 5 天攻略",
                "推荐一些好用的数码产品",
              ].map((hint) => (
                <span
                  key={hint}
                  className="px-3 py-1.5 bg-gray-100 dark:bg-slate-700 rounded-full text-xs text-gray-500 dark:text-gray-400"
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
    <Virtuoso
      ref={virtuosoRef}
      className="flex-1 overflow-x-hidden"
      data={messages}
      followOutput="smooth"
      alignToBottom
      itemContent={(index, msg) => {
        const msgId = msg.id || `msg-${index}`;
        const fb = feedbackState[msgId];

        return (
          <div className="px-4 py-2">
            <div
              className={clsx(
                "flex message-enter",
                msg.role === "user" ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={clsx(
                  "max-w-[80%] rounded-2xl px-4 py-3",
                  msg.role === "user"
                    ? "bg-blue-600 text-white rounded-br-md whitespace-pre-wrap"
                    : "bg-white dark:bg-slate-800 text-gray-800 dark:text-gray-200 rounded-bl-md shadow-sm border dark:border-slate-700 markdown-body"
                )}
              >
                {msg.role === "assistant" ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </div>
            {msg.role === "assistant" && (
              <div className="flex justify-start pl-2 mt-1 gap-2">
                {failedMessages?.has(index) ? (
                  <button
                    onClick={() => onRetry?.(msg.content)}
                    className="text-xs px-2 py-1 bg-red-50 text-red-500 rounded-md hover:bg-red-100 transition"
                    title="重试"
                  >
                    发送失败，点击重试
                  </button>
                ) : (
                  <>
                    {msg.content && (
                      <>
                        <button
                          onClick={() => handleFeedback(msg, "like")}
                          className={clsx(
                            "text-xs transition",
                            fb === "like" ? "text-blue-600" : "text-gray-300 hover:text-gray-500 dark:hover:text-gray-400"
                          )}
                          title="有用"
                        >
                          👍
                        </button>
                        <button
                          onClick={() => handleFeedback(msg, "dislike")}
                          className={clsx(
                            "text-xs transition",
                            fb === "dislike" ? "text-red-500" : "text-gray-300 hover:text-gray-500 dark:hover:text-gray-400"
                          )}
                          title="没用"
                        >
                          👎
                        </button>
                        <button
                          onClick={() => handleCopy(msg.content)}
                          className="text-xs text-gray-300 hover:text-gray-500 dark:hover:text-gray-400 transition"
                          title="复制"
                        >
                          📋
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        );
      }}
      components={{
        Footer: () =>
          loading ? (
            <div className="px-4 py-2">
              <div className="flex justify-start message-enter">
                <div className="bg-white dark:bg-slate-800 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm border dark:border-slate-700">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                    </div>
                    {thinkingText && (
                      <span className="text-xs text-gray-400 dark:text-gray-500 animate-pulse">{thinkingText}</span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : null,
      }}
    />
  );
}
