"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Project, Reimbursement } from "@/lib/types";

const tone = { submitted: "warn", approved: "good", rejected: "bad", cancelled: "default" } as const;

export default function EmployeeReimbursementsPage() {
  const qc = useQueryClient();
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("travel");
  const [spendDate, setSpendDate] = useState("");
  const [note, setNote] = useState("");
  const [projectId, setProjectId] = useState("");
  const claims = useQuery({ queryKey: ["my-claims"], queryFn: () => api<Reimbursement[]>("/me/reimbursements") });
  const projects = useQuery({ queryKey: ["my-projects"], queryFn: () => api<Project[]>("/me/projects") });
  const apply = useMutation({
    mutationFn: () =>
      api("/me/reimbursements", {
        method: "POST",
        body: JSON.stringify({
          amount,
          category,
          spend_date: spendDate,
          note,
          project_id: projectId || null,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["my-claims"] });
      setAmount("");
      setNote("");
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api(`/me/reimbursements/${id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-claims"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-4">
        {claims.data?.map((claim) => (
          <Card key={claim.id}>
            <div className="flex justify-between gap-3">
              <div>
                <h3 className="font-display text-2xl">{claim.amount}</h3>
                <p className="text-sm text-ink/60">
                  {claim.category} · {claim.spend_date}
                </p>
                {claim.note ? <p className="mt-2 text-sm">{claim.note}</p> : null}
              </div>
              <Badge tone={tone[claim.status]}>{claim.status}</Badge>
            </div>
            {claim.status === "submitted" && (
              <Button className="mt-3" variant="outline" onClick={() => cancel.mutate(claim.id)}>
                Cancel
              </Button>
            )}
          </Card>
        ))}
      </div>
      <Card>
        <h3 className="font-display text-2xl">New claim</h3>
        <div className="mt-4 space-y-3">
          <div>
            <Label>Amount</Label>
            <Input value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div>
            <Label>Category</Label>
            <Select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="travel">Travel</option>
              <option value="food">Food</option>
              <option value="internet">Internet</option>
              <option value="other">Other</option>
            </Select>
          </div>
          <div>
            <Label>Spend date</Label>
            <Input type="date" value={spendDate} onChange={(e) => setSpendDate(e.target.value)} />
          </div>
          <div>
            <Label>Project (optional)</Label>
            <Select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">None</option>
              {projects.data?.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Note</Label>
            <Textarea value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
          {apply.error ? <p className="text-sm text-red-700">{apply.error.message}</p> : null}
          <Button onClick={() => apply.mutate()} disabled={!amount || !spendDate || apply.isPending}>
            Submit claim
          </Button>
        </div>
      </Card>
    </div>
  );
}
