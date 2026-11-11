"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, FieldError, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { toast } from "@/components/toast";
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

function isValidNonNeg(val: string) {
  const trimmed = val.trim();
  if (!trimmed) return false;
  const n = Number(trimmed);
  return Number.isFinite(n) && n >= 0;
}

export default function AdminLeavePage() {
  const qc = useQueryClient();
  const [comment, setComment] = useState("");
  const [commentError, setCommentError] = useState("");

  // Add new leave type state
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [days, setDays] = useState("12");
  const [newAccrual, setNewAccrual] = useState<"lump" | "monthly">("monthly");
  const [newPerMonth, setNewPerMonth] = useState("1");
  const [newUnpaid, setNewUnpaid] = useState(false);
  const [typeSubmitted, setTypeSubmitted] = useState(false);

  // Add approved leave state
  const [employeeId, setEmployeeId] = useState("");
  const [leaveType, setLeaveType] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [half, setHalf] = useState(false);
  const [reason, setReason] = useState("");
  const [leaveSubmitted, setLeaveSubmitted] = useState(false);

  // Edit leave type modal state
  const [editing, setEditing] = useState<LeaveType | null>(null);
  const [editName, setEditName] = useState("");
  const [editAnnual, setEditAnnual] = useState("");
  const [editAccrual, setEditAccrual] = useState<"lump" | "monthly">("monthly");
  const [editPerMonth, setEditPerMonth] = useState("");
  const [editUnpaid, setEditUnpaid] = useState(false);
  const [editSubmitted, setEditSubmitted] = useState(false);

  const requests = useQuery({ queryKey: ["leave-admin"], queryFn: () => api<LeaveRequest[]>("/leave") });
  const types = useQuery({ queryKey: ["leave-types"], queryFn: () => api<LeaveType[]>("/leave-types") });
  const employees = useQuery({
    queryKey: ["employees", "active-options"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });

  const review = useMutation({
    mutationFn: ({ id, action, reviewComment }: { id: string; action: "approve" | "reject"; reviewComment: string }) =>
      api(`/leave/${id}/${action}`, { method: "POST", body: JSON.stringify({ comment: reviewComment }) }),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: ["leave-admin"] });
      setComment("");
      setCommentError("");
      toast.success(vars.action === "approve" ? "Leave approved" : "Leave rejected");
    },
  });

  const effectiveLeaveEnd = half ? start : end || start;
  const leaveErrors = {
    employeeId: !employeeId ? "Select an employee" : "",
    leaveType: !leaveType ? "Select a leave type" : "",
    start: !start ? "Start date is required" : "",
    end:
      start && effectiveLeaveEnd && effectiveLeaveEnd < start
        ? "End date cannot be earlier than start date"
        : half && start && effectiveLeaveEnd !== start
          ? "Half-day leave must be a single date"
          : "",
  };
  const hasLeaveErrors = Object.values(leaveErrors).some(Boolean);

  const typeAnnualNum = Number(days.trim());
  const typePerMonthNum = Number(newPerMonth.trim());
  const typeErrors = {
    name: !name.trim() ? "Name is required" : name.trim().length > 120 ? "Max 120 characters" : "",
    code: !code.trim() ? "Code is required" : code.trim().length > 20 ? "Max 20 characters" : "",
    days:
      !isValidNonNeg(days) || !Number.isInteger(typeAnnualNum)
        ? "Annual cap must be a whole number (0 or greater)"
        : "",
    perMonth:
      newAccrual === "monthly"
        ? !isValidNonNeg(newPerMonth)
          ? "Days per month must be 0 or greater"
          : Number.isFinite(typeAnnualNum) && typePerMonthNum > typeAnnualNum
            ? "Days per month cannot exceed the annual cap"
            : ""
        : "",
  };
  const hasTypeErrors = Object.values(typeErrors).some(Boolean);

  const lockedAccrual = editing?.code === "CO" || editing?.code === "LWP";
  const editAnnualNum = Number(editAnnual.trim());
  const editPerMonthNum = Number(editPerMonth.trim());
  const editErrors = {
    name: !editName.trim() ? "Name is required" : editName.trim().length > 120 ? "Max 120 characters" : "",
    annual:
      !lockedAccrual && (!isValidNonNeg(editAnnual) || !Number.isInteger(editAnnualNum))
        ? "Annual cap must be a whole number (0 or greater)"
        : "",
    perMonth:
      !lockedAccrual && editAccrual === "monthly"
        ? !isValidNonNeg(editPerMonth)
          ? "Days per month must be 0 or greater"
          : Number.isFinite(editAnnualNum) && editPerMonthNum > editAnnualNum
            ? "Days per month cannot exceed the annual cap"
            : ""
        : "",
  };
  const hasEditErrors = Object.values(editErrors).some(Boolean);

  const createType = useMutation({
    mutationFn: () =>
      api("/admin/leave-types", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          code: code.trim(),
          annual_allocation_days: Number(days),
          is_unpaid: newUnpaid,
          accrual_mode: newAccrual,
          days_per_month: newAccrual === "monthly" ? newPerMonth.trim() : "0",
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leave-types"] });
      setName("");
      setCode("");
      setDays("12");
      setNewAccrual("monthly");
      setNewPerMonth("1");
      setNewUnpaid(false);
      setTypeSubmitted(false);
      toast.success("Leave type added");
    },
  });

  const saveType = useMutation({
    mutationFn: () =>
      api(`/admin/leave-types/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editName.trim(),
          ...(editing?.code !== "CO" && editing?.code !== "LWP"
            ? {
                annual_allocation_days: Number(editAnnual),
                accrual_mode: editAccrual,
                days_per_month: editAccrual === "monthly" ? editPerMonth.trim() : "0",
                is_unpaid: editUnpaid,
              }
            : {}),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leave-types"] });
      setEditing(null);
      setEditSubmitted(false);
      toast.success("Leave type updated");
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
          end_date: effectiveLeaveEnd,
          is_half_day: half,
          reason: reason.trim(),
          approve: true,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["leave-admin"] });
      setEmployeeId("");
      setLeaveType("");
      setStart("");
      setEnd("");
      setHalf(false);
      setReason("");
      setLeaveSubmitted(false);
      toast.success("Leave added");
    },
  });

  function openEdit(t: LeaveType) {
    setEditSubmitted(false);
    saveType.reset();
    setEditing(t);
    setEditName(t.name);
    setEditAnnual(String(t.annual_allocation_days));
    setEditAccrual(t.accrual_mode);
    setEditPerMonth(t.days_per_month || "1");
    setEditUnpaid(Boolean(t.is_unpaid));
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
      <div className="space-y-4">
        <div>
          <Textarea
            maxLength={500}
            disabled={review.isPending}
            placeholder="Review comment (required when rejecting)"
            value={comment}
            onChange={(e) => {
              setCommentError("");
              setComment(e.target.value);
            }}
          />
          <FieldError message={commentError} />
          {review.error ? <p className="mt-1 text-sm text-red-700">{review.error.message}</p> : null}
        </div>
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
                <Button
                  disabled={review.isPending}
                  loading={review.isPending && review.variables?.id === req.id && review.variables?.action === "approve"}
                  onClick={() => {
                    setCommentError("");
                    review.mutate({ id: req.id, action: "approve", reviewComment: comment.trim() });
                  }}
                >
                  Approve
                </Button>
                <Button
                  variant="danger"
                  disabled={review.isPending}
                  loading={review.isPending && review.variables?.id === req.id && review.variables?.action === "reject"}
                  onClick={() => {
                    if (!comment.trim()) {
                      setCommentError("Please enter a review comment before rejecting.");
                      return;
                    }
                    setCommentError("");
                    review.mutate({ id: req.id, action: "reject", reviewComment: comment.trim() });
                  }}
                >
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
              <Select disabled={addLeave.isPending} value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
                <option value="">Select</option>
                {employees.data?.items.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name}
                  </option>
                ))}
              </Select>
              {leaveSubmitted && <FieldError message={leaveErrors.employeeId} />}
            </div>
            <div>
              <Label>Type</Label>
              <Select disabled={addLeave.isPending} value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
                <option value="">Select</option>
                {types.data?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </Select>
              {leaveSubmitted && <FieldError message={leaveErrors.leaveType} />}
            </div>
            <div>
              <Label>Start</Label>
              <Input
                type="date"
                disabled={addLeave.isPending}
                value={start}
                onChange={(e) => {
                  const nextStart = e.target.value;
                  setStart(nextStart);
                  if (half || (end && nextStart && end < nextStart)) {
                    setEnd(nextStart);
                  }
                }}
              />
              {leaveSubmitted && <FieldError message={leaveErrors.start} />}
            </div>
            <div>
              <Label>End</Label>
              <Input
                type="date"
                min={start || undefined}
                disabled={addLeave.isPending || half}
                value={half ? start : end}
                onChange={(e) => setEnd(e.target.value)}
              />
              {leaveSubmitted && <FieldError message={leaveErrors.end} />}
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                disabled={addLeave.isPending}
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
              disabled={addLeave.isPending}
              placeholder="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            {addLeave.error ? <p className="text-sm text-red-700">{addLeave.error.message}</p> : null}
            <Button
              loading={addLeave.isPending}
              onClick={() => {
                setLeaveSubmitted(true);
                if (!hasLeaveErrors) addLeave.mutate();
              }}
            >
              {addLeave.isPending ? "Adding..." : "Add leave"}
            </Button>
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
            <div>
              <Label>Name</Label>
              <Input maxLength={120} disabled={createType.isPending} value={name} onChange={(e) => setName(e.target.value)} />
              {typeSubmitted && <FieldError message={typeErrors.name} />}
            </div>
            <div>
              <Label>Code</Label>
              <Input maxLength={20} disabled={createType.isPending} value={code} onChange={(e) => setCode(e.target.value)} />
              {typeSubmitted && <FieldError message={typeErrors.code} />}
            </div>
            <div>
              <Label>Annual cap (days)</Label>
              <Input type="number" min="0" step="1" disabled={createType.isPending} value={days} onChange={(e) => setDays(e.target.value)} />
              {typeSubmitted && <FieldError message={typeErrors.days} />}
            </div>
            <div>
              <Label>Accrual</Label>
              <Select disabled={createType.isPending} value={newAccrual} onChange={(e) => setNewAccrual(e.target.value as "lump" | "monthly")}>
                <option value="monthly">Monthly</option>
                <option value="lump">Lump (full year upfront)</option>
              </Select>
            </div>
            {newAccrual === "monthly" ? (
              <div>
                <Label>Days per month</Label>
                <Input type="number" min="0" step="0.5" disabled={createType.isPending} value={newPerMonth} onChange={(e) => setNewPerMonth(e.target.value)} />
                {typeSubmitted && <FieldError message={typeErrors.perMonth} />}
              </div>
            ) : null}
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" disabled={createType.isPending} checked={newUnpaid} onChange={(e) => setNewUnpaid(e.target.checked)} />
              Unpaid leave
            </label>
            {createType.error ? <p className="text-sm text-red-700">{createType.error.message}</p> : null}
            <Button
              loading={createType.isPending}
              onClick={() => {
                setTypeSubmitted(true);
                if (!hasTypeErrors) createType.mutate();
              }}
            >
              {createType.isPending ? "Adding..." : "Add type"}
            </Button>
          </div>
        </Card>
      </div>

      <Modal
        open={Boolean(editing)}
        onClose={() => {
          setEditing(null);
          setEditSubmitted(false);
          saveType.reset();
        }}
        title={`Edit ${editing?.code ?? "leave type"}`}
      >
        <div className="space-y-3">
          <div>
            <Label>Name</Label>
            <Input maxLength={120} disabled={saveType.isPending} value={editName} onChange={(e) => setEditName(e.target.value)} />
            {editSubmitted && <FieldError message={editErrors.name} />}
          </div>
          {!lockedAccrual ? (
            <>
              <div>
                <Label>Annual cap (days)</Label>
                <Input type="number" min="0" step="1" disabled={saveType.isPending} value={editAnnual} onChange={(e) => setEditAnnual(e.target.value)} />
                {editSubmitted && <FieldError message={editErrors.annual} />}
              </div>
              <div>
                <Label>Accrual</Label>
                <Select disabled={saveType.isPending} value={editAccrual} onChange={(e) => setEditAccrual(e.target.value as "lump" | "monthly")}>
                  <option value="monthly">Monthly</option>
                  <option value="lump">Lump</option>
                </Select>
              </div>
              {editAccrual === "monthly" ? (
                <div>
                  <Label>Days per month</Label>
                  <Input type="number" min="0" step="0.5" disabled={saveType.isPending} value={editPerMonth} onChange={(e) => setEditPerMonth(e.target.value)} />
                  {editSubmitted && <FieldError message={editErrors.perMonth} />}
                </div>
              ) : null}
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" disabled={saveType.isPending} checked={editUnpaid} onChange={(e) => setEditUnpaid(e.target.checked)} />
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
          {saveType.error ? <p className="text-sm text-red-700">{saveType.error.message}</p> : null}
          <Button
            loading={saveType.isPending}
            onClick={() => {
              setEditSubmitted(true);
              if (!hasEditErrors) saveType.mutate();
            }}
          >
            {saveType.isPending ? "Saving..." : "Save"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
