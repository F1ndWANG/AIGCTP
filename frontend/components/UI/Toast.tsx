"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from "lucide-react";

type ToastVariant = "success" | "error" | "info" | "warning";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  action?: ToastAction;
}

interface ToastContextType {
  toast: (message: string, variant?: ToastVariant, action?: ToastAction) => void;
}

const ToastContext = createContext<ToastContextType>({ toast: () => {} });

export const useToast = () => useContext(ToastContext);

let nextId = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (message: string, variant: ToastVariant = "info", action?: ToastAction) => {
      const id = nextId++;
      setToasts((prev) => [...prev, { id, message, variant, action }]);
      setTimeout(() => removeToast(id), 4000);
    },
    [removeToast]
  );

  const variantIcons: Record<ToastVariant, React.ReactNode> = {
    success: <CheckCircle className="h-4 w-4 shrink-0" />,
    error: <AlertCircle className="h-4 w-4 shrink-0" />,
    info: <Info className="h-4 w-4 shrink-0" />,
    warning: <AlertTriangle className="h-4 w-4 shrink-0" />,
  };

  const variantStyles: Record<ToastVariant, string> = {
    success: "bg-green-600 text-white",
    error: "bg-red-600 text-white",
    info: "bg-primary text-primary-foreground",
    warning: "bg-yellow-500 text-white",
  };

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      <div className="fixed z-50 flex flex-col gap-2 pointer-events-none
                      top-4 inset-x-2 sm:inset-x-auto sm:right-4 sm:left-auto
                      items-stretch sm:items-end"
        role="alert" aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto px-4 py-3 rounded-xl shadow-lg text-sm font-medium animate-slide-in flex items-center gap-3 ${variantStyles[t.variant]}`}
          >
            {variantIcons[t.variant]}
            <span className="flex-1">{t.message}</span>
            {t.action && (
              <button
                onClick={() => { t.action!.onClick(); removeToast(t.id); }}
                className="font-bold text-xs underline whitespace-nowrap hover:opacity-80"
              >
                {t.action.label}
              </button>
            )}
            <button
              onClick={() => removeToast(t.id)}
              className="opacity-60 hover:opacity-100 ml-1"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
      <style jsx global>{`
        @keyframes slide-in {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        .animate-slide-in {
          animation: slide-in 0.3s ease-out;
        }
      `}</style>
    </ToastContext.Provider>
  );
}
