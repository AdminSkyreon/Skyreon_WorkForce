"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Badge, Button, Card, IconButton, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Employee, Page, Project, Task } from "@/lib/types";
import { labels } from "@/lib/utils";

const columns = ["not_started", "in_progress", "paused", "completed"] as const;

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [view, setView] = useState<"table" | "kanban">("table");
  const [open, setOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [assignee, setAssignee] = useState("");
  const [hours, setHours] = useState("8");
  const [priority, setPriority] = useState("medium");
  const [addMember, setAddMember] = useState("");

  const project = useQuery({
    queryKey: ["project", params.id],
    queryFn: () => api<Project>(`/admin/projects/${params.id}`),
  });
  const tasks = useQuery({
    queryKey: ["project-tasks", params.id],
    queryFn: () => api<Task[]>(`/admin/projects/${params.id}/tasks`),
  });
  const employees = useQuery({
    queryKey: ["employees-all"],
    queryFn: () => api<Page<Employee>>("/admin/employees?page_size=100"),
  });

  const createTask = useMutation({
    mutationFn: () =>
      api(`/admin/projects/${params.id}/tasks`, {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          assignee_id: assignee || null,
          estimated_hours: hours,
          priority,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["project-tasks", params.id] });
      setOpen(false);
      setEditingTask(null);
      setTitle("");
      setDescription("");
    },
  });

  const updateTask = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api(`/admin/projects/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project-tasks", params.id] }),
  });

  const saveTask = useMutation({
    mutationFn: () =>
      api(`/admin/projects/tasks/${editingTask?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title,
          description,
          assignee_id: assignee || null,
          estimated_hours: hours,
          priority,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["project-tasks", params.id] });
      setOpen(false);
      setEditingTask(null);
    },
  });

  function openCreateTask() {
    setEditingTask(null);
    setTitle("");
    setDescription("");
    setAssignee("");
    setHours("8");
    setPriority("medium");
    setOpen(true);
  }

  function openEditTask(task: Task) {
    setEditingTask(task);
    setTitle(task.title);
    setDescription(task.description || "");
    setAssignee(task.assignee_id || "");
    setHours(task.estimated_hours);
    setPriority(task.priority);
    setOpen(true);
  }

  const updateMembers = useMutation({
    mutationFn: (member_ids: string[]) =>
      api(`/admin/projects/${params.id}`, { method: "PATCH", body: JSON.stringify({ member_ids }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["project", params.id] }),
  });

  const p = project.data;
  const fin = p?.financials;

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-widest text-copper">{p?.project_code}</p>
            <h2 className="font-display text-4xl">{p?.name}</h2>
            <p className="text-ink/60">{p?.client_name} · {p?.manager_name}</p>
          </div>
          <Badge>{p ? labels.projectStatus[p.status] : ""}</Badge>
        </div>
        <p className="mt-4 text-sm text-ink/60">
          1. Add team &nbsp; 2. Add tasks &nbsp; 3. Employees track time and submit the week.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-5">
          {[
            ["Hours", fin?.total_hours],
            ["Cost", fin?.cost],
            ["Revenue", fin?.revenue],
            ["Profit", fin?.profit],
            ["Budget used", fin ? `${fin.budget_consumed_percent}%` : ""],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl bg-mist p-4">
              <p className="text-xs uppercase text-ink/50">{label}</p>
              <p className="mt-2 font-display text-2xl">{value ?? "—"}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="font-display text-2xl">Team</h3>
        <p className="mt-1 text-sm text-ink/60">People on this project can add tasks and log time.</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {p?.members.map((emp) => (
            <button
              key={emp.id}
              className="rounded-full bg-forest px-3 py-1 text-sm text-white"
              onClick={() => {
                if (!p || emp.id === p.manager_id) return;
                updateMembers.mutate(p.members.filter((member) => member.id !== emp.id).map((member) => member.id));
              }}
              title={emp.id === p.manager_id ? "Manager stays on the team" : "Remove from team"}
            >
              {emp.name}
              {emp.id === p.manager_id ? " · manager" : ""}
            </button>
          ))}
          {!p?.members.length ? <p className="text-sm text-ink/50">No team members yet.</p> : null}
        </div>
        <div className="mt-4 flex max-w-md flex-wrap items-center gap-2">
          <Select value={addMember} onChange={(e) => setAddMember(e.target.value)}>
            <option value="">Add teammate</option>
            {employees.data?.items
              .filter((emp) => !p?.members.some((member) => member.id === emp.id))
              .map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
          </Select>
          <Button
            variant="outline"
            disabled={!addMember}
            onClick={() => {
              if (!p || !addMember) return;
              updateMembers.mutate([...p.members.map((member) => member.id), addMember]);
              setAddMember("");
            }}
          >
            Add
          </Button>
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button variant={view === "table" ? "primary" : "outline"} onClick={() => setView("table")}>
            Table
          </Button>
          <Button variant={view === "kanban" ? "primary" : "outline"} onClick={() => setView("kanban")}>
            Kanban
          </Button>
        </div>
        <Button onClick={openCreateTask}>Add task</Button>
      </div>

      {view === "table" ? (
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-mist text-xs uppercase text-ink/60">
              <tr>
                <th className="px-4 py-3">Task</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Priority</th>
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
                    <td className="px-4 py-3">{labels.priority[task.priority]}</td>
                    <td className="px-4 py-3">
                      <Select value={task.status} onChange={(e) => updateTask.mutate({ id: task.id, status: e.target.value })}>
                        {Object.entries(labels.taskStatus).map(([k, v]) => (
                          <option key={k} value={k}>
                            {v}
                          </option>
                        ))}
                      </Select>
                    </td>
                    <td className="px-4 py-3">{task.estimated_hours}h</td>
                    <td className="px-4 py-3 text-right">
                      <IconButton label="Edit task" onClick={() => openEditTask(task)} />
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td className="px-4 py-8 text-center text-ink/50" colSpan={6}>
                    No tasks. Add one so the team can track time.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-4">
          {columns.map((col) => (
            <Card key={col}>
              <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide">{labels.taskStatus[col]}</h4>
              <div className="space-y-2">
                {tasks.data
                  ?.filter((t) => t.status === col)
                  .map((task) => (
                    <div
                      key={task.id}
                      draggable
                      onDragStart={(e) => e.dataTransfer.setData("task", task.id)}
                      className="rounded-2xl bg-mist p-3"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-semibold">{task.title}</p>
                          <p className="text-xs text-ink/50">{task.assignee_name}</p>
                        </div>
                        <IconButton label="Edit task" onClick={() => openEditTask(task)} />
                      </div>
                    </div>
                  ))}
                <div
                  className="min-h-10 rounded-2xl border border-dashed border-ink/10"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    const id = e.dataTransfer.getData("task");
                    if (id) updateTask.mutate({ id, status: col });
                  }}
                />
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal open={open} title={editingTask ? "Edit task" : "New task"} onClose={() => { setOpen(false); setEditingTask(null); }}>
        <div className="space-y-3">
          <div>
            <Label>Title</Label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <Label>Assignee</Label>
            <Select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
              <option value="">Unassigned</option>
              {p?.members.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Estimated hours</Label>
            <Input value={hours} onChange={(e) => setHours(e.target.value)} />
          </div>
          <div>
            <Label>Priority</Label>
            <Select value={priority} onChange={(e) => setPriority(e.target.value)}>
              {Object.entries(labels.priority).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Description</Label>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Optional details" />
          </div>
          <Button onClick={() => (editingTask ? saveTask.mutate() : createTask.mutate())}>
            {editingTask ? "Save changes" : "Create task"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
