"use client";

import { Select } from "@/components/ui";

export function MonthPicker({
  year,
  month,
  onYear,
  onMonth,
}: {
  year: string;
  month: string;
  onYear: (value: string) => void;
  onMonth: (value: string) => void;
}) {
  const now = new Date();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <Select value={year} onChange={(e) => onYear(e.target.value)}>
        {[now.getFullYear(), now.getFullYear() - 1].map((value) => (
          <option key={value} value={value}>
            {value}
          </option>
        ))}
      </Select>
      <Select value={month} onChange={(e) => onMonth(e.target.value)}>
        {Array.from({ length: 12 }, (_, i) => (
          <option key={i + 1} value={String(i + 1)}>
            {new Date(2000, i, 1).toLocaleString("en", { month: "long" })}
          </option>
        ))}
      </Select>
    </div>
  );
}

export function money(value?: string | number | null) {
  const amount = Number(value || 0);
  return amount.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
