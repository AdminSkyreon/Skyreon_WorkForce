"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { MonthPicker, money } from "@/components/period";
import { Badge, Button, Card } from "@/components/ui";
import { api, downloadPdf } from "@/lib/api";
import type { ContractorRegister } from "@/lib/types";

export default function ContractorsPage() {
  const now = new Date();
  const qc = useQueryClient();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const register = useQuery({
    queryKey: ["contractors", year, month],
    queryFn: () => api<ContractorRegister>(`/contractors?year=${year}&month=${month}`),
  });
  const pay = useMutation({
    mutationFn: (employeeId: string) =>
      api(`/employees/${employeeId}/contractor-paid`, {
        method: "POST",
        body: JSON.stringify({
          year: Number(year),
          month: Number(month),
          paid_date: new Date().toISOString().slice(0, 10),
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contractors"] }),
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/60">Contractor pay is a separate register from staff payroll. Hours do not change a fixed monthly fee.</p>
      <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Hours</th>
              <th className="px-4 py-3">Calculated</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {register.data?.lines.map((line) => (
              <tr key={line.employee_id} className="border-t border-ink/5">
                <td className="px-4 py-3">
                  <p className="font-semibold">{line.name}</p>
                  <p className="text-xs text-ink/50">{line.employee_code}</p>
                </td>
                <td className="px-4 py-3">{line.hours}</td>
                <td className="px-4 py-3">{money(line.calculated)}</td>
                <td className="px-4 py-3">
                  <Badge tone={line.paid ? "good" : "warn"}>{line.paid ? "Paid" : "Calculated"}</Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  {line.paid ? (
                    <Button
                      variant="ghost"
                      onClick={() =>
                        downloadPdf(
                          `/employees/${line.employee_id}/contractor-statement?year=${year}&month=${month}`,
                          `contractor-${line.employee_code}.pdf`,
                        )
                      }
                    >
                      Statement
                    </Button>
                  ) : (
                    <Button onClick={() => pay.mutate(line.employee_id)}>Mark paid</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
