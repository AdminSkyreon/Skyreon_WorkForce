"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Card, Input } from "@/components/ui";
import { api } from "@/lib/api";
import type { AuditRow } from "@/lib/types";

export default function AuditPage() {
  const [actor, setActor] = useState("");
  const rows = useQuery({
    queryKey: ["audit", actor],
    queryFn: () => api<AuditRow[]>(`/super/audit?actor=${encodeURIComponent(actor)}`),
  });

  return (
    <div className="space-y-4">
      <Input placeholder="Filter by email" value={actor} onChange={(e) => setActor(e.target.value)} className="max-w-sm" />
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase text-ink/60">
            <tr>
              <th className="px-4 py-3">When</th>
              <th className="px-4 py-3">Who</th>
              <th className="px-4 py-3">Action</th>
              <th className="px-4 py-3">What</th>
              <th className="px-4 py-3">Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.data?.map((row) => (
              <tr key={row.id} className="border-t border-ink/5 align-top">
                <td className="px-4 py-3 whitespace-nowrap">{new Date(row.created_at).toLocaleString()}</td>
                <td className="px-4 py-3">{row.actor_email}<br /><span className="text-xs text-ink/50">{row.actor_role}</span></td>
                <td className="px-4 py-3">{row.action}</td>
                <td className="px-4 py-3">{row.entity_type} {row.summary}</td>
                <td className="px-4 py-3 text-xs">
                  {row.before_json && <div>before: {row.before_json}</div>}
                  {row.after_json && <div>after: {row.after_json}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
