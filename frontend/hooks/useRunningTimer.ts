"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RunningTimer } from "@/lib/types";

export function useRunningTimer(enabled = true) {
  const qc = useQueryClient();

  // Fetched ONCE on load or when explicitly invalidated by Start/Stop actions
  // NO background polling, NO interval refetching
  const query = useQuery({
    queryKey: ["timer"],
    queryFn: () => api<RunningTimer>("/me/timer"),
    enabled,
    staleTime: Infinity, // Stay cached; only update when user interacts
  });

  const [remaining, setRemaining] = useState(0);
  const autoPaused = useRef(false);

  useEffect(() => {
    if (!enabled || !query.data?.running) {
      setRemaining(0);
      autoPaused.current = false;
      return;
    }

    const taskId = query.data.task_id;
    const cap = query.data.estimated_seconds > 0;
    const fetchedAt = Date.now();
    const base = query.data.remaining_seconds;
    setRemaining(base);

    // Ticks down purely in browser memory — ZERO network requests
    const id = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - fetchedAt) / 1000);
      const next = base - elapsed;
      setRemaining(next);

      if (cap && next <= 0 && taskId && !autoPaused.current) {
        autoPaused.current = true;
        void api(`/me/tasks/${taskId}/timer/pause`, { method: "POST", body: "{}" }).then(() => {
          void qc.invalidateQueries({ queryKey: ["timer"] });
          void qc.invalidateQueries({ queryKey: ["my-tasks"] });
          void qc.invalidateQueries({ queryKey: ["timesheet"] });
        });
      }
    }, 1000);

    return () => window.clearInterval(id);
  }, [query.data, qc, enabled]);

  return { ...query, remaining };
}