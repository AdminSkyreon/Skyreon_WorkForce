"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, parseISO, startOfWeek } from "date-fns";
import { useMemo, useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Task, Timesheet } from "@/lib/types";
import { labels } from "@/lib/utils";

function mondayOf(value: string) {
  return format(startOfWeek(parseISO(value), { weekStartsOn: 1 }), "yyyy-MM-dd");
}

export default function TimesheetPage() {
  const qc = useQueryClient();
  const [view, setView] = useState<"week" | "month">("week");
  const [week, setWeek] = useState(mondayOf(format(new Date(), "yyyy-MM-dd")));
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [open, setOpen] = useState(false);
  const [addRow, setAddRow] = useState(false);
  const [extraIds, setExtraIds] = useState<string[]>([]);
  const [taskId, setTaskId] = useState("");
  const [manualTaskMode, setManualTaskMode] = useState<"existing" | "new">("existing");
  const [rowTaskMode, setRowTaskMode] = useState<"existing" | "new">("existing");
  const [newTaskProjectId, setNewTaskProjectId] = useState("");
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskEstimate, setNewTaskEstimate] = useState("8");
  const [workDate, setWorkDate] = useState(week);
  const [hours, setHours] = useState("1");
  const [reason, setReason] = useState("");

  const sheet = useQuery({
    queryKey: ["timesheet", week],
    queryFn: () => api<Timesheet>(`/me/timesheets?week_start=${week}`),
    enabled: view === "week",
    placeholderData: (prev) => prev,
  });
  const monthSheets = useQuery({
    queryKey: ["timesheet-month", year, month],
    queryFn: () => api<Timesheet[]>(`/me/timesheets/month?year=${year}&month=${month}`),
    enabled: view === "month",
    placeholderData: (prev) => prev,
  });
  const timesheetFetching =
    (view === "week" && sheet.isFetching && !sheet.isLoading) ||
    (view === "month" && monthSheets.isFetching && !monthSheets.isLoading);
  const tasks = useQuery({ queryKey: ["my-tasks"], queryFn: () => api<Task[]>("/me/tasks") });
  const projects = useQuery({ queryKey: ["my-projects"], queryFn: () => api<{ id: string; name: string; client_name: string }[]>("/me/projects") });

  async function resolveTaskId(mode: "existing" | "new", selectedId: string) {
    if (mode === "existing") return selectedId;
    if (!newTaskProjectId || !newTaskTitle.trim()) {
      throw new Error("Choose a project and task title");
    }
    const created = await api<Task>(`/me/projects/${newTaskProjectId}/tasks`, {
      method: "POST",
      body: JSON.stringify({
        title: newTaskTitle.trim(),
        estimated_hours: newTaskEstimate || "8",
        priority: "medium",
      }),
    });
    return created.id;
  }

  const add = useMutation({
    mutationFn: async () => {
      const id = await resolveTaskId(manualTaskMode, taskId);
      return api("/me/timesheets/entries", {
        method: "POST",
        body: JSON.stringify({ task_id: id, work_date: workDate, hours, reason }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["timesheet", week] });
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      setOpen(false);
      setManualTaskMode("existing");
      setNewTaskTitle("");
      setNewTaskProjectId("");
    },
  });

  const addRowTask = useMutation({
    mutationFn: async () => resolveTaskId(rowTaskMode, taskId),
    onSuccess: (id) => {
      setExtraIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      setAddRow(false);
      setRowTaskMode("existing");
      setTaskId("");
      setNewTaskTitle("");
      setNewTaskProjectId("");
    },
  });
  const setDay = useMutation({
    mutationFn: (payload: { task_id: string; work_date: string; hours: string }) =>
      api<Timesheet>("/me/timesheets/day", { method: "PUT", body: JSON.stringify(payload) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["timesheet", week] }),
  });
  const [submitNote, setSubmitNote] = useState("");
  const submit = useMutation({
    mutationFn: () => api<Timesheet>(`/me/timesheets/submit?week_start=${week}`, { method: "POST" }),
    onSuccess: (result) => {
      const n = result.extra_work_pending_count ?? 0;
      setSubmitNote(
        n > 0 ? `${n} extra day(s) sent for manager approval (weekend/holiday hours).` : "",
      );
      void qc.invalidateQueries({ queryKey: ["timesheet", week] });
    },
  });

  const data = sheet.data;
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(parseISO(week), i)),
    [week],
  );
  const weekLabel = `Week of ${format(days[0], "EEE d MMM")} – ${format(days[6], "EEE d MMM")}`;
  const editable = Boolean(data && !data.locked && data.status !== "submitted");
  const shownIds = new Set([...(data?.rows.map((row) => row.task_id) ?? []), ...extraIds]);
  const extraTasks = tasks.data?.filter((task) => extraIds.includes(task.id) && !data?.rows.some((row) => row.task_id === task.id)) ?? [];
  const unusedTasks = tasks.data?.filter((task) => !shownIds.has(task.id) && task.status !== "completed") ?? [];
  const submitDisabled = !data || data.locked || data.status === "submitted" || Number(data.weekly_total) <= 0;
  const submitWhy =
    data?.status === "submitted"
      ? "Already submitted — waiting for admin"
      : data?.locked
        ? "Approved — this week is locked"
        : !data || Number(data.weekly_total) <= 0
          ? "Add hours first"
          : "";

  function emptyDays() {
    return days.map((day) => ({
      date: format(day, "yyyy-MM-dd"),
      hours: "0.00",
      is_manual: false,
      is_holiday: false,
      is_weekend: false,
      is_leave: false,
      exceeds_12h: false,
    }));
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/60">
        Type hours in a cell, or use Start/Stop on My Tasks. Submit the week when the grid is complete.
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <Select value={view} onChange={(e) => setView(e.target.value as "week" | "month")}>
          <option value="week">Week</option>
          <option value="month">Month</option>
        </Select>
        {view === "month" ? (
          <>
            <Select value={year} onChange={(e) => setYear(e.target.value)}>
              {[now.getFullYear(), now.getFullYear() - 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </Select>
            <Select value={month} onChange={(e) => setMonth(e.target.value)}>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={String(i + 1)}>{new Date(2000, i, 1).toLocaleString("en", { month: "long" })}</option>
              ))}
            </Select>
          </>
        ) : (
          <Input
            type="date"
            value={week}
            onChange={(e) => setWeek(mondayOf(e.target.value))}
            className="max-w-xs"
          />
        )}
        {view === "week" && (
          <>
        <p className="text-sm font-semibold">{weekLabel}</p>
        <Badge tone={data?.status === "approved" ? "good" : data?.status === "rejected" ? "bad" : "warn"}>
          {data ? labels.timesheet[data.status] : ""}
        </Badge>
        <Button
          variant="outline"
          onClick={() => {
            setRowTaskMode(unusedTasks.length ? "existing" : "new");
            setAddRow(true);
          }}
          disabled={!editable || (!unusedTasks.length && !projects.data?.length)}
        >
          Add task row
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            setManualTaskMode(tasks.data?.length ? "existing" : "new");
            setOpen(true);
          }}
          disabled={!editable}
        >
          Manual entry
        </Button>
        <Button
          loading={submit.isPending}
          onClick={() => submit.mutate()}
          disabled={submitDisabled}
        >
          {submit.isPending ? "Submitting..." : "Submit week"}
        </Button>
          </>
        )}
      </div>
      {timesheetFetching ? <p className="text-xs text-ink/50">Updating timesheet…</p> : null}
      {view === "month" && (
        <div className={`space-y-3 ${timesheetFetching ? "opacity-70" : ""}`}>
          {monthSheets.data?.map((row) => (
            <Card key={row.week_start} className="flex items-center justify-between">
              <div>
                <p className="font-semibold">Week of {row.week_start}</p>
                <p className="text-sm text-ink/50">{row.weekly_total}h · {row.status}</p>
              </div>
              <Button variant="outline" onClick={() => { setWeek(row.week_start); setView("week"); }}>
                Open week
              </Button>
            </Card>
          ))}
        </div>
      )}
      {view === "week" && submitWhy ? <p className="text-xs text-ink/50">{submitWhy}</p> : null}
      {view === "week" && data?.status === "rejected" && data.comment ? (
        <Card className="text-sm text-red-800">Rejected: {data.comment}</Card>
      ) : null}
      {view === "week" && submitNote ? <Card className="text-sm text-teal-900">{submitNote}</Card> : null}
      {view === "week" && data?.warnings?.length ? <Card className="text-sm text-amber-800">{data.warnings.join(" · ")}</Card> : null}
      {view === "week" && (
      <Card className={`overflow-x-auto p-0 ${timesheetFetching ? "opacity-70" : ""}`}>
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase text-ink/60">
            <tr>
              <th className="px-4 py-3">Task</th>
              {days.map((day) => (
                <th key={day.toISOString()} className="px-4 py-3">
                  {format(day, "EEE d")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data?.rows.length || extraTasks.length ? (
              <>
                {data?.rows.map((row) => (
                  <tr key={row.task_id} className="border-t border-ink/5">
                    <td className="px-4 py-3">
                      <p className="font-semibold">{row.task_title}</p>
                      <p className="text-xs text-ink/50">{row.project_name}</p>
                    </td>
                    {row.days.map((cell) => (
                      <td
                        key={cell.date}
                        className={`px-4 py-2 ${
                          cell.exceeds_12h || cell.is_leave
                            ? "bg-amber-50"
                            : cell.is_holiday
                              ? "bg-sky-50"
                              : cell.is_weekend
                                ? "bg-violet-50"
                                : ""
                        }`}
                      >
                        {editable ? (
                          <Input
                            key={`${row.task_id}-${cell.date}-${cell.hours}`}
                            type="number"
                            min="0"
                            max="24"
                            step="0.25"
                            defaultValue={cell.hours}
                            className="w-20 px-2 py-1"
                            onBlur={(e) => {
                              const next = e.target.value || "0";
                              if (Number(next) === Number(cell.hours)) return;
                              setDay.mutate({ task_id: row.task_id, work_date: cell.date, hours: next });
                            }}
                          />
                        ) : (
                          cell.hours
                        )}
                        {cell.is_manual ? <span className="ml-1 text-[10px] uppercase text-copper">manual</span> : null}
                      </td>
                    ))}
                  </tr>
                ))}
                {extraTasks.map((task) => (
                  <tr key={task.id} className="border-t border-ink/5">
                    <td className="px-4 py-3">
                      <p className="font-semibold">{task.title}</p>
                      <p className="text-xs text-ink/50">{task.project_name}</p>
                    </td>
                    {emptyDays().map((cell) => (
                      <td key={cell.date} className="px-4 py-2">
                        <Input
                          type="number"
                          min="0"
                          max="24"
                          step="0.25"
                          defaultValue="0"
                          className="w-20 px-2 py-1"
                          onBlur={(e) => {
                            const next = e.target.value || "0";
                            if (Number(next) === 0) return;
                            setDay.mutate({ task_id: task.id, work_date: cell.date, hours: next });
                          }}
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </>
            ) : (
              <tr>
                <td className="px-4 py-6 text-sm text-ink/50" colSpan={8}>
                  No hours this week. Start a timer on My Tasks, add a task row, or type a manual entry, then submit.
                </td>
              </tr>
            )}
            <tr className="border-t border-ink/10 font-semibold">
              <td className="px-4 py-3">Daily total</td>
              {data?.daily_totals.map((total, i) => (
                <td key={i} className="px-4 py-3">
                  {total}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </Card>
      )}
      {view === "week" && (
      <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-ink/60">
        <p>Weekly total: {data?.weekly_total ?? 0}h</p>
        <p>Amber cell = holiday, approved leave, or over 12 hours.</p>
      </div>
      )}
      {setDay.error ? <p className="text-sm text-red-700">{setDay.error.message}</p> : null}

      <Modal open={addRow} title="Add task row" onClose={() => setAddRow(false)}>
        <div className="space-y-3">
          <div className="flex rounded-full bg-mist p-1 text-sm font-semibold">
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${rowTaskMode === "existing" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => setRowTaskMode("existing")}
              disabled={!unusedTasks.length}
            >
              Existing task
            </button>
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${rowTaskMode === "new" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => setRowTaskMode("new")}
            >
              New task
            </button>
          </div>
          {rowTaskMode === "existing" ? (
            <>
              <Label>Task</Label>
              <Select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
                <option value="">Select task</option>
                {unusedTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.project_name} — {task.title}
                  </option>
                ))}
              </Select>
            </>
          ) : (
            <>
              <div>
                <Label>Project</Label>
                <Select value={newTaskProjectId} onChange={(e) => setNewTaskProjectId(e.target.value)}>
                  <option value="">Select project</option>
                  {projects.data?.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                      {project.client_name ? ` · ${project.client_name}` : ""}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label>Task title</Label>
                <Input value={newTaskTitle} onChange={(e) => setNewTaskTitle(e.target.value)} placeholder="What you worked on" />
              </div>
              <div>
                <Label>Estimate (hours)</Label>
                <Input value={newTaskEstimate} onChange={(e) => setNewTaskEstimate(e.target.value)} />
              </div>
            </>
          )}
          {addRowTask.error ? <p className="text-sm text-red-700">{addRowTask.error.message}</p> : null}
          <Button
            className="mt-2"
            disabled={rowTaskMode === "existing" ? !taskId : !newTaskProjectId || !newTaskTitle.trim()}
            onClick={() => addRowTask.mutate()}
          >
            Add row
          </Button>
        </div>
      </Modal>

      <Modal open={open} title="Manual time entry" onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <div className="flex rounded-full bg-mist p-1 text-sm font-semibold">
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${manualTaskMode === "existing" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => setManualTaskMode("existing")}
            >
              Existing task
            </button>
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${manualTaskMode === "new" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => setManualTaskMode("new")}
            >
              New task
            </button>
          </div>
          {manualTaskMode === "existing" ? (
            <div>
              <Label>Task</Label>
              <Select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
                <option value="">Select task</option>
                {tasks.data?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.project_name} — {t.title}
                  </option>
                ))}
              </Select>
            </div>
          ) : (
            <>
              <div>
                <Label>Project</Label>
                <Select value={newTaskProjectId} onChange={(e) => setNewTaskProjectId(e.target.value)}>
                  <option value="">Select project</option>
                  {projects.data?.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                      {project.client_name ? ` · ${project.client_name}` : ""}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label>Task title</Label>
                <Input value={newTaskTitle} onChange={(e) => setNewTaskTitle(e.target.value)} placeholder="What you worked on" />
              </div>
              <div>
                <Label>Estimate (hours)</Label>
                <Input value={newTaskEstimate} onChange={(e) => setNewTaskEstimate(e.target.value)} />
              </div>
            </>
          )}
          <div>
            <Label>Date</Label>
            <Input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} />
          </div>
          <div>
            <Label>Hours</Label>
            <Input value={hours} onChange={(e) => setHours(e.target.value)} />
          </div>
          <div>
            <Label>Reason (required)</Label>
            <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why this was entered manually" />
          </div>
          {add.error ? <p className="text-sm text-red-700">{add.error.message}</p> : null}
          <Button
            loading={add.isPending}
            onClick={() => add.mutate()}
            disabled={
              !reason.trim() ||
              !hours ||
              (manualTaskMode === "existing" ? !taskId : !newTaskProjectId || !newTaskTitle.trim())
            }
          >
            Add entry
          </Button>
        </div>
      </Modal>
    </div>
  );
}
