"use client";

import { useState } from "react";
import { Button, Card, Select } from "@/components/ui";
import { downloadPdf } from "@/lib/api";

export default function MyPayslipsPage() {
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [error, setError] = useState("");

  return (
    <Card className="max-w-xl">
      <h3 className="font-display text-2xl">My payslips</h3>
      <p className="mt-2 text-sm text-ink/60">Available after Admin closes that month.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Select value={year} onChange={(e) => setYear(e.target.value)}>
          {[now.getFullYear(), now.getFullYear() - 1].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </Select>
        <Select value={month} onChange={(e) => setMonth(e.target.value)}>
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i + 1} value={String(i + 1)}>
              {new Date(2000, i, 1).toLocaleString("en", { month: "long" })}
            </option>
          ))}
        </Select>
      </div>
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      <Button
        className="mt-4"
        onClick={() => {
          setError("");
          downloadPdf(`/me/payslips/${year}/${month}/pdf`, `payslip-${year}-${month.padStart(2, "0")}.pdf`).catch((err) =>
            setError(err instanceof Error ? err.message : "Payslip not available"),
          );
        }}
      >
        Open payslip PDF
      </Button>
    </Card>
  );
}
