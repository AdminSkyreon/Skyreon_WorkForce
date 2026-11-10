"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Badge, Button, Card, FieldError, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { Employee, Page, Project } from "@/lib/types";
import { labels } from "@/lib/utils";

const nonNegativeNumber = (label: string) =>
  z
    .string()
    .trim()
    .refine((val) => val !== "" && Number.isFinite(Number(val)) && Number(val) >= 0, {
      message: `${label} must be 0 or greater`,
    });

const schema = z
  .object({
    name: z.string().trim().min(1, "Project name is required").max(255, "Max 255 characters"),
    client_name: z.string().trim().min(1, "Client name is required").max(255, "Max 255 characters"),
    project_code: z.string().trim().min(1, "Project code is required").max(50, "Max 50 characters"),
    description: z.string().optional(),
    manager_id: z.string().min(1, "Select a project manager"),
    start_date: z.string().min(1, "Start date is required"),
    end_date: z.string().optional(),
    status: z.string(),
    contract_type: z.string(),
    revenue_amount: nonNegativeNumber("Revenue"),
    revenue_currency: z.string().trim().min(1, "Currency is required").max(8, "Max 8 characters"),
    budgeted_hours: nonNegativeNumber("Budgeted hours"),
  })
  .refine((v) => !v.end_date || !v.start_date || v.end_date >= v.start_date, {
    message: "End date cannot be earlier than start date",
    path: ["end_date"],
  });

const DEFAULT_VALUES: z.infer<typeof schema> = {
  name: "",
  client_name: "",
  project_code: "",
  description: "",
  manager_id: "",
  start_date: "",
  end_date: "",
  status: "planned",
  contract_type: "time_and_material",
  revenue_amount: "0",
  revenue_currency: "USD",
  budgeted_hours: "0",
};

export default function ProjectsPage() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  });
  const startDate = form.watch("start_date");
  const errors = form.formState.errors;

  const { data } = useQuery({
    queryKey: ["projects", search, status, page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "10", sort: "name" });
      if (search) params.set("search", search);
      if (status) params.set("status", status);
      return api<Page<Project>>(`/admin/projects?${params}`);
    },
  });
  const employees = useQuery({
    queryKey: ["employees-all"],
    queryFn: () => api<Page<Employee>>("/admin/employees?page_size=100"),
  });

  function closeModal() {
    setOpen(false);
    setEditing(null);
    form.reset(DEFAULT_VALUES);
    create.reset();
    update.reset();
  }

  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      api("/admin/projects", {
        method: "POST",
        body: JSON.stringify({ ...values, end_date: values.end_date || null, member_ids: [values.manager_id] }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project created");
      closeModal();
    },
  });
  const update = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      api(`/admin/projects/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ ...values, end_date: values.end_date || null }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project updated");
      closeModal();
    },
  });

  function openCreate() {
    setEditing(null);
    create.reset();
    update.reset();
    form.reset(DEFAULT_VALUES);
    setOpen(true);
  }

  function openEdit(project: Project) {
    setEditing(project);
    create.reset();
    update.reset();
    form.reset({
      name: project.name,
      client_name: project.client_name,
      project_code: project.project_code,
      description: project.description || "",
      manager_id: project.manager_id,
      start_date: project.start_date,
      end_date: project.end_date || "",
      status: project.status,
      contract_type: project.contract_type,
      revenue_amount: project.revenue_amount,
      revenue_currency: project.revenue_currency,
      budgeted_hours: project.budgeted_hours,
    });
    setOpen(true);
  }

  const isSaving = editing ? update.isPending : create.isPending;
  const saveError = editing ? update.error : create.error;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <Input placeholder="Search projects" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-xs" />
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="max-w-xs">
          <option value="">All statuses</option>
          {Object.entries(labels.projectStatus).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </Select>
        <Button onClick={openCreate}>New project</Button>
      </div>
      <Card className="overflow-x-auto p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3">Project</th>
              <th className="px-4 py-3">Client</th>
              <th className="px-4 py-3">Manager</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Dates</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {data?.items.length ? data.items.map((project) => (
              <tr key={project.id} className="border-t border-ink/5">
                <td className="px-4 py-3">
                  <Link href={`/admin/projects/${project.id}`} className="font-semibold hover:text-forest">
                    {project.name}
                  </Link>
                  <p className="text-xs text-ink/50">{project.project_code}</p>
                </td>
                <td className="px-4 py-3">{project.client_name}</td>
                <td className="px-4 py-3">{project.manager_name}</td>
                <td className="px-4 py-3">
                  <Badge>{labels.projectStatus[project.status]}</Badge>
                </td>
                <td className="px-4 py-3">
                  {project.start_date} {project.end_date ? `→ ${project.end_date}` : ""}
                </td>
                <td className="px-4 py-3 text-right">
                  <IconButton label="Edit project" onClick={() => openEdit(project)} />
                </td>
              </tr>
            )) : (
              <tr>
                <td className="px-4 py-8 text-center text-ink/50" colSpan={6}>
                  No projects yet. Create one, add the team, then add tasks so people can track time.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
      <div className="flex gap-2">
        <Button variant="outline" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
          Previous
        </Button>
        <Button variant="outline" disabled={!data || page * data.page_size >= data.total} onClick={() => setPage((p) => p + 1)}>
          Next
        </Button>
      </div>

      <Modal open={open} title={editing ? "Edit project" : "Create project"} onClose={closeModal}>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={form.handleSubmit((v) => (editing ? update.mutate(v) : create.mutate(v)))}>
          <div>
            <Label>Name</Label>
            <Input maxLength={255} disabled={isSaving} {...form.register("name")} />
            <FieldError message={errors.name?.message} />
          </div>
          <div>
            <Label>Client</Label>
            <Input maxLength={255} disabled={isSaving} {...form.register("client_name")} />
            <FieldError message={errors.client_name?.message} />
          </div>
          <div>
            <Label>Code</Label>
            <Input maxLength={50} disabled={!!editing || isSaving} {...form.register("project_code")} />
            <FieldError message={errors.project_code?.message} />
          </div>
          <div>
            <Label>Manager</Label>
            <Select disabled={isSaving} {...form.register("manager_id")}>
              <option value="">Select</option>
              {employees.data?.items.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </Select>
            <FieldError message={errors.manager_id?.message} />
          </div>
          <div>
            <Label>Start</Label>
            <Input type="date" disabled={isSaving} {...form.register("start_date")} />
            <FieldError message={errors.start_date?.message} />
          </div>
          <div>
            <Label>End</Label>
            <Input type="date" min={startDate || undefined} disabled={isSaving} {...form.register("end_date")} />
            <FieldError message={errors.end_date?.message} />
          </div>
          <div>
            <Label>Status</Label>
            <Select disabled={isSaving} {...form.register("status")}>
              {Object.entries(labels.projectStatus).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Contract</Label>
            <Select disabled={isSaving} {...form.register("contract_type")}>
              {Object.entries(labels.contract).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Revenue</Label>
            <Input type="number" min="0" step="0.01" disabled={isSaving} {...form.register("revenue_amount")} />
            <FieldError message={errors.revenue_amount?.message} />
          </div>
          <div>
            <Label>Currency</Label>
            <Input maxLength={8} disabled={isSaving} {...form.register("revenue_currency")} />
            <FieldError message={errors.revenue_currency?.message} />
          </div>
          <div>
            <Label>Budgeted hours</Label>
            <Input type="number" min="0" step="0.01" disabled={isSaving} {...form.register("budgeted_hours")} />
            <FieldError message={errors.budgeted_hours?.message} />
          </div>
          {saveError ? <p className="md:col-span-2 text-sm text-red-700">{saveError.message}</p> : null}
          <div className="md:col-span-2">
            <Button
              type="submit"
              loading={isSaving}
            >
              {editing
                ? isSaving ? "Saving..." : "Save changes"
                : isSaving ? "Creating..." : "Create"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
