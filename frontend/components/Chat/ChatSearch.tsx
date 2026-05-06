"use client";

import { useState, useMemo } from "react";
import type { Message } from "@/lib/types";

interface ChatSearchProps {
  messages: Message[];
  onJumpTo?: (index: number) => void;
}

export default function ChatSearch({ messages, onJumpTo }: ChatSearchProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    const results: { index: number; snippet: string }[] = [];
    messages.forEach((msg, i) => {
      const content = msg.content.toLowerCase();
      if (content.includes(q)) {
        const idx = content.indexOf(q);
        const start = Math.max(0, idx - 15);
        const end = Math.min(content.length, idx + q.length + 15);
        let snippet = content.slice(start, end);
        if (start > 0) snippet = "..." + snippet;
        if (end < content.length) snippet = snippet + "...";
        results.push({ index: i, snippet });
      }
    });
    return results.slice(0, 20);
  }, [messages, query]);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-slate-600 transition"
        title="搜索对话"
      >
        搜索
      </button>
    );
  }

  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索对话内容..."
          className="w-36 px-2 py-1 text-xs border rounded-lg focus:outline-none focus:border-blue-400"
          autoFocus
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
        />
        <button
          onClick={() => { setOpen(false); setQuery(""); }}
          className="text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 px-1"
        >
          ✕
        </button>
      </div>
      {query && (
        <div className="absolute top-full left-0 mt-1 w-72 bg-white dark:bg-slate-800 border dark:border-slate-700 rounded-lg shadow-lg max-h-48 overflow-y-auto z-50">
          {matches.length === 0 ? (
            <p className="text-xs text-gray-400 dark:text-gray-500 p-3">未找到匹配消息</p>
          ) : (
            matches.map((m) => (
              <button
                key={m.index}
                onClick={() => { onJumpTo?.(m.index); setOpen(false); setQuery(""); }}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 dark:hover:bg-slate-700 border-b dark:border-slate-700 last:border-b-0"
              >
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-0.5">
                  {m.index + 1}. {messages[m.index].role === "user" ? "你" : "AI"}
                </p>
                <p className="text-xs text-gray-700 dark:text-gray-300 truncate">{m.snippet}</p>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
