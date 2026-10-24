"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Employee, LeaveRequest, LeaveType, Page } from "@/lib/types";
import { labels } from "@/lib/utils";

function accrualLabel(t: LeaveType) {
  if (t.code === "CO") return "Comp-off credits";
  if (t.code === "LWP") return "Unpaid";
  if (t.accrual_mode === "monthly") {
    return `${t.days_per_month}/mo · cap ${t.annual_allocation_days}`;
  }
  return `${t.annual_allocation_days} days (lump)`;
}

export default function AdminLeavePage() {
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [days, setDays] = useState("12");
  const [newAccrual, setNewAccrual] = useState<"lump" | "monthly">("monthly");
  const [newPerMonth, setNewPerMonth] = useState("1");
  const [employeeId, setEmployeeId] = useState("");
  const [leaveType, setLeaveType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [half, setHalf] = useState(false);
  const [reason, setReason] = useState("");
  const [editing, setEditing] = useState<LeaveType | null>(null);
  const [editName, setEditName] = useState("");
  const [editAnnual, setEditAnnual] = useState("");
  const [editAccrual, setEditAccrual] = useState<"lump" | "monthly">("monthly");
  const [editPerMonth, setEditPerMonth] = useState("");
  const [editUnpaid, setEditUnpaid] = useState(false);

  const requests = useQuery({ queryKey: ["leave-admin"], queryFn: () => api<LeaveRequest[]>("/leave") });
  const types = useQuery({ queryKey: ["leave-types"], queryFn: () => api<LeaveType[]>("/leave-types") });
  const employees = useQuery({
    queryKey: ["employees-all"],
    queryFn: () => api<Page<Employee>>("/admin/employees?page_size=100"),
  });
  const review = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      api(`/leave/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leave-admin"] }),
  });
  const createType = useMutation({
    mutationFn: () =>
      api("/admin/leave-types", {
        method: "POST",
        body: JSON.stringify({
          name,
          code,
          annual_allocation_days: Number(days),
          accrual_mode: newAccrual,
          days_per_month: newAccrual === "monthly" ? newPerMonth : "0",
        }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["leave-types"] }),
  });
  const saveType = useMutation({
    mutationFn: () =>
      api(`/admin/leave-types/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName,
          ...(editing?.code !== "CO" && editing?.code !== "LWP"
            ? {
                annual_allocation_days: Number(editAnnual),
                accrual_mode: editAccrual,
                days_per_month: editAccrual === "monthly" ? editPerMonth : "0",
                is_unpaid: editUnpaid,
              }
            : {}),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leave-types"] });
      setEditing(null);
    },
  });
  const addLeave = useMutation({
    mutationFn: () =>
      api("/admin/leave", {
        method: "POST",
        body: JSON.stringify({
          employee_id: employeeId,
          leave_type_id: leaveType,
          start_date: start,
          end_date: end || start,
          is_half_day: half,
          reason,
          approve: true,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leave-admin"] });
      setReason("");
    },
  });

  function openEdit(t: LeaveType) {
    setEditing(t);
    setEditName(t.name);
    setEditAnnual(String(t.annual_allocation_days));
    setEditAccrual(t.accrual_mode);
    setEditPerMonth(t.days_per_month || "1");
    setEditUnpaid(Boolean(t.is_unpaid));
  }

  const lockedAccrual = editing?.code === "CO" || editing?.code === "LWP";

  return (
    <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
      <div className="space-y-4">
        <Textarea placeholder="Review comment" value={comment} onChange={(e) => setComment(e.target.value)} />
        {requests.data?.map((req) => (
          <Card key={req.id}>
            <div className="flex justify-between gap-3">
              <div>
                <h3 className="font-display text-2xl">{req.employee_name}</h3>
                <p className="text-sm text-ink/60">
                  {req.leave_type_name} · {req.start_date} to {req.end_date} · {req.days} days
                </p>
                <p className="mt-2 text-sm">{req.reason}</p>
              </div>
              <Badge tone={req.status === "approved" ? "good" : req.status === "rejected" ? "bad" : "warn"}>
                {labels.leave[req.status]}
              </Badge>
            </div>
            {req.status === "pending" && (
              <div className="mt-4 flex gap-2">
                <Button onClick={() => review.mutate({ id: req.id, action: "approve" })}>Approve</Button>
                <Button variant="danger" onClick={() => review.mutate({ id: req.id, action: "reject" })}>
                  Reject
                </Button>
              </div>
            )}
          </Card>
        ))}
      </div>
      <div className="space-y-4">
        <Card>
          <h3 className="font-display text-2xl">Add leave</h3>
          <p className="mt-1 text-sm text-ink/60">Creates an approved leave for the selected employee.</p>
          <div className="mt-4 space-y-3">
            <div>
              <Label>Employee</Label>
              <Select value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                <option value="">Select</option>
                {employees.data?.items.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label>Type</Label>
              <Select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
                <option value="">Select</option>
                {types.data?.map((t) => (
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
            <Button onClick={() => addLeave.mutate()}>Add leave</Button>
            {addLeave.error ? <p className="text-sm text-red-700">{addLeave.error.message}</p> : null}
          </div>
        </Card>
        <Card>
          <h3 className="font-display text-2xl">Leave types</h3>
          <p className="mt-1 text-sm text-ink/60">
            Monthly types accrue each calendar month up to the annual cap.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {types.data?.map((t) => (
              <li key={t.id} className="flex items-center justify-between gap-2">
                <div>
                  <span className="font-semibold">{t.name}</span>
                  <span className="ml-2 text-ink/50">{t.code}</span>
                  {t.is_unpaid ? <span className="ml-2 inline-block"><Badge>Unpaid</Badge></span> : null}
                  <p className="text-xs text-ink/50">{accrualLabel(t)}</p>
                </div>
                <Button variant="ghost" onClick={() => openEdit(t)}>
                  Edit
                </Button>
              </li>
            ))}
          </ul>
          <div className="mt-4 space-y-2 border-t border-ink/10 pt-4">
            <p className="text-sm font-semibold">Add new type</p>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
            <Label>Code</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} />
            <Label>Annual cap (days)</Label>
            <Input value={days} onChange={(e) => setDays(e.target.value)} />
            <Label>Accrual</Label>
            <Select value={newAccrual} onChange={(e) => setNewAccrual(e.target.value as "lump" | "monthly")}>
              <option value="monthly">Monthly</option>
              <option value="lump">Lump (full year upfront)</option>
            </Select>
            {newAccrual === "monthly" ? (
              <>
                <Label>Days per month</Label>
                <Input value={newPerMonth} onChange={(e) => setNewPerMonth(e.target.value)} />
              </>
            ) : null}
            <Button onClick={() => createType.mutate()}>Add type</Button>
          </div>
        </Card>
      </div>

      <Modal open={Boolean(editing)} onClose={() => setEditing(null)} title={`Edit ${editing?.code ?? "leave type"}`}>
        <div className="space-y-3">
          <div>
            <Label>Name</Label>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </div>
          {!lockedAccrual ? (
            <>
              <div>
                <Label>Annual cap (days)</Label>
                <Input type="number" min="0" value={editAnnual} onChange={(e) => setEditAnnual(e.target.value)} />
              </div>
              <div>
                <Label>Accrual</Label>
                <Select value={editAccrual} onChange={(e) => setEditAccrual(e.target.value as "lump" | "monthly")}>
                  <option value="monthly">Monthly</option>
                  <option value="lump">Lump</option>
                </Select>
              </div>
              {editAccrual === "monthly" ? (
                <div>
                  <Label>Days per month</Label>
                  <Input value={editPerMonth} onChange={(e) => setEditPerMonth(e.target.value)} />
                </div>
              ) : null}
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editUnpaid} onChange={(e) => setEditUnpaid(e.target.checked)} />
                Unpaid leave
              </label>
            </>
          ) : (
            <p className="text-sm text-ink/60">
              {editing?.code === "CO"
                ? "Comp-off balance comes from approved extra work only."
                : "Leave without pay has no allocation."}
            </p>
          )}
          <Button onClick={() => saveType.mutate()} disabled={saveType.isPending}>
            Save
          </Button>
          {saveType.error ? <p className="text-sm text-red-700">{saveType.error.message}</p> : null}
        </div>
      </Modal>
    </div>
  );
}
