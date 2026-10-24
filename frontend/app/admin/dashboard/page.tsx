"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { AdminDashboard } from "@/lib/types";

export default function AdminDashboardPage() {
  const { data } = useQuery({
    queryKey: ["admin-dashboard"],
    queryFn: () => api<AdminDashboard>("/admin/dashboard"),
  });

  const stats = [
    ["Active employees", data?.active_employees ?? "—", "/admin/employees"],
    ["Active projects", data?.active_projects ?? "—", "/admin/projects"],
    ["Pending timesheets", data?.pending_timesheets ?? "—", "/admin/timesheets"],
    ["Pending leave", data?.pending_leaves ?? "—", "/admin/leave"],
    ["Hours this week", data?.hours_this_week ?? "—", "/admin/timesheets"],
    ["Cost this week", data?.cost_this_week ?? "—", "/admin/payroll"],
    ["Pending claims", data?.pending_claims ?? "—", "/admin/reimbursements"],
    ["Missing billing", data?.missing_billing ?? "—", "/admin/billing"],
    ["Company month", "Cash", "/admin/company-month"],
  ] as const;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        {stats.map(([label, value, href]) => (
          <Link key={label} href={href}>
            <Card>
              <p className="text-xs uppercase tracking-widest text-ink/50">{label}</p>
              <p className="mt-3 font-display text-4xl">{value}</p>
            </Card>
          </Link>
        ))}
      </div>
      <Card>
        <h3 className="font-display text-2xl">Project cost vs revenue</h3>
        <div className="mt-6 h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data?.project_financials ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#d5e4f0" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="cost" fill="#081020" />
              <Bar dataKey="revenue" fill="#0060a8" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}
