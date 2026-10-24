"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Employee, EmployeeDocument, Page } from "@/lib/types";

export default function DocumentsPage() {
  const qc = useQueryClient();
  const [employeeId, setEmployeeId] = useState("");
  const people = useQuery({
    queryKey: ["employees", "docs"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });
  const docs = useQuery({
    queryKey: ["docs", employeeId],
    queryFn: () => api<EmployeeDocument[]>(`/employees/${employeeId}/documents`),
    enabled: Boolean(employeeId),
  });
  const toggle = useMutation({
    mutationFn: (row: EmployeeDocument) =>
      api(`/employees/${employeeId}/documents/${row.requirement_id}?provided=${!row.provided}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["docs", employeeId] }),
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/60">Joining checklist. Tick what has been collected — files stay outside the portal.</p>
      <Select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
        <option value="">Choose a person</option>
        {people.data?.items.map((emp) => (
          <option key={emp.id} value={emp.id}>
            {emp.name}
          </option>
        ))}
      </Select>
      {docs.data?.map((row) => (
        <Card key={row.requirement_id} className="flex items-center justify-between">
          <div>
            <p className="font-semibold">{row.name}</p>
            <Badge tone={row.provided ? "good" : "warn"}>{row.provided ? "Collected" : "Missing"}</Badge>
          </div>
          <Button variant="outline" onClick={() => toggle.mutate(row)}>
            {row.provided ? "Mark missing" : "Collected"}
          </Button>
        </Card>
      ))}
    </div>
  );
}
