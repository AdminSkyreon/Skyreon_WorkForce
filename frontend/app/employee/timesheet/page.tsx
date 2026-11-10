"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, isValid, parseISO, startOfWeek } from "date-fns";
import { useMemo, useState } from "react";
import { Badge, Button, Card, FieldError, Input, Label, Modal, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { Task, Timesheet } from "@/lib/types";
import { labels } from "@/lib/utils";

function mondayOf(value: string) {
  const parsed = parseISO(value);
  if (!isValid(parsed)) return null;
  return format(startOfWeek(parsed, { weekStartsOn: 1 }), "yyyy-MM-dd");
}

function isValidNonNegative(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return false;
  const num = Number(trimmed);
  return Number.isFinite(num) && num >= 0;
}

export default function TimesheetPage() {
  const qc = useQueryClient();
  const [view, setView] = useState<"week" | "month">("week");
  const [week, setWeek] = useState(mondayOf(format(new Date(), "yyyy-MM-dd"))!);
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [extraIds, setExtraIds] = useState<string[]>([]);
  const [cellError, setCellError] = useState("");

  // Add task row modal state
  const [addRow, setAddRow] = useState(false);
  const [rowTaskMode, setRowTaskMode] = useState<"existing" | "new">("existing");
  const [rowTaskId, setRowTaskId] = useState("");
  const [rowProjectId, setRowProjectId] = useState("");
  const [rowTitle, setRowTitle] = useState("");
  const [rowEstimate, setRowEstimate] = useState("8");
  const [rowSubmitted, setRowSubmitted] = useState(false);

  // Manual entry modal state
  const [open, setOpen] = useState(false);
  const [manualTaskMode, setManualTaskMode] = useState<"existing" | "new">("existing");
  const [manualTaskId, setManualTaskId] = useState("");
  const [manualProjectId, setManualProjectId] = useState("");
  const [manualTitle, setManualTitle] = useState("");
  const [manualEstimate, setManualEstimate] = useState("8");
  const [workDate, setWorkDate] = useState(week);
  const [hours, setHours] = useState("1");
  const [reason, setReason] = useState("");
  const [manualSubmitted, setManualSubmitted] = useState(false);

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

  async function createInlineTask(projectId: string, title: string, estimate: string) {
    const created = await api<Task>(`/me/projects/${projectId}/tasks`, {
      method: "POST",
      body: JSON.stringify({
        title: title.trim(),
        estimated_hours: estimate.trim() || "0",
        priority: "medium",
      }),
    });
    return created.id;
  }

  function closeAddRowModal() {
    setAddRow(false);
    setRowTaskMode("existing");
    setRowTaskId("");
    setRowProjectId("");
    setRowTitle("");
    setRowEstimate("8");
    setRowSubmitted(false);
    addRowTask.reset();
  }

  function closeManualModal() {
    setOpen(false);
    setManualTaskMode("existing");
    setManualTaskId("");
    setManualProjectId("");
    setManualTitle("");
    setManualEstimate("8");
    setWorkDate(week);
    setHours("1");
    setReason("");
    setManualSubmitted(false);
    add.reset();
  }

  const add = useMutation({
    mutationFn: async () => {
      const id =
        manualTaskMode === "existing"
          ? manualTaskId
          : await createInlineTask(manualProjectId, manualTitle, manualEstimate);
      return api("/me/timesheets/entries", {
        method: "POST",
        body: JSON.stringify({
          task_id: id,
          work_date: workDate,
          hours: hours.trim(),
          reason: reason.trim(),
        }),
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["timesheet"] });
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      toast.success("Time entry added");
      closeManualModal();
    },
  });

  const addRowTask = useMutation({
    mutationFn: async () =>
      rowTaskMode === "existing"
        ? rowTaskId
        : createInlineTask(rowProjectId, rowTitle, rowEstimate),
    onSuccess: (id) => {
      setExtraIds((prev) => (prev.includes(id) ? prev : [...prev, id]));
      void qc.invalidateQueries({ queryKey: ["my-tasks"] });
      closeAddRowModal();
    },
  });
  const setDay = useMutation({
    mutationFn: (payload: { task_id: string; work_date: string; hours: string }) =>
      api<Timesheet>("/me/timesheets/day", { method: "PUT", body: JSON.stringify(payload) }),
    onSuccess: () => {
      setCellError("");
      void qc.invalidateQueries({ queryKey: ["timesheet", week] });
    },
  });
  const [submitNote, setSubmitNote] = useState("");
  const submit = useMutation({
    mutationFn: () => api<Timesheet>(`/me/timesheets/submit?week_start=${week}`, { method: "POST" }),
    onSuccess: (result) => {
      const n = result.extra_work_pending_count ?? 0;
      setSubmitNote(
        n > 0 ? `${n} extra day(s) sent for manager approval (weekend/holiday hours).` : "",
      );
      toast.success("Timesheet submitted");
      void qc.invalidateQueries({ queryKey: ["timesheet", week] });
    },
  });

  const data = sheet.data;
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(parseISO(week), i)),
    [week],
  );
  const weekEnd = format(days[6], "yyyy-MM-dd");
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

  const rowErrors = {
    task: rowTaskMode === "existing" && !rowTaskId ? "Select a task" : "",
    project: rowTaskMode === "new" && !rowProjectId ? "Select a project" : "",
    title:
      rowTaskMode === "new"
        ? !rowTitle.trim()
          ? "Task title is required"
          : rowTitle.trim().length > 255
            ? "Max 255 characters"
            : ""
        : "",
    estimate:
      rowTaskMode === "new" && !isValidNonNegative(rowEstimate)
        ? "Estimate must be 0 or greater"
        : "",
  };
  const hasRowErrors = Object.values(rowErrors).some(Boolean);

  const manualHoursNum = Number(hours.trim());
  const manualDayIndex = days.findIndex((d) => format(d, "yyyy-MM-dd") === workDate);
  const existingDayTotal =
    manualDayIndex >= 0 && data?.daily_totals[manualDayIndex] !== undefined
      ? Number(data.daily_totals[manualDayIndex])
      : 0;
  const manualErrors = {
    task: manualTaskMode === "existing" && !manualTaskId ? "Select a task" : "",
    project: manualTaskMode === "new" && !manualProjectId ? "Select a project" : "",
    title:
      manualTaskMode === "new"
        ? !manualTitle.trim()
          ? "Task title is required"
          : manualTitle.trim().length > 255
            ? "Max 255 characters"
            : ""
        : "",
    estimate:
      manualTaskMode === "new" && !isValidNonNegative(manualEstimate)
        ? "Estimate must be 0 or greater"
        : "",
    workDate: !workDate ? "Date is required" : "",
    hours:
      !hours.trim() || !Number.isFinite(manualHoursNum) || manualHoursNum <= 0 || manualHoursNum > 24
        ? "Hours must be between 0.01 and 24"
        : manualDayIndex >= 0 && existingDayTotal + manualHoursNum > 24
          ? `Day total cannot exceed 24h (already logged ${existingDayTotal}h)`
          : "",
    reason: !reason.trim()
      ? "Reason is required"
      : reason.trim().length > 500
        ? "Max 500 characters"
        : "",
  };
  const hasManualErrors = Object.values(manualErrors).some(Boolean);

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

  function handleCellBlur(
    e: React.FocusEvent<HTMLInputElement>,
    taskId: string,
    workDateStr: string,
    previousHours: string,
    dayIdx: number,
  ) {
    const raw = e.target.value.trim();
    const nextStr = raw === "" ? "0" : raw;
    const nextNum = Number(nextStr);
    const prevNum = Number(previousHours);
    if (!Number.isFinite(nextNum) || nextNum < 0 || nextNum > 24) {
      e.target.value = previousHours;
      setCellError("Hours must be between 0 and 24.");
      return;
    }
    if (nextNum === prevNum) {
      setCellError("");
      return;
    }
    const dayTotal = data?.daily_totals[dayIdx] !== undefined ? Number(data.daily_totals[dayIdx]) : 0;
    if (dayTotal - prevNum + nextNum > 24) {
      e.target.value = previousHours;
      setCellError(`Total hours for ${workDateStr} cannot exceed 24h.`);
      return;
    }
    setCellError("");
    setDay.mutate({ task_id: taskId, work_date: workDateStr, hours: nextStr });
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
            onChange={(e) => {
              const nextMonday = mondayOf(e.target.value);
              if (nextMonday) setWeek(nextMonday);
            }}
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
            setRowSubmitted(false);
            addRowTask.reset();
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
            setManualSubmitted(false);
            add.reset();
            setWorkDate(week);
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
                    {row.days.map((cell, dayIdx) => (
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
                            disabled={setDay.isPending}
                            defaultValue={cell.hours}
                            className="w-20 px-2 py-1"
                            onBlur={(e) => handleCellBlur(e, row.task_id, cell.date, cell.hours, dayIdx)}
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
                    {emptyDays().map((cell, dayIdx) => (
                      <td key={cell.date} className="px-4 py-2">
                        {editable ? (
                          <Input
                            type="number"
                            min="0"
                            max="24"
                            step="0.25"
                            disabled={setDay.isPending}
                            defaultValue="0"
                            className="w-20 px-2 py-1"
                            onBlur={(e) => handleCellBlur(e, task.id, cell.date, "0", dayIdx)}
                          />
                        ) : (
                          cell.hours
                        )}
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
      {cellError ? <p className="text-sm text-red-700">{cellError}</p> : null}
      {setDay.error ? <p className="text-sm text-red-700">{setDay.error.message}</p> : null}

      <Modal open={addRow} title="Add task row" onClose={closeAddRowModal}>
        <div className="space-y-3">
          <div className="flex rounded-full bg-mist p-1 text-sm font-semibold">
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${rowTaskMode === "existing" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => {
                setRowSubmitted(false);
                setRowTaskMode("existing");
              }}
              disabled={!unusedTasks.length || addRowTask.isPending}
            >
              Existing task
            </button>
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${rowTaskMode === "new" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => {
                setRowSubmitted(false);
                setRowTaskMode("new");
              }}
              disabled={addRowTask.isPending}
            >
              New task
            </button>
          </div>
          {rowTaskMode === "existing" ? (
            <div>
              <Label>Task</Label>
              <Select disabled={addRowTask.isPending} value={rowTaskId} onChange={(e) => setRowTaskId(e.target.value)}>
                <option value="">Select task</option>
                {unusedTasks.map((task) => (
                  <option key={task.id} value={task.id}>
                    {task.project_name} — {task.title}
                  </option>
                ))}
              </Select>
              {rowSubmitted && <FieldError message={rowErrors.task} />}
            </div>
          ) : (
            <>
              <div>
                <Label>Project</Label>
                <Select disabled={addRowTask.isPending} value={rowProjectId} onChange={(e) => setRowProjectId(e.target.value)}>
                  <option value="">Select project</option>
                  {projects.data?.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                      {project.client_name ? ` · ${project.client_name}` : ""}
                    </option>
                  ))}
                </Select>
                {rowSubmitted && <FieldError message={rowErrors.project} />}
              </div>
              <div>
                <Label>Task title</Label>
                <Input maxLength={255} disabled={addRowTask.isPending} value={rowTitle} onChange={(e) => setRowTitle(e.target.value)} placeholder="What you worked on" />
                {rowSubmitted && <FieldError message={rowErrors.title} />}
              </div>
              <div>
                <Label>Estimate (hours)</Label>
                <Input type="number" min="0" step="0.25" disabled={addRowTask.isPending} value={rowEstimate} onChange={(e) => setRowEstimate(e.target.value)} />
                {rowSubmitted && <FieldError message={rowErrors.estimate} />}
              </div>
            </>
          )}
          {addRowTask.error ? <p className="text-sm text-red-700">{addRowTask.error.message}</p> : null}
          <Button
            className="mt-2"
            loading={addRowTask.isPending}
            onClick={() => {
              setRowSubmitted(true);
              if (!hasRowErrors) addRowTask.mutate();
            }}
          >
            {addRowTask.isPending ? "Adding..." : "Add row"}
          </Button>
        </div>
      </Modal>

      <Modal open={open} title="Manual time entry" onClose={closeManualModal}>
        <div className="space-y-3">
          <div className="flex rounded-full bg-mist p-1 text-sm font-semibold">
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${manualTaskMode === "existing" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => {
                setManualSubmitted(false);
                setManualTaskMode("existing");
              }}
              disabled={add.isPending}
            >
              Existing task
            </button>
            <button
              type="button"
              className={`flex-1 rounded-full px-3 py-1.5 ${manualTaskMode === "new" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
              onClick={() => {
                setManualSubmitted(false);
                setManualTaskMode("new");
              }}
              disabled={add.isPending}
            >
              New task
            </button>
          </div>
          {manualTaskMode === "existing" ? (
            <div>
              <Label>Task</Label>
              <Select disabled={add.isPending} value={manualTaskId} onChange={(e) => setManualTaskId(e.target.value)}>
                <option value="">Select task</option>
                {tasks.data?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.project_name} — {t.title}
                  </option>
                ))}
              </Select>
              {manualSubmitted && <FieldError message={manualErrors.task} />}
            </div>
          ) : (
            <>
              <div>
                <Label>Project</Label>
                <Select disabled={add.isPending} value={manualProjectId} onChange={(e) => setManualProjectId(e.target.value)}>
                  <option value="">Select project</option>
                  {projects.data?.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                      {project.client_name ? ` · ${project.client_name}` : ""}
                    </option>
                  ))}
                </Select>
                {manualSubmitted && <FieldError message={manualErrors.project} />}
              </div>
              <div>
                <Label>Task title</Label>
                <Input maxLength={255} disabled={add.isPending} value={manualTitle} onChange={(e) => setManualTitle(e.target.value)} placeholder="What you worked on" />
                {manualSubmitted && <FieldError message={manualErrors.title} />}
              </div>
              <div>
                <Label>Estimate (hours)</Label>
                <Input type="number" min="0" step="0.25" disabled={add.isPending} value={manualEstimate} onChange={(e) => setManualEstimate(e.target.value)} />
                {manualSubmitted && <FieldError message={manualErrors.estimate} />}
              </div>
            </>
          )}
          <div>
            <Label>Date</Label>
            <Input type="date" min={week} max={weekEnd} disabled={add.isPending} value={workDate} onChange={(e) => setWorkDate(e.target.value)} />
            {manualSubmitted && <FieldError message={manualErrors.workDate} />}
          </div>
          <div>
            <Label>Hours</Label>
            <Input type="number" min="0.01" max="24" step="0.25" disabled={add.isPending} value={hours} onChange={(e) => setHours(e.target.value)} />
            {manualSubmitted && <FieldError message={manualErrors.hours} />}
          </div>
          <div>
            <Label>Reason (required)</Label>
            <Input maxLength={500} disabled={add.isPending} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why this was entered manually" />
            {manualSubmitted && <FieldError message={manualErrors.reason} />}
          </div>
          {add.error ? <p className="text-sm text-red-700">{add.error.message}</p> : null}
          <Button
            loading={add.isPending}
            onClick={() => {
              setManualSubmitted(true);
              if (!hasManualErrors) add.mutate();
            }}
          >
            {add.isPending ? "Adding..." : "Add entry"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
