"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { useRunningTimer } from "@/hooks/useRunningTimer";
import { Badge, Button, Card, Modal, Textarea } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { Task } from "@/lib/types";
import { labels, remainingLabel } from "@/lib/utils";

const groups = ["in_progress", "paused", "not_started", "completed"] as const;

export default function MyTasksPage() {
  const qc = useQueryClient();
  const { remaining, data: timer } = useRunningTimer();
  const [stopId, setStopId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [prompt, setPrompt] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const { data } = useQuery({ queryKey: ["my-tasks"], queryFn: () => api<Task[]>("/me/tasks") });

  const act = useMutation({
    mutationFn: async ({ id, action, pauseCurrent }: { id: string; action: string; pauseCurrent?: boolean }) => {
      const body = action === "stop" ? { note } : { pause_current: Boolean(pauseCurrent) };
      return api(`/me/tasks/${id}/timer/${action}`, { method: "POST", body: JSON.stringify(body) });
    },
    onSuccess: (_result, vars) => {
      void qc.invalidateQueries({ queryKey: ["timer"] });
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      void qc.invalidateQueries({ queryKey: ["timesheet"] });
      setStopId(null);
      setPrompt(null);
      setNote("");
      if (vars.action === "stop" || vars.action === "pause") setSaved(true);
    },
    onError: (err, vars) => {
      if (err instanceof ApiError && err.status === 409) {
        setPrompt(vars.id);
      }
    },
  });

  return (
    <div className="space-y-6">
      <p className="text-sm text-ink/60">
        Start while you work. The timer pauses automatically when you reach the task estimate (e.g. 8h). Pause or Stop
        to post hours on this week’s timesheet. You can also type hours on{" "}
        <Link href="/employee/timesheet" className="font-semibold text-forest hover:underline">
          Timesheet
        </Link>
        .
      </p>
      {saved ? (
        <Card className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm">Hours saved on this week’s timesheet.</p>
          <Link href="/employee/timesheet">
            <Button>Open timesheet</Button>
          </Link>
        </Card>
      ) : null}
      {!data?.length ? (
        <Card>
          <h3 className="font-display text-2xl">No tasks yet</h3>
          <p className="mt-2 text-sm text-ink/60">Add a task from a project so you can start a timer or fill the timesheet.</p>
          <Link href="/employee/projects" className="mt-4 inline-block">
            <Button>Add task from Projects</Button>
          </Link>
        </Card>
      ) : null}
      {groups.map((status) => {
        const items = data?.filter((t) => t.status === status) ?? [];
        if (!items.length) return null;
        return (
          <section key={status}>
            <h3 className="mb-3 font-display text-2xl">{labels.taskStatus[status]}</h3>
            <div className="grid gap-4 md:grid-cols-2">
              {items.map((task) => {
                const running = timer?.running && timer.task_id === task.id;
                const remain = running ? remaining : task.remaining_seconds;
                return (
                  <Card key={task.id}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase text-copper">{task.project_name}</p>
                        <h4 className="font-display text-2xl">{task.title}</h4>
                      </div>
                      <Badge>{labels.priority[task.priority]}</Badge>
                    </div>
                    <p className={`mt-4 font-display text-3xl ${remain <= 0 ? "text-red-700" : "text-forest"}`}>
                      {remainingLabel(remain)}
                    </p>
                    <p className="mt-1 text-xs text-ink/50">Time left vs {task.estimated_hours}h estimate</p>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {!running && task.status !== "completed" && (
                        <Button onClick={() => act.mutate({ id: task.id, action: task.status === "paused" ? "resume" : "start" })}>
                          {task.status === "paused" ? "Resume" : "Start"}
                        </Button>
                      )}
                      {running && (
                        <>
                          <Button variant="outline" onClick={() => act.mutate({ id: task.id, action: "pause" })}>
                            Pause
                          </Button>
                          <Button variant="danger" onClick={() => setStopId(task.id)}>
                            Stop
                          </Button>
                        </>
                      )}
                    </div>
                  </Card>
                );
              })}
            </div>
          </section>
        );
      })}

      <Modal open={!!stopId} title="Stop timer" onClose={() => setStopId(null)}>
        <Textarea placeholder="Optional note" value={note} onChange={(e) => setNote(e.target.value)} />
        <p className="mt-2 text-xs text-ink/50">Stopped time is added to this week’s timesheet.</p>
        <Button className="mt-4" loading={act.isPending} onClick={() => stopId && act.mutate({ id: stopId, action: "stop" })}>
          {act.isPending ? "Saving..." : "Save hours"}
        </Button>
      </Modal>

      <Modal open={!!prompt} title="Another timer is running" onClose={() => setPrompt(null)}>
        <p className="text-sm text-ink/70">Pause the current timer and start this task?</p>
        <Button className="mt-4" loading={act.isPending} onClick={() => prompt && act.mutate({ id: prompt, action: "start", pauseCurrent: true })}>
          {act.isPending ? "Starting..." : "Pause current and start"}
        </Button>
      </Modal>
    </div>
  );
}
