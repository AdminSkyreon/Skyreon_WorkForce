"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Reimbursement } from "@/lib/types";

const tone = { submitted: "warn", approved: "good", rejected: "bad", cancelled: "default" } as const;

export default function AdminReimbursementsPage() {
  const qc = useQueryClient();
  const [comments, setComments] = useState<Record<string, string>>({});
  const claims = useQuery({ queryKey: ["admin-claims"], queryFn: () => api<Reimbursement[]>("/reimbursements") });
  const review = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment: string }) =>
      api(`/reimbursements/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-claims"] }),
  });

  return (
    <div className="space-y-4">
      {claims.data?.map((claim) => (
        <Card key={claim.id}>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold">{claim.employee_name}</p>
              <p className="text-sm text-ink/60">{claim.category} · {claim.spend_date} · {claim.amount}</p>
              {claim.note ? <p className="mt-1 text-sm">{claim.note}</p> : null}
            </div>
            <Badge tone={tone[claim.status]}>{claim.status}</Badge>
          </div>
            {claim.status === "approved" && !claim.paid_separately && (
              <Button
                className="mt-3"
                variant="outline"
                onClick={() => api(`/reimbursements/${claim.id}/paid`, { method: "POST" }).then(() => qc.invalidateQueries({ queryKey: ["admin-claims"] }))}
              >
                Paid separately
              </Button>
            )}
            {claim.paid_separately && <p className="mt-2 text-xs text-forest">Paid outside payroll</p>}
            {claim.status === "submitted" && (
            <>
              <Textarea className="mt-3" placeholder="Comment" value={comments[claim.id] || ""} onChange={(e) => setComments((p) => ({ ...p, [claim.id]: e.target.value }))} />
              <div className="mt-3 flex gap-2">
                <Button onClick={() => review.mutate({ id: claim.id, action: "approve", comment: comments[claim.id] || "" })}>Approve</Button>
                <Button variant="danger" onClick={() => review.mutate({ id: claim.id, action: "reject", comment: comments[claim.id] || "" })}>Reject</Button>
              </div>
            </>
          )}
        </Card>
      ))}
      {!claims.data?.length && <Card>No reimbursement claims.</Card>}
    </div>
  );
}
