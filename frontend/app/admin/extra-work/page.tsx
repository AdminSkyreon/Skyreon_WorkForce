"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { ExtraWorkDay, ExtraWorkDefaults } from "@/lib/types";
import { labels } from "@/lib/utils";

export default function AdminExtraWorkPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"pending" | "approved" | "rejected" | "">("pending");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [settlement, setSettlement] = useState<"comp_off" | "extra_pay">("comp_off");
  const [compDays, setCompDays] = useState("");
  const [payAmount, setPayAmount] = useState("");
  const [comment, setComment] = useState("");
  const [rejectId, setRejectId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState("");

  const queryKey = ["extra-work", filter];
  const rows = useQuery({
    queryKey,
    queryFn: () => api<ExtraWorkDay[]>(`/extra-work${filter ? `?status=${filter}` : ""}`),
  });

  const defaults = useQuery({
    queryKey: ["extra-work-defaults", activeId],
    queryFn: () => api<ExtraWorkDefaults>(`/extra-work/${activeId}/defaults`),
    enabled: Boolean(activeId),
  });

  const approve = useMutation({
    mutationFn: () =>
      api(`/extra-work/${activeId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          settlement,
          comp_off_days: settlement === "comp_off" ? compDays || undefined : undefined,
          extra_pay_amount: settlement === "extra_pay" ? payAmount || undefined : undefined,
          comment,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["extra-work"] });
      setActiveId(null);
      setComment("");
    },
  });

  const reject = useMutation({
    mutationFn: () =>
      api(`/extra-work/${rejectId}/reject`, {
        method: "POST",
        body: JSON.stringify({ comment: rejectComment }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["extra-work"] });
      setRejectId(null);
      setRejectComment("");
    },
  });

  function openApprove(row: ExtraWorkDay) {
    setActiveId(row.id);
    setSettlement("comp_off");
    setCompDays("");
    setPayAmount("");
    setComment("");
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/60">
        Weekend or holiday hours from submitted timesheets appear here. Choose comp-off credit or extra pay for payroll.
      </p>
      <Select value={filter} onChange={(e) => setFilter(e.target.value as typeof filter)} className="max-w-xs">
        <option value="pending">Pending</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="">All</option>
      </Select>
      <div className="space-y-3">
        {rows.data?.map((row) => (
          <Card key={row.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-display text-2xl">{row.employee_name}</h3>
                <p className="text-sm text-ink/60">
                  {row.work_date} · {row.hours}h · {row.kind === "holiday" ? "Holiday" : "Weekend"}
                </p>
                {row.settlement ? (
                  <p className="mt-1 text-sm">
                    Settled as {row.settlement === "comp_off" ? `${row.comp_off_days} comp-off day(s)` : `₹${row.extra_pay_amount} extra pay`}
                  </p>
                ) : null}
              </div>
              <Badge tone={row.status === "approved" ? "good" : row.status === "rejected" ? "bad" : "warn"}>
                {labels.leave[row.status] ?? row.status}
              </Badge>
            </div>
            {row.status === "pending" && (
              <div className="mt-4 flex gap-2">
                <Button onClick={() => openApprove(row)}>Settle</Button>
                <Button variant="danger" onClick={() => setRejectId(row.id)}>
                  Reject
                </Button>
              </div>
            )}
          </Card>
        ))}
        {!rows.data?.length && <p className="text-sm text-ink/50">No extra-work items in this view.</p>}
      </div>

      <Modal open={Boolean(activeId)} onClose={() => setActiveId(null)} title="Settle extra work">
        {defaults.data ? (
          <div className="space-y-3">
            <div>
              <Label>Settlement</Label>
              <Select value={settlement} onChange={(e) => setSettlement(e.target.value as typeof settlement)}>
                <option value="comp_off">Comp-off ({defaults.data.comp_off_days} days suggested)</option>
                <option value="extra_pay">Extra pay ({defaults.data.extra_pay_amount} suggested)</option>
              </Select>
            </div>
            {settlement === "comp_off" ? (
              <div>
                <Label>Comp-off days</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  value={compDays}
                  placeholder={defaults.data.comp_off_days}
                  onChange={(e) => setCompDays(e.target.value)}
                />
              </div>
            ) : (
              <div>
                <Label>Extra pay amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={payAmount}
                  placeholder={defaults.data.extra_pay_amount}
                  onChange={(e) => setPayAmount(e.target.value)}
                />
              </div>
            )}
            <div>
              <Label>Comment</Label>
              <Textarea value={comment} onChange={(e) => setComment(e.target.value)} />
            </div>
            <Button onClick={() => approve.mutate()} disabled={approve.isPending}>
              Approve
            </Button>
          </div>
        ) : (
          <p className="text-sm text-ink/50">Loading suggested amounts…</p>
        )}
      </Modal>

      <Modal open={Boolean(rejectId)} onClose={() => setRejectId(null)} title="Reject extra work">
        <div className="space-y-3">
          <Textarea placeholder="Reason" value={rejectComment} onChange={(e) => setRejectComment(e.target.value)} />
          <Button variant="danger" onClick={() => reject.mutate()} disabled={reject.isPending}>
            Reject
          </Button>
        </div>
      </Modal>
    </div>
  );
}
