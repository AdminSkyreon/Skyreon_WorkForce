"use client";

import { useQuery } from "@tanstack/react-query";
import { Badge, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { EmployeeDocument } from "@/lib/types";

export default function MyDocumentsPage() {
  const { data } = useQuery({ queryKey: ["my-docs"], queryFn: () => api<EmployeeDocument[]>("/me/documents") });
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink/60">Your joining checklist. Admin marks items as collected.</p>
      {data?.map((row) => (
        <Card key={row.requirement_id} className="flex items-center justify-between">
          <p className="font-semibold">{row.name}</p>
          <Badge tone={row.provided ? "good" : "warn"}>{row.provided ? "Collected" : "Pending"}</Badge>
        </Card>
      ))}
    </div>
  );
}
