"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Project, Task } from "@/lib/types";
import { labels } from "@/lib/utils";

export default function EmployeeProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [hours, setHours] = useState("8");
  const [priority, setPriority] = useState("medium");

  const project = useQuery({
    queryKey: ["my-project", params.id],
    queryFn: () => api<Project>(`/me/projects/${params.id}`),
  });
  const tasks = useQuery({
    queryKey: ["my-project-tasks", params.id],
    queryFn: () => api<Task[]>(`/me/projects/${params.id}/tasks`),
  });
  const create = useMutation({
    mutationFn: () =>
      api(`/me/projects/${params.id}/tasks`, {
        method: "POST",
        body: JSON.stringify({ title, estimated_hours: hours, priority }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["my-project-tasks", params.id] });
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      setOpen(false);
      setTitle("");
    },
  });

  const p = project.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href="/employee/projects" className="text-sm text-forest hover:underline">
            All projects
          </Link>
          <p className="mt-2 text-xs uppercase tracking-widest text-copper">{p?.project_code}</p>
          <h2 className="font-display text-4xl">{p?.name ?? "Project"}</h2>
          <p className="text-ink/60">{p?.client_name}</p>
        </div>
        <Button onClick={() => setOpen(true)}>Add task</Button>
      </div>
      <p className="text-sm text-ink/60">
        Add a task assigned to you, then start the timer on My Tasks or type hours on Timesheet.
      </p>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase text-ink/60">
            <tr>
              <th className="px-4 py-3">Task</th>
              <th className="px-4 py-3">Assignee</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Estimate</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {tasks.data?.length ? (
              tasks.data.map((task) => (
                <tr key={task.id} className="border-t border-ink/5">
                  <td className="px-4 py-3 font-semibold">{task.title}</td>
                  <td className="px-4 py-3">{task.assignee_name || "Unassigned"}</td>
                  <td className="px-4 py-3">{labels.taskStatus[task.status]}</td>
                  <td className="px-4 py-3">{task.estimated_hours}h</td>
                  <td className="px-4 py-3 text-right">
                    <Link href="/employee/tasks" className="text-sm font-semibold text-forest hover:underline">
                      Track time
                    </Link>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td className="px-4 py-8 text-center text-ink/50" colSpan={5}>
                  No tasks yet. Add one so you can track time this week.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Modal open={open} title="Add task" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div>
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="What will you work on?" />
          </div>
          <div>
            <Label>Estimated hours</Label>
            <Input value={hours} onChange={(e) => setHours(e.target.value)} />
          </div>
          <div>
            <Label>Priority</Label>
            <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
              {Object.entries(labels.priority).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
          <p className="text-xs text-ink/50">This task is assigned to you.</p>
          {create.error ? <p className="text-sm text-red-700">{create.error.message}</p> : null}
          <Button disabled={!title.trim() || create.isPending} onClick={() => create.mutate()}>
            Create task
          </Button>
        </div>
      </Modal>
    </div>
  );
}
