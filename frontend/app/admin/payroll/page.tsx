"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { api, downloadPdf } from "@/lib/api";
import type { Location, PayrollDetails, PayrollRegister, SalaryPayment } from "@/lib/types";

const emptyForm = {
  currency: "INR",
  basic_salary: "0",
  hra: "0",
  allowances: "0",
  tax_percent: "0",
  pf_percent: "0",
  professional_tax: "0",
  hourly_pay_rate: "0",
  other_deductions: "0",
  bonus: "0",
};

export default function PayrollPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [locationId, setLocationId] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editPayType, setEditPayType] = useState<"fixed" | "hourly">("fixed");
  const [form, setForm] = useState(emptyForm);
  const [claimsAmount, setClaimsAmount] = useState("0.00");
  const query = useMemo(() => {
    const params = new URLSearchParams({ year, month });
    if (locationId) params.set("location_id", locationId);
    return params.toString();
  }, [year, month, locationId]);
  const locations = useQuery({ queryKey: ["locations-admin"], queryFn: () => api<Location[]>("/admin/locations") });
  const payroll = useQuery({
    queryKey: ["payroll", query],
    queryFn: () => api<PayrollRegister>(`/admin/payroll?${query}`),
  });
  const save = useMutation({
    mutationFn: () =>
      api(`/admin/payroll/details/${editId}?year=${year}&month=${month}`, {
        method: "PUT",
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["payroll"] });
      setEditId(null);
    },
  });
  const closeMonth = useMutation({
    mutationFn: () => api(`/admin/payroll/close?year=${year}&month=${month}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payroll"] }),
  });
  const reopenMonth = useMutation({
    mutationFn: () => api(`/admin/payroll/reopen?year=${year}&month=${month}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["payroll"] }),
  });
  const paid = useQuery({
    queryKey: ["salary-paid", year, month],
    queryFn: () => api<SalaryPayment[]>(`/salary-payments?year=${year}&month=${month}`),
  });
  const markPaid = useMutation({
    mutationFn: (employeeId: string) =>
      api(`/employees/${employeeId}/salary-paid`, {
        method: "POST",
        body: JSON.stringify({
          year: Number(year),
          month: Number(month),
          paid_date: new Date().toISOString().slice(0, 10),
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["salary-paid"] }),
  });
  const paidIds = new Set((paid.data ?? []).map((row) => row.employee_id));

  async function openDetails(employeeId: string, name: string, payType: "fixed" | "hourly" = "fixed") {
    const details = await api<PayrollDetails>(`/admin/payroll/details/${employeeId}?year=${year}&month=${month}`);
    setEditId(employeeId);
    setEditName(name);
    setEditPayType(payType);
    setForm({
      currency: details.currency,
      basic_salary: details.basic_salary,
      hra: details.hra,
      allowances: details.allowances,
      tax_percent: details.tax_percent,
      hourly_pay_rate: details.hourly_pay_rate || "0",
      pf_percent: details.pf_percent,
      professional_tax: details.professional_tax,
      other_deductions: details.other_deductions,
      bonus: details.bonus || "0",
    });
    setClaimsAmount(details.reimbursements || "0.00");
  }

  const data = payroll.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="max-w-2xl text-sm text-ink/60">
          Standing pay is set once (monthly salary for fixed, hourly rate for hourly). Bonus is for the
          selected month only. Close the month to freeze payslips.
          {data?.closed ? " This month is closed." : ""}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            onClick={() => downloadPdf(`/admin/payroll/pdf?${query}`, `payroll-${year}-${month.padStart(2, "0")}.pdf`)}
          >
            Open payroll PDF
          </Button>
          {!data?.closed && (
            <Button variant="outline" onClick={() => closeMonth.mutate()}>Close month</Button>
          )}
          {data?.closed && user?.role === "super_admin" && (
            <Button variant="outline" onClick={() => reopenMonth.mutate()}>Re-open month</Button>
          )}
        </div>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Input type="number" value={year} onChange={(e) => setYear(e.target.value)} />
        <Select value={month} onChange={(e) => setMonth(e.target.value)}>
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i + 1} value={String(i + 1)}>
              {new Date(2000, i, 1).toLocaleString("en", { month: "long" })}
            </option>
          ))}
        </Select>
        <Select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
          <option value="">All locations</option>
          {locations.data?.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </Select>
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase text-ink/60">
            <tr>
              <th className="px-4 py-3">Employee</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Bonus</th>
              <th className="px-4 py-3">Extra work</th>
              <th className="px-4 py-3">Reimbursement</th>
              <th className="px-4 py-3">Gross</th>
              <th className="px-4 py-3">Tax</th>
              <th className="px-4 py-3">Net</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.lines.map((line) => (
              <tr key={line.employee_id} className="border-t border-ink/5">
                <td className="px-4 py-3">
                  <p className="font-semibold">{line.name}</p>
                  <p className="text-xs text-ink/50">{line.employee_code}</p>
                </td>
                <td className="px-4 py-3">
                  {line.location_name || "—"}{" "}
                  {line.has_details ? <Badge tone="good">details set</Badge> : <Badge>needs details</Badge>}
                </td>
                <td className="px-4 py-3">{line.hours}</td>
                <td className="px-4 py-3">{line.bonus || "0.00"}</td>
                <td className="px-4 py-3">{line.extra_work_pay || "0.00"}</td>
                <td className="px-4 py-3">{line.reimbursements || "0.00"}</td>
                <td className="px-4 py-3">{line.gross_pay}</td>
                <td className="px-4 py-3">{line.tax_amount}</td>
                <td className="px-4 py-3 font-semibold">{line.net_pay}</td>
                <td className="px-4 py-3 text-right">
                  <Button variant="ghost" onClick={() => void openDetails(line.employee_id, line.name, line.pay_type)}>
                    Payroll details
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() =>
                      downloadPdf(
                        `/admin/payroll/${line.employee_id}/pdf?year=${year}&month=${month}`,
                        `payslip-${line.employee_code}-${year}-${month.padStart(2, "0")}.pdf`,
                      )
                    }
                  >
                    Payslip PDF
                  </Button>
                  {data?.closed && !paidIds.has(line.employee_id) && line.employee_id !== user?.employee_id && (
                    <Button variant="ghost" onClick={() => markPaid.mutate(line.employee_id)}>
                      Mark paid
                    </Button>
                  )}
                  {paidIds.has(line.employee_id) && <Badge tone="good">Paid</Badge>}
                </td>
              </tr>
            ))}
            {data ? (
              <tr className="border-t border-ink/10 font-semibold">
                <td className="px-4 py-3" colSpan={2}>
                  {data.period_label} total
                </td>
                <td className="px-4 py-3">{data.total_hours}</td>
                <td className="px-4 py-3">
                  {data.lines.reduce((sum, line) => sum + Number(line.bonus || 0), 0).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  {data.lines.reduce((sum, line) => sum + Number(line.extra_work_pay || 0), 0).toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  {data.lines.reduce((sum, line) => sum + Number(line.reimbursements || 0), 0).toFixed(2)}
                </td>
                <td className="px-4 py-3">{data.total_gross}</td>
                <td className="px-4 py-3">{data.total_tax}</td>
                <td className="px-4 py-3">{data.total_pay}</td>
                <td />
              </tr>
            ) : null}
          </tbody>
        </table>
      </Card>

      <Modal open={!!editId} title={`Payroll details · ${editName}`} onClose={() => setEditId(null)}>
        <p className="mb-3 text-sm text-ink/60">
          {editPayType === "hourly"
            ? "Take-home = (approved hours × hourly rate) + paid leave + this month’s bonus + claims − tax/PF."
            : "Take-home = monthly salary (basic + HRA + allowances) − unpaid leave + this month’s bonus + claims − tax/PF. Hours do not change fixed pay."}
        </p>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/50">Every month</p>
        <div className="grid gap-3 md:grid-cols-2">
          {(
            (
              editPayType === "hourly"
                ? ([
                    ["currency", "Currency"],
                    ["hourly_pay_rate", "Hourly pay rate"],
                    ["tax_percent", "Tax %"],
                    ["pf_percent", "PF %"],
                    ["professional_tax", "Professional tax"],
                    ["other_deductions", "Other deductions"],
                  ] as const)
                : ([
                    ["currency", "Currency"],
                    ["basic_salary", "Monthly salary / basic"],
                    ["hra", "HRA"],
                    ["allowances", "Allowances"],
                    ["tax_percent", "Tax %"],
                    ["pf_percent", "PF %"],
                    ["professional_tax", "Professional tax"],
                    ["other_deductions", "Other deductions"],
                  ] as const)
            )
          ).map(([key, label]) => (
            <div key={key}>
              <Label>{label}</Label>
              <Input value={form[key]} onChange={(e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))} />
            </div>
          ))}
        </div>
        <p className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-ink/50">This month only</p>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>Bonus</Label>
            <Input value={form.bonus} onChange={(e) => setForm((prev) => ({ ...prev, bonus: e.target.value }))} />
            <p className="mt-1 text-xs text-ink/50">Leave 0 if there is no bonus this month. It does not carry to the next month.</p>
          </div>
          <div>
            <Label>Reimbursement</Label>
            <Input value={claimsAmount} readOnly className="bg-mist" />
            <p className="mt-1 text-xs text-ink/50">Approved claims for this month that are paid with salary. Change them on Claims.</p>
          </div>
        </div>
        {save.error ? <p className="mt-2 text-sm text-red-700">{save.error.message}</p> : null}
        <Button className="mt-4" disabled={save.isPending || data?.closed} onClick={() => save.mutate()}>
          Save payroll details
        </Button>
      </Modal>
    </div>
  );
}
