"use client";

import Link from "next/link";
import { remainingLabel } from "@/lib/utils";
import { useRunningTimer } from "@/hooks/useRunningTimer";

export function MiniTimer() {
  const { data, remaining } = useRunningTimer();
  if (!data?.running) return null;
  const overtime = remaining <= 0;
  return (
    <Link
      href="/employee/tasks"
      className="flex items-center gap-3 rounded-full bg-white px-3 py-1 text-sm text-ink shadow-card"
    >
      <span className="h-2 w-2 animate-pulse rounded-full bg-copper" />
      <span className="max-w-[160px] truncate">{data.task_title}</span>
      <span className={overtime ? "font-semibold text-red-700" : "font-semibold text-forest"}>
        {remainingLabel(remaining)}
      </span>
    </Link>
  );
}
