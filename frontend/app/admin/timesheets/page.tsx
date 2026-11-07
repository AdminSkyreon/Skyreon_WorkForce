"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addDays, format, parseISO, startOfWeek } from "date-fns";
import { useMemo, useState } from "react";
import { Badge, Button, Card, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Timesheet } from "@/lib/types";
import { labels } from "@/lib/utils";

type StatusFilter = "all" | "submitted" | "approved" | "rejected";

function weekLabel(weekStart: string) {
  const start = parseISO(weekStart);
  return `${format(start, "d MMM")} – ${format(addDays(start, 6), "d MMM yyyy")}`;
}

function dayHeaders(weekStart: string) {
  return Array.from({ length: 7 }, (_, i) => format(addDays(parseISO(weekStart), i), "EEE d"));
}

function toneFor(status: Timesheet["status"]) {
  if (status === "approved") return "good" as const;
  if (status === "rejected") return "bad" as const;
  return "warn" as const;
}

function projectNames(sheet: Timesheet) {
  return [...new Set(sheet.rows.filter((row) => row.days.some((cell) => Number(cell.hours) > 0)).map((row) => row.project_name))];
}

function activeRows(sheet: Timesheet) {
  return sheet.rows.filter((row) => row.days.some((cell) => Number(cell.hours) > 0));
}

function sheetKey(sheet: Timesheet) {
  return sheet.id ?? `${sheet.employee_id}-${sheet.week_start}`;
}

export default function AdminTimesheetsPage() {
  const qc = useQueryClient();
  const [status, setStatus] = useState<StatusFilter>("all");
  const [employee, setEmployee] = useState("all");
  const [project, setProject] = useState("all");
  const [view, setView] = useState<"week" | "month">("week");
  const [week, setWeek] = useState(format(startOfWeek(new Date(), { weekStartsOn: 1 }), "yyyy-MM-dd"));
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [search, setSearch] = useState("");
  const [openId, setOpenId] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, string>>({});

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["admin-timesheets", view, week, year, month],
    queryFn: () =>
      api<Timesheet[]>(
        view === "month"
          ? `/timesheets?year=${year}&month=${month}`
          : `/timesheets?week_start=${week}`,
      ),
    placeholderData: (prev) => prev,
  });
  const review = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment: string }) =>
      api(`/timesheets/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) }),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: ["admin-timesheets"] });
      setComments((prev) => ({ ...prev, [vars.id]: "" }));
    },
  });

  const employees = useMemo(
    () => [...new Set((data ?? []).map((sheet) => sheet.employee_name).filter(Boolean))].sort() as string[],
    [data],
  );
  const projects = useMemo(
    () => [...new Set((data ?? []).flatMap(projectNames))].sort(),
    [data],
  );
  const sheets = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (data ?? []).filter((sheet) => {
      if (status !== "all" && sheet.status !== status) return false;
      if (employee !== "all" && sheet.employee_name !== employee) return false;
      if (view === "week" && sheet.week_start !== week) return false;
      const names = projectNames(sheet);
      if (project !== "all" && !names.includes(project)) return false;
      if (q) {
        const hay = `${sheet.employee_name ?? ""} ${names.join(" ")} ${sheet.week_start}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [data, status, employee, project, week, search, view]);

  const pending = (data ?? []).filter((sheet) => sheet.status === "submitted").length;
  const selected = sheets.find((sheet) => sheetKey(sheet) === openId) ?? sheets[0] ?? null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="max-w-2xl text-sm text-ink/60">
          Week or month view. Admin and Super admin can open any person and period. You cannot approve your own week.
        </p>
        <p className="text-sm text-ink/60">
          {sheets.length} shown · {pending} awaiting review
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <Input placeholder="Search employee or project" value={search} onChange={(e) => setSearch(e.target.value)} />
        <Select value={employee} onChange={(e) => setEmployee(e.target.value)}>
          <option value="all">All employees</option>
          {employees.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select value={project} onChange={(e) => setProject(e.target.value)}>
          <option value="all">All projects</option>
          {projects.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select value={view} onChange={(e) => setView(e.target.value as "week" | "month")}>
          <option value="week">This week view</option>
          <option value="month">Month view</option>
        </Select>
        {view === "week" ? (
          <Input type="date" value={week} onChange={(e) => setWeek(format(startOfWeek(parseISO(e.target.value), { weekStartsOn: 1 }), "yyyy-MM-dd"))} />
        ) : (
          <Select value={`${year}-${month}`} onChange={(e) => {
            const [y, m] = e.target.value.split("-");
            setYear(y);
            setMonth(m);
          }}>
            {[now.getFullYear(), now.getFullYear() - 1].flatMap((y) =>
              Array.from({ length: 12 }, (_, i) => (
                <option key={`${y}-${i + 1}`} value={`${y}-${i + 1}`}>
                  {new Date(y, i, 1).toLocaleString("en", { month: "long", year: "numeric" })}
                </option>
              )),
            )}
          </Select>
        )}
        <Select value={status} onChange={(e) => setStatus(e.target.value as StatusFilter)}>
          <option value="all">All statuses</option>
          <option value="submitted">Awaiting review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </Select>
      </div>

      {isLoading && !data ? <Card className="text-sm text-ink/60">Loading timesheets…</Card> : null}
      {isFetching && !isLoading ? <p className="text-xs text-ink/50">Updating timesheets…</p> : null}

      {!isLoading && sheets.length === 0 ? (
        <Card>
          <h3 className="font-display text-2xl">No timesheets match</h3>
          <p className="mt-2 text-sm leading-6 text-ink/70">
            Employees submit a week from their Timesheet page. After that, rows appear here for every person and
            project they logged time against.
          </p>
        </Card>
      ) : null}

      {sheets.length > 0 ? (
        <div className={`grid gap-4 xl:grid-cols-[1.15fr_0.85fr] ${isFetching && !isLoading ? "opacity-70" : ""}`}>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="bg-mist text-xs uppercase tracking-wide text-ink/60">
                <tr>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Projects</th>
                  <th className="px-4 py-3">Week</th>
                  <th className="px-4 py-3">Hours</th>
                  <th className="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {sheets.map((sheet) => {
                  const key = sheetKey(sheet);
                  const active = selected && sheetKey(selected) === key;
                  const names = projectNames(sheet);
                  return (
                    <tr
                      key={key}
                      className={`cursor-pointer border-t border-ink/5 ${active ? "bg-mist/70" : "hover:bg-mist/40"}`}
                      onClick={() => setOpenId(key)}
                    >
                      <td className="px-4 py-3 font-semibold">{sheet.employee_name || "Employee"}</td>
                      <td className="px-4 py-3 text-ink/70">{names.join(", ") || "—"}</td>
                      <td className="px-4 py-3 text-ink/70">{weekLabel(sheet.week_start)}</td>
                      <td className="px-4 py-3">{sheet.weekly_total}h</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={toneFor(sheet.status)}>{labels.timesheet[sheet.status]}</Badge>
                          {sheet.warnings.length > 0 ? <Badge tone="warn">{sheet.warnings.length} flags</Badge> : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          {selected ? (
            <Card className="space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-display text-2xl">{selected.employee_name}</h3>
                  <p className="text-sm text-ink/60">
                    {weekLabel(selected.week_start)} · {selected.weekly_total}h · {projectNames(selected).join(", ")}
                  </p>
                </div>
                <Badge tone={toneFor(selected.status)}>{labels.timesheet[selected.status]}</Badge>
              </div>

              {selected.warnings.length > 0 ? (
                <p className="text-sm text-amber-800">{selected.warnings.join(" · ")}</p>
              ) : null}

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-mist text-xs uppercase text-ink/60">
                    <tr>
                      <th className="px-3 py-2">Task</th>
                      {dayHeaders(selected.week_start).map((day) => (
                        <th key={day} className="px-3 py-2">
                          {day}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activeRows(selected).map((row) => (
                      <tr key={row.task_id} className="border-t border-ink/5">
                        <td className="px-3 py-2">
                          <p className="font-semibold">{row.task_title}</p>
                          <p className="text-xs text-ink/50">{row.project_name}</p>
                        </td>
                        {row.days.map((cell) => (
                          <td
                            key={cell.date}
                            className={`px-3 py-2 ${cell.exceeds_12h || cell.is_holiday || cell.is_leave ? "bg-amber-50" : ""}`}
                          >
                            {Number(cell.hours) > 0 ? cell.hours : "—"}
                            {cell.is_manual ? <span className="ml-1 text-[10px] uppercase text-copper">m</span> : null}
                          </td>
                        ))}
                      </tr>
                    ))}
                    <tr className="border-t border-ink/10 font-semibold">
                      <td className="px-3 py-2">Daily total</td>
                      {selected.daily_totals.map((total, i) => (
                        <td key={`${selected.week_start}-${i}`} className="px-3 py-2">
                          {total}
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>

              {selected.comment ? <p className="text-sm text-ink/70">Review note: {selected.comment}</p> : null}

              {selected.status === "submitted" && selected.id ? (
                <div className="space-y-3 border-t border-ink/5 pt-4">
                  <Textarea
                    placeholder="Optional review comment for the employee"
                    value={comments[selected.id] ?? ""}
                    onChange={(e) => setComments((prev) => ({ ...prev, [selected.id!]: e.target.value }))}
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      loading={review.isPending && review.variables?.action === "approve"}
                      onClick={() =>
                        review.mutate({ id: selected.id!, action: "approve", comment: comments[selected.id!] ?? "" })
                      }
                    >
                      Approve
                    </Button>
                    <Button
                      variant="danger"
                      loading={review.isPending && review.variables?.action === "reject"}
                      onClick={() =>
                        review.mutate({ id: selected.id!, action: "reject", comment: comments[selected.id!] ?? "" })
                      }
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              ) : null}
            </Card>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
