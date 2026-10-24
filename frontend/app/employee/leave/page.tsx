"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { LeaveBalance, LeaveRequest, LeaveType } from "@/lib/types";
import { labels } from "@/lib/utils";

export default function EmployeeLeavePage() {
  const qc = useQueryClient();
  const [leaveType, setLeaveType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [half, setHalf] = useState(false);
  const [reason, setReason] = useState("");

  const requests = useQuery({ queryKey: ["my-leave"], queryFn: () => api<LeaveRequest[]>("/me/leave") });
  const balances = useQuery({ queryKey: ["my-balances"], queryFn: () => api<LeaveBalance[]>("/me/leave/balances") });
  const types = useQuery({ queryKey: ["leave-types"], queryFn: () => api<LeaveType[]>("/leave-types") });

  const apply = useMutation({
    mutationFn: () =>
      api("/me/leave", {
        method: "POST",
        body: JSON.stringify({
          leave_type_id: leaveType,
          start_date: start,
          end_date: end || start,
          is_half_day: half,
          reason,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["my-leave"] });
      void qc.invalidateQueries({ queryKey: ["my-balances"] });
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api(`/me/leave/${id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-leave"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-4">
        {requests.data?.map((req) => (
          <Card key={req.id}>
            <div className="flex justify-between">
              <div>
                <h3 className="font-display text-2xl">{req.leave_type_name}</h3>
                <p className="text-sm text-ink/60">
                  {req.start_date} → {req.end_date} · {req.days} days
                </p>
              </div>
              <Badge tone={req.status === "approved" ? "good" : req.status === "rejected" ? "bad" : "warn"}>
                {labels.leave[req.status]}
              </Badge>
            </div>
            {req.status === "pending" && (
              <Button className="mt-3" variant="outline" onClick={() => cancel.mutate(req.id)}>
                Cancel
              </Button>
            )}
          </Card>
        ))}
      </div>
      <div className="space-y-4">
        <Card>
          <h3 className="font-display text-2xl">Balances</h3>
          <ul className="mt-3 space-y-2 text-sm">
            {balances.data?.map((b) => (
              <li key={b.leave_type_id} className="flex justify-between">
                <span>{b.leave_type_name}</span>
                <span>
                  {b.leave_type_name === "Comp Off"
                    ? `${b.available} comp-off`
                    : `${b.available} left (${b.allocated} earned YTD)`}
                </span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <h3 className="font-display text-2xl">Apply</h3>
          <div className="mt-3 space-y-3">
            <div>
              <Label>Type</Label>
              <Select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
                <option value="">Select</option>
                {types.data
                  ?.filter((t) => {
                    if (t.code !== "CO") return true;
                    const co = balances.data?.find((b) => b.leave_type_id === t.id);
                    return co && Number(co.available) > 0;
                  })
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
              </Select>
            </div>
            <div>
              <Label>Start</Label>
              <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div>
              <Label>End</Label>
              <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={half} onChange={(e) => setHalf(e.target.checked)} />
              Half day
            </label>
            <Textarea placeholder="Reason" value={reason} onChange={(e) => setReason(e.target.value)} />
            <Button onClick={() => apply.mutate()}>Submit request</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
