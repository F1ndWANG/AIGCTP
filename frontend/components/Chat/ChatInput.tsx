"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Textarea } from "@/components/UI/textarea";
import { ShimmerButton } from "@/components/UI/shimmer-button";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = "输入你的问题...",
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border/50 bg-background/80 backdrop-blur-sm p-4">
      <div className="max-w-4xl mx-auto flex gap-3 items-end">
        <div className="flex-1 relative">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            maxLength={2000}
            disabled={disabled}
            aria-label="输入消息"
            className="min-h-[44px] max-h-[200px] pr-16 resize-none rounded-xl"
          />
          <span className="absolute bottom-2.5 right-3 text-xs text-muted-foreground pointer-events-none select-none">
            {input.length}/2000
          </span>
        </div>
        <ShimmerButton
          onClick={handleSubmit}
          disabled={disabled || !input.trim()}
          shimmerColor="#d946ef"
          background="linear-gradient(135deg, #d946ef, #ec4899)"
          borderRadius="12px"
          className="px-5 py-3 h-[44px] shrink-0"
          aria-label={disabled ? "思考中" : "发送消息"}
        >
          <Send className="h-4 w-4 mr-1.5" />
          {disabled ? "思考中" : "发送"}
        </ShimmerButton>
      </div>
    </div>
  );
}
