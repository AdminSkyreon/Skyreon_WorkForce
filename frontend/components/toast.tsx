"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

let toastListeners: Array<(toast: ToastMessage) => void> = [];

// Deduplication cache: stores the last timestamp an identical message was displayed
const recentToastCache = new Map<string, number>();
const DEDUPE_WINDOW_MS = 3_000;

export function showToast(type: ToastType, title: string, description?: string) {
  const key = `${type}:${title}:${description || ""}`;
  const now = Date.now();
  const lastShown = recentToastCache.get(key) || 0;

  // Suppress duplicate toasts fired within the deduplication window
  if (now - lastShown < DEDUPE_WINDOW_MS) {
    return;
  }
  recentToastCache.set(key, now);

  const id = Math.random().toString(36).substring(2, 9);
  const toast: ToastMessage = { id, type, title, description };
  toastListeners.forEach((fn) => fn(toast));
}

export const toast = {
  success: (title: string, description?: string) => showToast("success", title, description),
  error: (title: string, description?: string) => showToast("error", title, description),
  info: (title: string, description?: string) => showToast("info", title, description),
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const handler = (newToast: ToastMessage) => {
      setToasts((prev) => [...prev, newToast]);
      // Auto-dismiss after 4.5 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== newToast.id));
      }, 4500);
    };

    toastListeners.push(handler);
    return () => {
      toastListeners = toastListeners.filter((fn) => fn !== handler);
    };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-5 right-5 z-[100000] flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => {
        const isSuccess = t.type === "success";
        const isError = t.type === "error";

        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl shadow-2xl border backdrop-blur-md transition-all animate-in slide-in-from-bottom-5 duration-200 ${
              isSuccess
                ? "bg-white/95 border-emerald-500/20 text-ink shadow-emerald-500/10"
                : isError
                ? "bg-white/95 border-rose-500/20 text-ink shadow-rose-500/10"
                : "bg-white/95 border-sky-500/20 text-ink shadow-sky-500/10"
            }`}
          >
            <div className="mt-0.5 shrink-0">
              {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-600" />}
              {isError && <AlertCircle className="w-5 h-5 text-rose-600" />}
              {!isSuccess && !isError && <Info className="w-5 h-5 text-sky-600" />}
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold tracking-tight text-ink">{t.title}</h4>
              {t.description && <p className="text-xs text-muted mt-0.5 leading-relaxed">{t.description}</p>}
            </div>
            <button
              onClick={() => setToasts((prev) => prev.filter((item) => item.id !== t.id))}
              className="text-muted/60 hover:text-ink transition-colors p-0.5 -mr-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}