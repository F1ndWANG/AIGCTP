"use client";

import { useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import clsx from "clsx";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ThumbsUp, ThumbsDown, Clipboard, Sparkles, SendHorizonal } from "lucide-react";

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
  failedMessages?: Set<string>;
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
      <div className="flex-1 flex items-center justify-center text-muted-foreground px-4">
        <div className="text-center space-y-4 max-w-md">
          <motion.div
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ type: "spring", bounce: 0.4, duration: 0.8 }}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-fuchsia-100 to-pink-100 dark:from-fuchsia-900/30 dark:to-pink-900/30 mx-auto mb-2"
          >
            <Sparkles className="w-8 h-8 text-fuchsia-500" />
          </motion.div>
          <p className="text-lg font-medium text-foreground">你好！我是你的 AI 生活助手</p>
          <p className="text-sm text-muted-foreground">我可以帮你规划旅行、推荐美食、挑选商品和提供生活建议。</p>
          <div className="pt-4 space-y-2">
            <p className="text-xs text-muted-foreground/60">可以试试这样问我：</p>
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
                  className="px-3 py-1.5 bg-muted rounded-full text-xs text-muted-foreground"
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
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            className="px-4 py-2"
          >
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
                    ? "bg-primary text-primary-foreground rounded-br-md whitespace-pre-wrap"
                    : "bg-card text-card-foreground rounded-bl-md shadow-sm border border-border markdown-body"
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
                {failedMessages?.has(msgId) ? (
                  <button
                    onClick={() => onRetry?.(msg.content)}
                    className="text-xs px-2 py-1 bg-destructive/10 text-destructive rounded-md hover:bg-destructive/20 transition"
                    title="重试"
                  >
                    <SendHorizonal className="inline h-3 w-3 mr-1" />
                    发送失败，点击重试
                  </button>
                ) : (
                  <>
                    {msg.content && (
                      <>
                        <button
                          onClick={() => handleFeedback(msg, "like")}
                          className={clsx(
                            "text-xs transition p-1 rounded hover:bg-muted",
                            fb === "like" ? "text-primary" : "text-muted-foreground/40 hover:text-muted-foreground"
                          )}
                          title="有用"
                        >
                          <ThumbsUp className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleFeedback(msg, "dislike")}
                          className={clsx(
                            "text-xs transition p-1 rounded hover:bg-muted",
                            fb === "dislike" ? "text-destructive" : "text-muted-foreground/40 hover:text-muted-foreground"
                          )}
                          title="没用"
                        >
                          <ThumbsDown className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => handleCopy(msg.content)}
                          className="text-xs text-muted-foreground/40 hover:text-muted-foreground transition p-1 rounded hover:bg-muted"
                          title="复制"
                        >
                          <Clipboard className="h-3.5 w-3.5" />
                        </button>
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </motion.div>
        );
      }}
      components={{
        Footer: () =>
          loading ? (
            <div className="px-4 py-2">
              <div className="flex justify-start message-enter">
                <div className="bg-card rounded-2xl rounded-bl-md px-4 py-3 shadow-sm border border-border">
                  <div className="flex items-center gap-3">
                    <div className="flex gap-1.5">
                      <motion.span
                        className="w-2 h-2 bg-primary/60 rounded-full"
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
                      />
                      <motion.span
                        className="w-2 h-2 bg-primary/60 rounded-full"
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
                      />
                      <motion.span
                        className="w-2 h-2 bg-primary/60 rounded-full"
                        animate={{ y: [0, -6, 0] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
                      />
                    </div>
                    {thinkingText && (
                      <span className="text-xs text-muted-foreground animate-pulse">{thinkingText}</span>
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
