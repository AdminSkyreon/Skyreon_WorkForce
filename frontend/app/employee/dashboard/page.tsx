"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { EmployeeDashboard } from "@/lib/types";
import { labels } from "@/lib/utils";

function nextStep(data: EmployeeDashboard | undefined) {
  if (!data) return { href: "/employee/projects", title: "Get started", body: "Open Projects to add a task, then track time." };
  if (data.project_count === 0) {
    return { href: "/employee/projects", title: "Ask to join a project", body: "You are not on a project yet. An admin must add you to a team." };
  }
  if (data.open_tasks === 0) {
    return { href: "/employee/projects", title: "Add a task", body: "Open a project and add a task so you can start a timer or fill the timesheet." };
  }
  if (data.timesheet_status === "submitted") {
    return { href: "/employee/timesheet", title: "Waiting for review", body: "This week is submitted. Your project manager will approve or reject it." };
  }
  if (data.timesheet_status === "rejected") {
    return { href: "/employee/timesheet", title: "Fix and resubmit", body: "Your timesheet was rejected. Update hours and submit again." };
  }
  if (Number(data.hours_this_week) <= 0) {
    return { href: "/employee/tasks", title: "Track this week", body: "Start a timer on My Tasks, or type hours on Timesheet." };
  }
  if (data.timesheet_status === "draft") {
    return { href: "/employee/timesheet", title: "Submit this week", body: "Hours are on the timesheet. Review the grid and submit for approval." };
  }
  return { href: "/employee/timesheet", title: "Open timesheet", body: "See this week’s hours and status." };
}

export default function EmployeeDashboardPage() {
  const { data } = useQuery({
    queryKey: ["me-dashboard"],
    queryFn: () => api<EmployeeDashboard>("/me/dashboard"),
  });
  const step = nextStep(data);

  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Link href={step.href} className="md:col-span-3">
        <Card className="border border-forest/20">
          <p className="text-xs uppercase tracking-widest text-copper">What to do next</p>
          <h3 className="mt-2 font-display text-3xl">{step.title}</h3>
          <p className="mt-2 text-sm text-ink/60">{step.body}</p>
        </Card>
      </Link>
      <Link href="/employee/tasks">
        <Card>
          <p className="text-xs uppercase tracking-widest text-ink/50">Open tasks</p>
          <p className="mt-3 font-display text-5xl">{data?.open_tasks ?? "—"}</p>
        </Card>
      </Link>
      <Link href="/employee/timesheet">
        <Card>
          <p className="text-xs uppercase tracking-widest text-ink/50">Hours this week</p>
          <p className="mt-3 font-display text-5xl">{data?.hours_this_week ?? "—"}</p>
          <p className="mt-2 text-xs uppercase text-ink/50">
            {data ? labels.timesheet[data.timesheet_status] : ""}
          </p>
        </Card>
      </Link>
      <Link href="/employee/tasks">
        <Card>
          <p className="text-xs uppercase tracking-widest text-ink/50">Running</p>
          <p className="mt-3 font-display text-2xl">{data?.running_task_title || "No timer"}</p>
        </Card>
      </Link>
      {(data?.is_people_manager || data?.is_project_manager) && (
        <Link href={data.is_people_manager ? "/employee/team" : "/employee/team-timesheets"} className="md:col-span-3">
          <Card className="border border-copper/30">
            <p className="text-xs uppercase tracking-widest text-copper">Waiting on you</p>
            <p className="mt-2 font-display text-3xl">
              {(data.pending_team_leaves || 0) + (data.pending_team_claims || 0)} leave/claims · {data.pending_team_timesheets || 0} timesheets
            </p>
            {data.missing_billing ? <p className="mt-2 text-sm">{data.missing_billing} project(s) missing last month’s billing</p> : null}
          </Card>
        </Link>
      )}
      <Card className="md:col-span-3">
        <h3 className="font-display text-2xl">Leave balances</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {data?.leave_balances.map((b) => (
            <div key={b.leave_type_id} className="rounded-2xl bg-mist p-4">
              <p className="text-sm text-ink/60">{b.leave_type_name}</p>
              <p className="font-display text-3xl">{b.available}</p>
              <p className="text-xs">used {b.used} · pending {b.pending}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
