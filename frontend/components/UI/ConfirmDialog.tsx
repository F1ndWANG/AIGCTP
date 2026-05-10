"use client";

import { useEffect, useRef } from "react";
import { AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/UI/dialog";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmText = "确认",
  cancelText = "取消",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={(open) => { if (!open) onCancel(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <div className="flex items-center gap-3 mb-2">
            {variant === "danger" && (
              <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
                <AlertTriangle className="h-5 w-5 text-destructive" />
              </div>
            )}
            <DialogTitle>{title}</DialogTitle>
          </div>
          <DialogDescription>{message}</DialogDescription>
        </DialogHeader>
        <div className="flex gap-3 justify-end mt-4">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm rounded-lg border border-border bg-background hover:bg-muted transition-colors"
          >
            {cancelText}
          </button>
          <button
            ref={confirmRef}
            onClick={onConfirm}
            className={`px-4 py-2 text-sm text-white rounded-lg transition-colors ${
              variant === "danger"
                ? "bg-destructive hover:bg-destructive/90"
                : "bg-primary hover:bg-primary/90"
            }`}
          >
            {confirmText}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
