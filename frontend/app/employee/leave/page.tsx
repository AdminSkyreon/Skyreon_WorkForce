"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, subDays } from "date-fns";
import { useState } from "react";
import { Badge, Button, Card, FieldError, Input, Label, Select, Textarea } from "@/components/ui";
import { toast } from "@/components/toast";
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
  const [submitted, setSubmitted] = useState(false);

  const requests = useQuery({ queryKey: ["my-leave"], queryFn: () => api<LeaveRequest[]>("/me/leave") });
  const balances = useQuery({ queryKey: ["my-balances"], queryFn: () => api<LeaveBalance[]>("/me/leave/balances") });
  const types = useQuery({ queryKey: ["leave-types"], queryFn: () => api<LeaveType[]>("/leave-types") });

  const minDate = format(subDays(new Date(), 7), "yyyy-MM-dd");
  const effectiveEnd = half ? start : end || start;
  const errors = {
    leaveType: !leaveType ? "Select a leave type" : "",
    start: !start
      ? "Start date is required"
      : start < minDate
        ? "Cannot apply leave more than 7 days in the past"
        : "",
    end:
      start && effectiveEnd && effectiveEnd < start
        ? "End date cannot be earlier than start date"
        : half && start && effectiveEnd !== start
          ? "Half-day leave must be a single date"
          : "",
  };
  const hasErrors = Object.values(errors).some(Boolean);

  const apply = useMutation({
    mutationFn: () =>
      api("/me/leave", {
        method: "POST",
        body: JSON.stringify({
          leave_type_id: leaveType,
          start_date: start,
          end_date: effectiveEnd,
          is_half_day: half,
          reason: reason.trim(),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["my-leave"] });
      void qc.invalidateQueries({ queryKey: ["my-balances"] });
      setLeaveType("");
      setStart("");
      setEnd("");
      setHalf(false);
      setReason("");
      setSubmitted(false);
      toast.success("Leave request submitted");
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => api(`/me/leave/${id}/cancel`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["my-leave"] });
      void qc.invalidateQueries({ queryKey: ["my-balances"] });
      toast.success("Leave request cancelled");
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <div className="space-y-4">
        {cancel.error ? <p className="text-sm text-red-700">{cancel.error.message}</p> : null}
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
              <Button
                className="mt-3"
                variant="outline"
                disabled={cancel.isPending}
                loading={cancel.isPending && cancel.variables === req.id}
                onClick={() => cancel.mutate(req.id)}
              >
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
              <Select disabled={apply.isPending} value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
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
              {submitted && <FieldError message={errors.leaveType} />}
            </div>
            <div>
              <Label>Start</Label>
              <Input
                type="date"
                min={minDate}
                disabled={apply.isPending}
                value={start}
                onChange={(e) => {
                  const nextStart = e.target.value;
                  setStart(nextStart);
                  if (half || (end && nextStart && end < nextStart)) {
                    setEnd(nextStart);
                  }
                }}
              />
              {submitted && <FieldError message={errors.start} />}
            </div>
            <div>
              <Label>End</Label>
              <Input
                type="date"
                min={start || minDate}
                disabled={apply.isPending || half}
                value={half ? start : end}
                onChange={(e) => setEnd(e.target.value)}
              />
              {submitted && <FieldError message={errors.end} />}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                disabled={apply.isPending}
                checked={half}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setHalf(checked);
                  if (checked && start) setEnd(start);
                }}
              />
              Half day
            </label>
            <Textarea
              maxLength={500}
              disabled={apply.isPending}
              placeholder="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            {apply.error ? <p className="text-sm text-red-700">{apply.error.message}</p> : null}
            <Button
              loading={apply.isPending}
              onClick={() => {
                setSubmitted(true);
                if (!hasErrors) apply.mutate();
              }}
            >
              {apply.isPending ? "Submitting..." : "Submit request"}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
