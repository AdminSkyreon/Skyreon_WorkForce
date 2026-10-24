"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Download } from "lucide-react";
import { Fragment, useState } from "react";
import { money, MonthPicker } from "@/components/period";
import { Button, Card, Select } from "@/components/ui";
import { api, downloadPdf } from "@/lib/api";
import type { FinanceMonth, FinanceYear } from "@/lib/types";

export default function FinancePage() {
  const now = new Date();
  const [view, setView] = useState<"year" | "month">("year");
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [open, setOpen] = useState<Record<string, boolean>>({});

  const yearReport = useQuery({
    queryKey: ["finance-year", year],
    queryFn: () => api<FinanceYear>(`/super/finance/year?year=${year}`),
    enabled: view === "year",
    placeholderData: (prev) => prev,
  });
  const monthReport = useQuery({
    queryKey: ["finance-month", year, month],
    queryFn: () => api<FinanceMonth>(`/super/finance?year=${year}&month=${month}`),
    enabled: view === "month",
    placeholderData: (prev) => prev,
  });

  const report = yearReport.data;
  const monthData = monthReport.data;
  const isFetching =
    (view === "year" && yearReport.isFetching && !yearReport.isLoading) ||
    (view === "month" && monthReport.isFetching && !monthReport.isLoading);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-ink/60">
          Year view groups invoiced work by project manager. Invoiced uses invoice date, received uses cash date, profit is invoiced minus time-cost.
        </p>
        <div className="flex rounded-full bg-mist p-1 text-sm font-semibold">
          <button
            type="button"
            className={`rounded-full px-4 py-1.5 ${view === "year" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
            onClick={() => setView("year")}
          >
            Year
          </button>
          <button
            type="button"
            className={`rounded-full px-4 py-1.5 ${view === "month" ? "bg-white text-ink shadow-sm" : "text-ink/60"}`}
            onClick={() => setView("month")}
          >
            This month
          </button>
        </div>
      </div>

      {isFetching ? <p className="text-xs text-ink/50">Updating report…</p> : null}

      {view === "year" ? (
        <div className={isFetching ? "space-y-6 opacity-70" : "space-y-6"}>
          <div className="flex flex-wrap items-end gap-3">
            <Select value={year} onChange={(e) => setYear(e.target.value)} className="max-w-40">
              {[now.getFullYear(), now.getFullYear() - 1, now.getFullYear() - 2].map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </Select>
            <Button
              variant="outline"
              onClick={() => downloadPdf(`/super/finance/year.pdf?year=${year}`, `finance-${year}.pdf`)}
            >
              <Download className="h-4 w-4" />
              Download year PDF
            </Button>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {[
              ["Invoiced", report?.invoiced],
              ["Received", report?.received],
              ["Cost", report?.cost],
              ["Profit", report?.profit],
            ].map(([label, value]) => (
              <Card key={label}>
                <p className="text-xs uppercase tracking-widest text-ink/50">{label}</p>
                <p className="mt-3 font-display text-4xl">{report ? money(value) : "—"}</p>
              </Card>
            ))}
          </div>
          <p className="text-sm text-ink/70">
            Company cash leftover for {year}: <span className="font-semibold">{report ? money(report.cash_leftover) : "—"}</span>
          </p>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="bg-mist text-xs uppercase text-ink/60">
                <tr>
                  <th className="px-4 py-3">Manager / project</th>
                  <th className="px-4 py-3">Client</th>
                  <th className="px-4 py-3 text-right">Invoiced</th>
                  <th className="px-4 py-3 text-right">Received</th>
                  <th className="px-4 py-3 text-right">Cost</th>
                  <th className="px-4 py-3 text-right">Profit</th>
                </tr>
              </thead>
              <tbody>
                {(report?.managers ?? []).map((manager) => {
                  const key = manager.manager_id ?? "unassigned";
                  const expanded = open[key] ?? false;
                  return (
                    <Fragment key={key}>
                      <tr className="border-t border-ink/5 bg-white">
                        <td className="px-4 py-3 font-semibold">
                          <button
                            type="button"
                            className="inline-flex items-center gap-2"
                            onClick={() => setOpen((current) => ({ ...current, [key]: !expanded }))}
                          >
                            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                            {manager.manager_name}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-ink/50">{manager.projects.length} project{manager.projects.length === 1 ? "" : "s"}</td>
                        <td className="px-4 py-3 text-right">{money(manager.invoiced)}</td>
                        <td className="px-4 py-3 text-right">{money(manager.received)}</td>
                        <td className="px-4 py-3 text-right">{money(manager.cost)}</td>
                        <td className="px-4 py-3 text-right">{money(manager.profit)}</td>
                      </tr>
                      {expanded
                        ? manager.projects.map((project) => (
                            <tr key={project.project_id} className="border-t border-ink/5 bg-mist/40">
                              <td className="px-4 py-2 pl-12">{project.project_name}</td>
                              <td className="px-4 py-2">{project.client_name || "—"}</td>
                              <td className="px-4 py-2 text-right">{money(project.invoiced)}</td>
                              <td className="px-4 py-2 text-right">{money(project.received)}</td>
                              <td className="px-4 py-2 text-right">{money(project.cost)}</td>
                              <td className="px-4 py-2 text-right">{money(project.profit)}</td>
                            </tr>
                          ))
                        : null}
                    </Fragment>
                  );
                })}
                {!report?.managers.length ? (
                  <tr>
                    <td className="px-4 py-6 text-ink/50" colSpan={6}>
                      No started projects in this year.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </Card>
          <Card className="overflow-x-auto p-0">
            <p className="px-4 pt-4 text-xs uppercase tracking-widest text-ink/50">Month by month</p>
            <table className="mt-2 w-full text-left text-sm">
              <thead className="text-xs uppercase text-ink/60">
                <tr>
                  <th className="px-4 py-2">Month</th>
                  <th className="px-4 py-2 text-right">Invoiced</th>
                  <th className="px-4 py-2 text-right">Received</th>
                  <th className="px-4 py-2 text-right">Cost</th>
                  <th className="px-4 py-2 text-right">Profit</th>
                </tr>
              </thead>
              <tbody>
                {(report?.months ?? []).map((row) => (
                  <tr key={row.month} className="border-t border-ink/5">
                    <td className="px-4 py-2">{row.label}</td>
                    <td className="px-4 py-2 text-right">{money(row.invoiced)}</td>
                    <td className="px-4 py-2 text-right">{money(row.received)}</td>
                    <td className="px-4 py-2 text-right">{money(row.cost)}</td>
                    <td className="px-4 py-2 text-right">{money(row.profit)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      ) : (
        <div className={isFetching ? "space-y-6 opacity-70" : "space-y-6"}>
          <p className="text-sm text-ink/60">Projects that have started by the end of this month. Revenue is invoices dated in the month; none is 0.00.</p>
          <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <p className="text-xs uppercase tracking-widest text-ink/50">Revenue</p>
              <p className="mt-3 font-display text-4xl">{monthData ? money(monthData.total_billing) : "—"}</p>
            </Card>
            <Card>
              <p className="text-xs uppercase tracking-widest text-ink/50">Cost</p>
              <p className="mt-3 font-display text-4xl">{monthData ? money(monthData.total_cost) : "—"}</p>
            </Card>
            <Card>
              <p className="text-xs uppercase tracking-widest text-ink/50">Profit</p>
              <p className="mt-3 font-display text-4xl">{monthData ? money(monthData.total_margin) : "—"}</p>
            </Card>
          </div>
          <Card className="overflow-x-auto p-0">
            <table className="w-full text-left text-sm">
              <thead className="bg-mist text-xs uppercase text-ink/60">
                <tr>
                  <th className="px-4 py-3">Project</th>
                  <th className="px-4 py-3">Manager</th>
                  <th className="px-4 py-3 text-right">Revenue</th>
                  <th className="px-4 py-3 text-right">Cost</th>
                  <th className="px-4 py-3 text-right">Profit</th>
                </tr>
              </thead>
              <tbody>
                {monthData?.projects.map((row) => (
                  <tr key={row.project_id} className="border-t border-ink/5">
                    <td className="px-4 py-3">{row.project_name}</td>
                    <td className="px-4 py-3">{row.manager_name || "Unassigned"}</td>
                    <td className="px-4 py-3 text-right">{money(row.billing)}</td>
                    <td className="px-4 py-3 text-right">{money(row.cost)}</td>
                    <td className="px-4 py-3 text-right">{money(row.margin)}</td>
                  </tr>
                ))}
                {!monthData?.projects.length ? (
                  <tr>
                    <td className="px-4 py-6 text-ink/50" colSpan={5}>
                      No started projects in this month.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </Card>
        </div>
      )}
    </div>
  );
}
