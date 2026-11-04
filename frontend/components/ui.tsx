"use client";

import { cn } from "@/lib/utils";
import { useEffect, useRef, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type TextareaHTMLAttributes } from "react";
import { createPortal } from "react-dom";

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" | "outline" }) {
  const styles = {
    primary: "bg-forest text-white hover:bg-[#004e8a] shadow-sm",
    ghost: "bg-transparent text-ink hover:bg-mist",
    danger: "bg-red-700 text-white hover:bg-red-800",
    outline: "border border-ink/15 bg-white text-ink hover:bg-mist",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none",
        styles[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-xl border border-ink/15 bg-white px-3.5 py-2 text-sm text-ink outline-none transition focus:border-forest focus:ring-2 focus:ring-forest/20 disabled:bg-mist/50 disabled:text-ink/40",
        className,
      )}
      {...props}
    />
  );
}

export function Select({ className, children, ...props }: InputHTMLAttributes<HTMLSelectElement> & { children: ReactNode }) {
  return (
    <select
      className={cn(
        "w-full rounded-xl border border-ink/15 bg-white px-3.5 py-2 text-sm text-ink outline-none transition focus:border-forest focus:ring-2 focus:ring-forest/20 disabled:bg-mist/50 disabled:text-ink/40",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "w-full rounded-xl border border-ink/15 bg-white px-3.5 py-2 text-sm text-ink outline-none transition focus:border-forest focus:ring-2 focus:ring-forest/20 disabled:bg-mist/50 disabled:text-ink/40",
        className,
      )}
      {...props}
    />
  );
}

export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <label className={cn("mb-1.5 block text-xs font-semibold uppercase tracking-wider text-ink/70", className)}>
      {children}
    </label>
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-3xl bg-white p-6 shadow-card border border-ink/5", className)}>{children}</div>;
}

export function Badge({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "good" | "warn" | "bad" }) {
  const tones = {
    default: "bg-mist text-ink/80 border border-ink/10",
    good: "bg-emerald-50 text-emerald-700 border border-emerald-200",
    warn: "bg-amber-50 text-amber-700 border border-amber-200",
    bad: "bg-red-50 text-red-700 border border-red-200",
  };
  return <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold", tones[tone])}>{children}</span>;
}

export function IconButton({
  label,
  onClick,
  className,
  variant = "edit",
}: {
  label: string;
  onClick: () => void;
  className?: string;
  variant?: "edit" | "view";
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 w-8 items-center justify-center rounded-lg border border-ink/10 text-ink/60 transition hover:bg-mist hover:text-forest hover:border-forest/30",
        className,
      )}
    >
      {variant === "view" ? (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z" />
        </svg>
      )}
    </button>
  );
}

export function DetailGrid({ rows }: { rows: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid gap-3 sm:grid-cols-2">
      {rows.map((row) => (
        <div key={row.label} className="rounded-xl bg-mist/40 p-3 border border-ink/5">
          <dt className="text-xs font-semibold uppercase tracking-wide text-ink/50">{row.label}</dt>
          <dd className="mt-1 text-sm font-medium text-ink">{row.value || "—"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs font-medium text-red-600">{message}</p>;
}

export function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 p-12 text-ink/40">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-ink/10 border-t-forest" />
      <span className="text-xs font-semibold uppercase tracking-widest">{text}</span>
    </div>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const [mounted, setMounted] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  // Lock background scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  if (!open || !mounted) return null;

  const modalContent = (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[9999] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-black/60 p-4 sm:p-6 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={contentRef}
        className="relative my-auto flex max-h-[88vh] w-full max-w-2xl flex-col rounded-3xl bg-paper shadow-2xl border border-ink/10 animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Sticky Header */}
        <div className="flex shrink-0 items-center justify-between border-b border-ink/10 px-6 py-4">
          <h2 className="font-display text-2xl text-ink tracking-tight">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-ink/50 transition hover:bg-mist hover:text-ink active:scale-95"
            aria-label="Close dialog"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
