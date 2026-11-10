"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, startOfMonth } from "date-fns";
import { useState } from "react";
import { Badge, Button, Card, FieldError, Input, Label, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { AttendanceDay, Employee, Page } from "@/lib/types";

export default function AttendancePage() {
  const qc = useQueryClient();
  const start = format(startOfMonth(new Date()), "yyyy-MM-dd");
  const today = format(new Date(), "yyyy-MM-dd");
  const [range, setRange] = useState({ start, end: today });
  const [form, setForm] = useState({ employee_id: "", work_date: today, mark: "present", note: "" });
  const [submitted, setSubmitted] = useState(false);

  const people = useQuery({
    queryKey: ["employees", "attendance"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });
  const rows = useQuery({
    queryKey: ["attendance", range],
    queryFn: () => api<AttendanceDay[]>(`/attendance?start=${range.start}&end=${range.end}`),
  });

  const errors = {
    employee_id: !form.employee_id ? "Select a person" : "",
    work_date: !form.work_date
      ? "Date is required"
      : form.work_date > today
        ? "Cannot mark attendance for a future date"
        : "",
  };
  const hasErrors = Object.values(errors).some(Boolean);

  const mark = useMutation({
    mutationFn: () =>
      api(`/employees/${form.employee_id}/attendance`, {
        method: "POST",
        body: JSON.stringify({ work_date: form.work_date, mark: form.mark, note: form.note }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["attendance"] });
      setSubmitted(false);
      toast.success("Attendance saved");
    },
  });

  return (
    <div className="space-y-4">
      <Card className="grid gap-3 md:grid-cols-4">
        <div>
          <Label>Person</Label>
          <Select
            disabled={mark.isPending}
            value={form.employee_id}
            onChange={(e) => setForm((p) => ({ ...p, employee_id: e.target.value }))}
          >
            <option value="">Select</option>
            {people.data?.items.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.name}
              </option>
            ))}
          </Select>
          {submitted && <FieldError message={errors.employee_id} />}
        </div>
        <div>
          <Label>Date</Label>
          <Input
            type="date"
            max={today}
            disabled={mark.isPending}
            value={form.work_date}
            onChange={(e) => setForm((p) => ({ ...p, work_date: e.target.value }))}
          />
          {submitted && <FieldError message={errors.work_date} />}
        </div>
        <div>
          <Label>Mark</Label>
          <Select
            disabled={mark.isPending}
            value={form.mark}
            onChange={(e) => setForm((p) => ({ ...p, mark: e.target.value }))}
          >
            <option value="present">Present</option>
            <option value="work_from">Work from</option>
            <option value="leave">Leave</option>
            <option value="absent">Absent</option>
          </Select>
        </div>
        <Button
          className="self-end"
          loading={mark.isPending}
          onClick={() => {
            setSubmitted(true);
            if (!hasErrors) mark.mutate();
          }}
        >
          {mark.isPending ? "Saving..." : "Save mark"}
        </Button>
        {mark.error ? <p className="md:col-span-4 text-sm text-red-700">{mark.error.message}</p> : null}
      </Card>
      <div className="grid gap-3 sm:grid-cols-2">
        <Input
          type="date"
          max={range.end || undefined}
          value={range.start}
          onChange={(e) => setRange((p) => ({ ...p, start: e.target.value }))}
        />
        <Input
          type="date"
          min={range.start || undefined}
          value={range.end}
          onChange={(e) => setRange((p) => ({ ...p, end: e.target.value }))}
        />
      </div>
      {rows.data?.map((row) => (
        <Card key={row.id} className="flex items-center justify-between">
          <div>
            <p className="font-semibold">{row.employee_name}</p>
            <p className="text-sm text-ink/50">{row.work_date}</p>
          </div>
          <Badge>{row.mark.replace("_", " ")}</Badge>
        </Card>
      ))}
    </div>
  );
}
