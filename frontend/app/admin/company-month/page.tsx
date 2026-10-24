"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { MonthPicker, money } from "@/components/period";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { CompanyMonth } from "@/lib/types";

export default function CompanyMonthPage() {
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const { data } = useQuery({
    queryKey: ["company-month", year, month],
    queryFn: () => api<CompanyMonth>(`/company/month?year=${year}&month=${month}`),
  });
  const cash = [
    ["Received", data?.received],
    ["Staff paid", data?.staff_paid],
    ["Contractors paid", data?.contractors_paid],
    ["Claims paid separately", data?.claims_paid],
    ["GST / CA / legal", data?.compliance],
    ["Other opex", data?.other_opex],
    ["Leftover", data?.leftover],
  ] as const;
  const notCash = [
    ["Invoiced (not cash)", data?.invoiced_not_cash],
    ["Salaries calculated", data?.salaries_calculated],
    ["Contractors calculated", data?.contractors_calculated],
  ] as const;

  return (
    <div className="space-y-6">
      <p className="max-w-2xl text-sm text-ink/60">
        Cash view for the company month. Invoice and calculated payroll stay separate until money actually moves.
      </p>
      <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
      <p className="font-display text-3xl">{data?.period_label}</p>
      <div className="grid gap-4 md:grid-cols-3">
        {cash.map(([label, value]) => (
          <Card key={label}>
            <p className="text-xs uppercase tracking-widest text-ink/50">{label}</p>
            <p className="mt-3 font-display text-4xl">{money(value)}</p>
          </Card>
        ))}
      </div>
      <Card>
        <p className="text-xs uppercase tracking-widest text-copper">Not cash yet</p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {notCash.map(([label, value]) => (
            <div key={label}>
              <p className="text-sm text-ink/50">{label}</p>
              <p className="font-display text-2xl">{money(value)}</p>
            </div>
          ))}
        </div>
        {Number(data?.receipts_against_earlier || 0) > 0 ? (
          <p className="mt-4 text-sm text-ink/60">
            Of this month’s receipts, {money(data?.receipts_against_earlier)} is against earlier invoices.
          </p>
        ) : null}
      </Card>
    </div>
  );
}
