"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, FieldError, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { Employee, Page, Review, ReviewCycle } from "@/lib/types";

export default function ReviewsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [cycleId, setCycleId] = useState("");
  const [form, setForm] = useState({ name: "", start_date: "", end_date: "" });
  const [cycleSubmitted, setCycleSubmitted] = useState(false);
  const [review, setReview] = useState({ employee_id: "", summary: "" });
  const [reviewSubmitted, setReviewSubmitted] = useState(false);

  const cycles = useQuery({ queryKey: ["cycles"], queryFn: () => api<ReviewCycle[]>("/review-cycles") });
  const people = useQuery({
    queryKey: ["employees", "reviews"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });
  const reviews = useQuery({
    queryKey: ["reviews", cycleId],
    queryFn: () => api<Review[]>(`/review-cycles/${cycleId}/reviews`),
    enabled: Boolean(cycleId),
  });

  const cycleErrors = {
    name: !form.name.trim() ? "Cycle name is required" : form.name.trim().length > 120 ? "Max 120 characters" : "",
    start_date: !form.start_date ? "Start date is required" : "",
    end_date: !form.end_date
      ? "End date is required"
      : form.start_date && form.end_date < form.start_date
        ? "End date cannot be earlier than start date"
        : "",
  };
  const hasCycleErrors = Object.values(cycleErrors).some(Boolean);

  const reviewErrors = {
    employee_id: !review.employee_id ? "Select an employee" : "",
    summary: !review.summary.trim() ? "Review summary is required" : "",
  };
  const hasReviewErrors = Object.values(reviewErrors).some(Boolean);

  function closeCycleModal() {
    setOpen(false);
    setForm({ name: "", start_date: "", end_date: "" });
    setCycleSubmitted(false);
    create.reset();
  }

  const create = useMutation({
    mutationFn: () =>
      api("/review-cycles", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          start_date: form.start_date,
          end_date: form.end_date,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cycles"] });
      toast.success("Review cycle created");
      closeCycleModal();
    },
  });
  const save = useMutation({
    mutationFn: () =>
      api(`/review-cycles/${cycleId}/reviews`, {
        method: "POST",
        body: JSON.stringify({
          employee_id: review.employee_id,
          summary: review.summary.trim(),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["reviews", cycleId] });
      setReview({ employee_id: "", summary: "" });
      setReviewSubmitted(false);
      toast.success("Review saved");
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Open a cycle, write a short review, then the person acknowledges it.</p>
        <Button
          onClick={() => {
            create.reset();
            setCycleSubmitted(false);
            setForm({ name: "", start_date: "", end_date: "" });
            setOpen(true);
          }}
        >
          New cycle
        </Button>
      </div>
      <Select
        value={cycleId}
        onChange={(e) => {
          setCycleId(e.target.value);
          setReviewSubmitted(false);
          save.reset();
        }}
      >
        <option value="">Choose cycle</option>
        {cycles.data?.map((cycle) => (
          <option key={cycle.id} value={cycle.id}>
            {cycle.name}
          </option>
        ))}
      </Select>
      {cycleId && (
        <Card className="grid gap-3">
          <div>
            <Select
              disabled={save.isPending}
              value={review.employee_id}
              onChange={(e) => setReview((p) => ({ ...p, employee_id: e.target.value }))}
            >
              <option value="">Person</option>
              {people.data?.items.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </Select>
            {reviewSubmitted && <FieldError message={reviewErrors.employee_id} />}
          </div>
          <div>
            <Textarea
              maxLength={4000}
              disabled={save.isPending}
              value={review.summary}
              onChange={(e) => setReview((p) => ({ ...p, summary: e.target.value }))}
              placeholder="Review summary"
            />
            {reviewSubmitted && <FieldError message={reviewErrors.summary} />}
          </div>
          {save.error ? <p className="text-sm text-red-700">{save.error.message}</p> : null}
          <Button
            loading={save.isPending}
            onClick={() => {
              setReviewSubmitted(true);
              if (!hasReviewErrors) save.mutate();
            }}
          >
            {save.isPending ? "Saving..." : "Save review"}
          </Button>
        </Card>
      )}
      {reviews.data?.map((row) => (
        <Card key={row.id}>
          <div className="flex justify-between">
            <p className="font-semibold">{row.employee_name}</p>
            <Badge tone={row.acknowledged ? "good" : "warn"}>{row.acknowledged ? "Acknowledged" : "Pending"}</Badge>
          </div>
          <p className="mt-2 text-sm text-ink/70">{row.summary}</p>
        </Card>
      ))}
      <Modal open={open} title="Review cycle" onClose={closeCycleModal}>
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input
              maxLength={120}
              disabled={create.isPending}
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
            {cycleSubmitted && <FieldError message={cycleErrors.name} />}
          </div>
          <div>
            <Label>Start</Label>
            <Input
              type="date"
              disabled={create.isPending}
              value={form.start_date}
              onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))}
            />
            {cycleSubmitted && <FieldError message={cycleErrors.start_date} />}
          </div>
          <div>
            <Label>End</Label>
            <Input
              type="date"
              min={form.start_date || undefined}
              disabled={create.isPending}
              value={form.end_date}
              onChange={(e) => setForm((p) => ({ ...p, end_date: e.target.value }))}
            />
            {cycleSubmitted && <FieldError message={cycleErrors.end_date} />}
          </div>
          {create.error ? <p className="text-sm text-red-700">{create.error.message}</p> : null}
          <Button
            loading={create.isPending}
            onClick={() => {
              setCycleSubmitted(true);
              if (!hasCycleErrors) create.mutate();
            }}
          >
            {create.isPending ? "Creating..." : "Create"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
