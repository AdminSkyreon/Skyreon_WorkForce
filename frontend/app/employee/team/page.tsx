"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Employee, LeaveRequest, Reimbursement } from "@/lib/types";
import { useState } from "react";

export default function MyTeamPage() {
  const qc = useQueryClient();
  const [comments, setComments] = useState<Record<string, string>>({});
  const team = useQuery({ queryKey: ["my-team"], queryFn: () => api<Employee[]>("/me/team") });
  const leave = useQuery({ queryKey: ["team-leave"], queryFn: () => api<LeaveRequest[]>("/leave") });
  const claims = useQuery({ queryKey: ["team-claims"], queryFn: () => api<Reimbursement[]>("/reimbursements") });
  const reviewLeave = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment: string }) =>
      api(`/leave/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team-leave"] }),
  });
  const reviewClaim = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment: string }) =>
      api(`/reimbursements/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team-claims"] }),
  });

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="font-display text-2xl">Direct reports</h3>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {team.data?.map((emp) => (
            <div key={emp.id} className="rounded-2xl bg-mist p-4">
              <p className="font-semibold">{emp.name}</p>
              <p className="text-sm text-ink/60">{emp.designation} · {emp.employee_code}</p>
            </div>
          ))}
          {!team.data?.length && <p className="text-sm text-ink/50">No direct reports.</p>}
        </div>
      </Card>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-3">
          <h3 className="font-display text-2xl">Leave to approve</h3>
          {leave.data?.filter((r) => r.status === "pending").map((req) => (
            <Card key={req.id}>
              <p className="font-semibold">{req.employee_name}</p>
              <p className="text-sm text-ink/60">{req.leave_type_name} · {req.start_date} → {req.end_date}</p>
              <Textarea className="mt-3" placeholder="Comment" value={comments[req.id] || ""} onChange={(e) => setComments((p) => ({ ...p, [req.id]: e.target.value }))} />
              <div className="mt-3 flex gap-2">
                <Button
                  loading={reviewLeave.isPending && reviewLeave.variables?.id === req.id && reviewLeave.variables?.action === "approve"}
                  onClick={() => reviewLeave.mutate({ id: req.id, action: "approve", comment: comments[req.id] || "" })}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  loading={reviewLeave.isPending && reviewLeave.variables?.id === req.id && reviewLeave.variables?.action === "reject"}
                  onClick={() => reviewLeave.mutate({ id: req.id, action: "reject", comment: comments[req.id] || "" })}
                >
                  Reject
                </Button>
              </div>
            </Card>
          ))}
        </div>
        <div className="space-y-3">
          <h3 className="font-display text-2xl">Claims to approve</h3>
          {claims.data?.filter((c) => c.status === "submitted").map((claim) => (
            <Card key={claim.id}>
              <div className="flex justify-between">
                <p className="font-semibold">{claim.employee_name}</p>
                <Badge tone="warn">{claim.amount}</Badge>
              </div>
              <p className="text-sm text-ink/60">{claim.category} · {claim.spend_date}</p>
              <Textarea className="mt-3" placeholder="Comment" value={comments[claim.id] || ""} onChange={(e) => setComments((p) => ({ ...p, [claim.id]: e.target.value }))} />
              <div className="mt-3 flex gap-2">
                <Button
                  loading={reviewClaim.isPending && reviewClaim.variables?.id === claim.id && reviewClaim.variables?.action === "approve"}
                  onClick={() => reviewClaim.mutate({ id: claim.id, action: "approve", comment: comments[claim.id] || "" })}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  loading={reviewClaim.isPending && reviewClaim.variables?.id === claim.id && reviewClaim.variables?.action === "reject"}
                  onClick={() => reviewClaim.mutate({ id: claim.id, action: "reject", comment: comments[claim.id] || "" })}
                >
                  Reject
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
