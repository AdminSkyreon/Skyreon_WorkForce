"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { Employee, Page, Review, ReviewCycle } from "@/lib/types";

export default function ReviewsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [cycleId, setCycleId] = useState("");
  const [form, setForm] = useState({ name: "", start_date: "", end_date: "" });
  const [review, setReview] = useState({ employee_id: "", summary: "" });
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
  const create = useMutation({
    mutationFn: () => api("/review-cycles", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["cycles"] });
      setOpen(false);
    },
  });
  const save = useMutation({
    mutationFn: () => api(`/review-cycles/${cycleId}/reviews`, { method: "POST", body: JSON.stringify(review) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reviews", cycleId] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Open a cycle, write a short review, then the person acknowledges it.</p>
        <Button onClick={() => setOpen(true)}>New cycle</Button>
      </div>
      <Select value={cycleId} onChange={(e) => setCycleId(e.target.value)}>
        <option value="">Choose cycle</option>
        {cycles.data?.map((cycle) => (
          <option key={cycle.id} value={cycle.id}>
            {cycle.name}
          </option>
        ))}
      </Select>
      {cycleId && (
        <Card className="grid gap-3">
          <Select value={review.employee_id} onChange={(e) => setReview((p) => ({ ...p, employee_id: e.target.value }))}>
            <option value="">Person</option>
            {people.data?.items.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.name}
              </option>
            ))}
          </Select>
          <Textarea value={review.summary} onChange={(e) => setReview((p) => ({ ...p, summary: e.target.value }))} placeholder="Review summary" />
          <Button
            loading={save.isPending}
            onClick={() => save.mutate()}
            disabled={!review.employee_id}
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
      <Modal open={open} title="Review cycle" onClose={() => setOpen(false)}>
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div>
            <Label>Start</Label>
            <Input type="date" value={form.start_date} onChange={(e) => setForm((p) => ({ ...p, start_date: e.target.value }))} />
          </div>
          <div>
            <Label>End</Label>
            <Input type="date" value={form.end_date} onChange={(e) => setForm((p) => ({ ...p, end_date: e.target.value }))} />
          </div>
          <Button loading={create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Creating..." : "Create"}</Button>
        </div>
      </Modal>
    </div>
  );
}
