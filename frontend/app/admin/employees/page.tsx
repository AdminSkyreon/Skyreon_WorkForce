"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Badge, Button, Card, DetailGrid, IconButton, Input, Label, Modal, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DepartmentSelect, DesignationSelect, LocationSelect } from "@/components/org-pickers";
import type { Employee, Page } from "@/lib/types";
import { toast } from "@/components/toast";

const schema = z.object({
  name: z.string().min(1),
  phone: z.string().optional(),
  address: z.string().optional(),
  email: z.string().email(),
  designation: z.string().min(1),
  department: z.string().min(1),
  engagement: z.enum(["staff", "contractor"]),
  allow_leave: z.boolean().optional(),
  contract_monthly_fee: z.string().optional(),
  joining_date: z.string().min(1),
  reporting_manager_id: z.string().optional(),
  location_id: z.string().optional(),
  hourly_cost_rate: z.string().optional(),
  monthly_salary: z.string().optional(),
  pay_type: z.enum(["fixed", "hourly"]),
  temporary_password: z.string().min(8),
});

type StatusTab = "active" | "inactive";

export default function EmployeesPage() {
  const { user } = useAuth();
  const canManage = user?.role === "admin";
  const qc = useQueryClient();
  const [tab, setTab] = useState<StatusTab>("active");
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedSearch(search), 300);
    return () => window.clearTimeout(id);
  }, [search]);
  const [open, setOpen] = useState(false);
  const [resetId, setResetId] = useState<string | null>(null);
  const [tempPassword, setTempPassword] = useState("TempPass123");
  const [viewId, setViewId] = useState<string | null>(null);
  const [editEmp, setEditEmp] = useState<Employee | null>(null);
  const [editForm, setEditForm] = useState({
    name: "",
    phone: "",
    address: "",
    designation: "",
    department: "",
    joining_date: "",
    engagement: "staff" as "staff" | "contractor",
    allow_leave: false,
    contract_monthly_fee: "",
    pay_type: "fixed" as "fixed" | "hourly",
    hourly_cost_rate: "",
    monthly_salary: "",
    location_id: "",
    reporting_manager_id: "",
  });
  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: { pay_type: "fixed", engagement: "staff", designation: "", department: "", hourly_cost_rate: "0", monthly_salary: "", allow_leave: false, contract_monthly_fee: "" },
  });
  const payType = form.watch("pay_type");
  const engagement = form.watch("engagement");

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["employees", debouncedSearch, tab],
    queryFn: () =>
      api<Page<Employee>>(
        `/admin/employees?search=${encodeURIComponent(debouncedSearch)}&status=${tab}&page_size=50`,
      ),
    placeholderData: (prev) => prev,
  });
  const profile = useQuery({
    queryKey: ["employee", viewId],
    queryFn: () => api<Employee>(`/admin/employees/${viewId}`),
    enabled: Boolean(viewId),
  });
  const managers = useQuery({
    queryKey: ["employees", "active-options"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
    enabled: open, // <-- ONLY fetch when the "Add Employee" modal is opened!
    staleTime: 5 * 60 * 1000,
  });
  const counts = useQuery({
    queryKey: ["employees", "status-counts"],
    queryFn: async () => {
      const [active, inactive] = await Promise.all([
        api<Page<Employee>>("/admin/employees?status=active&page_size=1"),
        api<Page<Employee>>("/admin/employees?status=inactive&page_size=1"),
      ]);
      return { active: active.total, inactive: inactive.total };
    },
  });
  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      api("/admin/employees", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          hourly_cost_rate: values.pay_type === "hourly" ? values.hourly_cost_rate || "0" : "0",
          hourly_pay_rate: values.pay_type === "hourly" ? values.hourly_cost_rate || "0" : "0",
          monthly_salary: values.pay_type === "fixed" ? values.monthly_salary || "0" : "0",
          contract_monthly_fee: values.engagement === "contractor" ? values.contract_monthly_fee || "0" : "0",
          allow_leave: values.engagement === "contractor" ? Boolean(values.allow_leave) : true,
          reporting_manager_id: values.reporting_manager_id || null,
          location_id: values.location_id || null,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["employees"] });
      setOpen(false);
      form.reset();
    },
  });

const toggleStatus = useMutation({
  mutationFn: ({ id, nextStatus }: { id: string; nextStatus: StatusTab }) =>
    api<Employee>(
      `/admin/employees/${id}/${nextStatus === "active" ? "activate" : "deactivate"}`,
      { method: "POST" },
    ),
  onSuccess: (updated, { nextStatus }) => {
    // Remove row immediately from the current status tab cache so there is zero UI lag
    qc.setQueryData<Page<Employee>>(["employees", debouncedSearch, tab], (old) =>
      old
        ? {
            ...old,
            items: old.items.filter((item) => item.id !== updated.id),
            total: Math.max(0, old.total - 1),
          }
        : old,
    );
    void qc.invalidateQueries({ queryKey: ["employees"] });
    void qc.invalidateQueries({ queryKey: ["employee", updated.id] });
    toast.success(
      nextStatus === "active" ? "Employee activated" : "Employee deactivated",
      `${updated.name} is now ${nextStatus}.`,
    );
  },
});

  const update = useMutation({
    mutationFn: () =>
      api(`/admin/employees/${editEmp?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: editForm.name,
          phone: editForm.phone,
          address: editForm.address,
          designation: editForm.designation,
          department: editForm.department,
          joining_date: editForm.joining_date,
          engagement: editForm.engagement,
          allow_leave: editForm.engagement === "contractor" ? editForm.allow_leave : true,
          contract_monthly_fee: editForm.engagement === "contractor" ? editForm.contract_monthly_fee || "0" : "0",
          pay_type: editForm.pay_type,
          hourly_cost_rate: editForm.pay_type === "hourly" ? editForm.hourly_cost_rate || "0" : "0",
          hourly_pay_rate: editForm.pay_type === "hourly" ? editForm.hourly_cost_rate || "0" : "0",
          monthly_salary: editForm.pay_type === "fixed" ? editForm.monthly_salary || "0" : "0",
          location_id: editForm.location_id || null,
          reporting_manager_id: editForm.reporting_manager_id || null,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["employees"] });
      void qc.invalidateQueries({ queryKey: ["employee"] });
      setEditEmp(null);
    },
  });

  const resetPassword = useMutation({
    mutationFn: () =>
      api(`/admin/employees/${resetId}/reset-password`, {
        method: "POST",
        body: JSON.stringify({ temporary_password: tempPassword }),
      }),
    onSuccess: () => setResetId(null),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex rounded-full bg-mist p-1">
            {(["active", "inactive"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setTab(value)}
                className={`rounded-full px-4 py-1.5 text-sm font-semibold capitalize ${
                  tab === value ? "bg-white text-ink shadow-sm" : "text-ink/50"
                }`}
              >
                {value}
                {counts.data ? ` (${counts.data[value]})` : ""}
              </button>
            ))}
          </div>
          <Input placeholder="Search name, code, department" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
        </div>
        {canManage ? (
          <Button onClick={() => setOpen(true)}>Add employee</Button>
        ) : (
          <p className="text-sm text-ink/60">Only Admin can add employees. Sign in as admin@skyreon.com.</p>
        )}
      </div>
      {isFetching && !isLoading ? <p className="text-xs text-ink/50">Updating list…</p> : null}
      <Card className={`overflow-x-auto p-0 ${isFetching && !isLoading ? "opacity-70" : ""}`}>
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase tracking-wide text-ink/60">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Role</th>
              <th className="px-4 py-3">Department</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Pay</th>
              <th className="px-4 py-3">Pay amount</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody>
            {data?.items.length ? data.items.map((emp) => (
              <tr key={emp.id} className="border-t border-ink/5">
                <td className="px-4 py-3">
                  <p className="font-semibold">{emp.name}</p>
                  <p className="text-xs text-ink/50">{emp.email}</p>
                </td>
                <td className="px-4 py-3">{emp.employee_code}</td>
                <td className="px-4 py-3">{emp.designation}</td>
                <td className="px-4 py-3">{emp.department}</td>
                <td className="px-4 py-3">{emp.location_name || "—"}</td>
                <td className="px-4 py-3 capitalize">{emp.engagement || "staff"}</td>
                <td className="px-4 py-3 capitalize">{emp.pay_type || "fixed"}</td>
                <td className="px-4 py-3">
                  {emp.pay_type === "hourly"
                    ? emp.hourly_pay_rate || emp.hourly_cost_rate
                    : emp.monthly_salary && Number(emp.monthly_salary) > 0
                      ? emp.monthly_salary
                      : "—"}
                </td>
                <td className="px-4 py-3">
                  <Badge tone={emp.status === "active" ? "good" : "bad"}>{emp.status}</Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <IconButton label="View employee" variant="view" onClick={() => setViewId(emp.id)} />
                    {canManage && (
                      <>
                      <IconButton
                        label="Edit employee"
                        onClick={() => {
                          setEditEmp(emp);
                          setEditForm({
                            name: emp.name,
                            phone: emp.phone || "",
                            address: emp.address || "",
                            designation: emp.designation,
                            department: emp.department,
                            joining_date: emp.joining_date,
                            engagement: emp.engagement || "staff",
                            allow_leave: Boolean(emp.allow_leave),
                            contract_monthly_fee: emp.contract_monthly_fee || "",
                            pay_type: emp.pay_type || "fixed",
                            hourly_cost_rate: emp.hourly_pay_rate || emp.hourly_cost_rate || "",
                            monthly_salary: emp.monthly_salary || "",
                            location_id: emp.location_id || "",
                            reporting_manager_id: emp.reporting_manager_id || "",
                          });
                        }}
                      />
                      <Button variant="ghost" onClick={() => setResetId(emp.id)}>
                        Reset password
                      </Button>
                        <Button
                          variant="ghost"
                          loading={toggleStatus.isPending && toggleStatus.variables?.id === emp.id}
                          onClick={() =>
                            toggleStatus.mutate({
                              id: emp.id,
                              nextStatus: emp.status === "active" ? "inactive" : "active",
                            })
                          }
                        >
                          {emp.status === "active" ? "Deactivate" : "Activate"}
                        </Button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
            )) : (
              <tr>
                <td className="px-4 py-8 text-center text-ink/50" colSpan={10}>
                  {tab === "inactive" ? "No inactive employees." : "No active employees."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>

      <Modal open={open} title="Create employee" onClose={() => setOpen(false)}>
        <form className="grid gap-3 md:grid-cols-2" onSubmit={form.handleSubmit((v) => create.mutate(v))}>
          <p className="md:col-span-2 text-sm text-ink/60">Employee code is assigned automatically (SKY-0001, SKY-0002, …).</p>
          {[
            ["name", "Name"],
            ["phone", "Phone"],
            ["email", "Email"],
            ["joining_date", "Joining date"],
            ["temporary_password", "Temporary password"],
          ].map(([name, label]) => (
            <div key={name}>
              <Label>{label}</Label>
              <Input type={name.includes("date") ? "date" : name.includes("password") ? "password" : "text"} {...form.register(name as keyof z.infer<typeof schema>)} />
            </div>
          ))}
          <div className="md:col-span-2">
            <Label>Address</Label>
            <Textarea {...form.register("address")} rows={3} placeholder="Residential / correspondence address" />
          </div>
          <DesignationSelect value={form.watch("designation") || ""} onChange={(value) => form.setValue("designation", value)} />
          <DepartmentSelect value={form.watch("department") || ""} onChange={(value) => form.setValue("department", value)} />
          <div>
            <Label>Engagement</Label>
            <Select {...form.register("engagement")}>
              <option value="staff">Staff</option>
              <option value="contractor">Contractor</option>
            </Select>
          </div>
          {engagement === "contractor" && (
            <>
              <div>
                <Label>Contract monthly fee</Label>
                <Input {...form.register("contract_monthly_fee")} />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" {...form.register("allow_leave")} />
                Allow staff leave
              </label>
            </>
          )}
          <div>
            <Label>Pay type</Label>
            <Select {...form.register("pay_type")}>
              <option value="fixed">Fixed</option>
              <option value="hourly">Hourly</option>
            </Select>
          </div>
          {payType === "hourly" ? (
            <div>
              <Label>Hourly rate</Label>
              <Input {...form.register("hourly_cost_rate")} />
            </div>
          ) : (
            <div>
              <Label>Monthly salary</Label>
              <Input {...form.register("monthly_salary")} placeholder="e.g. 50000" />
              <p className="mt-1 text-xs text-ink/50">This is the fixed package. Split into basic / HRA later on Payroll if needed.</p>
            </div>
          )}
          <LocationSelect value={form.watch("location_id") || ""} onChange={(value) => form.setValue("location_id", value)} />
          <div>
            <Label>Reporting manager</Label>
            <Select {...form.register("reporting_manager_id")}>
              <option value="">None</option>
              {managers.data?.items.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="md:col-span-2">
            <Button type="submit" loading={create.isPending}>
              {create.isPending ? "Creating..." : "Create account"}
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={!!editEmp} title={`Edit ${editEmp?.name || "employee"}`} onClose={() => setEditEmp(null)}>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <Label>Name</Label>
            <Input value={editForm.name} onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div>
            <Label>Phone</Label>
            <Input value={editForm.phone} onChange={(e) => setEditForm((p) => ({ ...p, phone: e.target.value }))} />
          </div>
          <div className="md:col-span-2">
            <Label>Address</Label>
            <Textarea value={editForm.address} onChange={(e) => setEditForm((p) => ({ ...p, address: e.target.value }))} rows={3} />
          </div>
          <div>
            <Label>Joining date</Label>
            <Input type="date" value={editForm.joining_date} onChange={(e) => setEditForm((p) => ({ ...p, joining_date: e.target.value }))} />
          </div>
          <DesignationSelect value={editForm.designation} onChange={(value) => setEditForm((p) => ({ ...p, designation: value }))} />
          <DepartmentSelect value={editForm.department} onChange={(value) => setEditForm((p) => ({ ...p, department: value }))} />
          <div>
            <Label>Engagement</Label>
            <Select value={editForm.engagement} onChange={(e) => setEditForm((p) => ({ ...p, engagement: e.target.value as "staff" | "contractor" }))}>
              <option value="staff">Staff</option>
              <option value="contractor">Contractor</option>
            </Select>
          </div>
          {editForm.engagement === "contractor" && (
            <>
              <div>
                <Label>Contract monthly fee</Label>
                <Input value={editForm.contract_monthly_fee} onChange={(e) => setEditForm((p) => ({ ...p, contract_monthly_fee: e.target.value }))} />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={editForm.allow_leave} onChange={(e) => setEditForm((p) => ({ ...p, allow_leave: e.target.checked }))} />
                Allow staff leave
              </label>
            </>
          )}
          <div>
            <Label>Pay type</Label>
            <Select value={editForm.pay_type} onChange={(e) => setEditForm((p) => ({ ...p, pay_type: e.target.value as "fixed" | "hourly" }))}>
              <option value="fixed">Fixed</option>
              <option value="hourly">Hourly</option>
            </Select>
          </div>
          {editForm.pay_type === "hourly" ? (
            <div>
              <Label>Hourly rate</Label>
              <Input value={editForm.hourly_cost_rate} onChange={(e) => setEditForm((p) => ({ ...p, hourly_cost_rate: e.target.value }))} />
            </div>
          ) : (
            <div>
              <Label>Monthly salary</Label>
              <Input value={editForm.monthly_salary} onChange={(e) => setEditForm((p) => ({ ...p, monthly_salary: e.target.value }))} />
            </div>
          )}
          <LocationSelect value={editForm.location_id} onChange={(value) => setEditForm((p) => ({ ...p, location_id: value }))} />
          <div>
            <Label>Reporting manager</Label>
            <Select value={editForm.reporting_manager_id} onChange={(e) => setEditForm((p) => ({ ...p, reporting_manager_id: e.target.value }))}>
              <option value="">None</option>
              {managers.data?.items.filter((emp) => emp.id !== editEmp?.id).map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </Select>
          </div>
          {update.error ? <p className="md:col-span-2 text-sm text-red-700">{update.error.message}</p> : null}
          <div className="md:col-span-2">
            <Button 
              onClick={() => update.mutate()} 
              loading={update.isPending}
              disabled={!editForm.name || !editForm.designation || !editForm.department}
            >
              {update.isPending ? "Saving..." : "Save changes"}
            </Button>
          </div>
        </div>
      </Modal>

      <Modal open={!!viewId} title={profile.data?.name || "Employee profile"} onClose={() => setViewId(null)}>
        {profile.data ? (
          <div className="space-y-6">
            <DetailGrid
              rows={[
                { label: "Employee code", value: profile.data.employee_code },
                { label: "Email", value: profile.data.email },
                { label: "Phone", value: profile.data.phone },
                { label: "Status", value: profile.data.status },
                { label: "Designation", value: profile.data.designation },
                { label: "Department", value: profile.data.department },
                { label: "Location", value: profile.data.location_name },
                { label: "Reporting manager", value: profile.data.reporting_manager_name },
                { label: "Joining date", value: profile.data.joining_date },
                { label: "Engagement", value: profile.data.engagement || "staff" },
                { label: "Pay type", value: profile.data.pay_type },
                {
                  label: profile.data.pay_type === "hourly" ? "Hourly rate" : "Monthly salary",
                  value:
                    profile.data.pay_type === "hourly"
                      ? profile.data.hourly_pay_rate || profile.data.hourly_cost_rate
                      : profile.data.monthly_salary && Number(profile.data.monthly_salary) > 0
                        ? profile.data.monthly_salary
                        : "—",
                },
                {
                  label: "Contract fee",
                  value:
                    profile.data.engagement === "contractor" && profile.data.contract_monthly_fee
                      ? profile.data.contract_monthly_fee
                      : "—",
                },
                { label: "Portal login", value: profile.data.is_active_user ? "Active" : "Inactive" },
              ]}
            />
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-ink/50">Address</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{profile.data.address || "—"}</p>
            </div>
            {canManage ? (
              <Button
                variant="outline"
                onClick={() => {
                  const emp = profile.data;
                  setViewId(null);
                  setEditEmp(emp);
                  setEditForm({
                    name: emp.name,
                    phone: emp.phone || "",
                    address: emp.address || "",
                    designation: emp.designation,
                    department: emp.department,
                    joining_date: emp.joining_date,
                    engagement: emp.engagement || "staff",
                    allow_leave: Boolean(emp.allow_leave),
                    contract_monthly_fee: emp.contract_monthly_fee || "",
                    pay_type: emp.pay_type || "fixed",
                    hourly_cost_rate: emp.hourly_pay_rate || emp.hourly_cost_rate || "",
                    monthly_salary: emp.monthly_salary || "",
                    location_id: emp.location_id || "",
                    reporting_manager_id: emp.reporting_manager_id || "",
                  });
                }}
              >
                Edit profile
              </Button>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-ink/60">Loading profile…</p>
        )}
      </Modal>

      <Modal open={!!resetId} title="Reset password" onClose={() => setResetId(null)}>
        <Label>Temporary password</Label>
        <Input value={tempPassword} onChange={(e) => setTempPassword(e.target.value)} />
        <p className="mt-2 text-sm text-ink/60">The employee must change this on next login.</p>
          <Button className="mt-4" loading={resetPassword.isPending} onClick={() => resetPassword.mutate()}>
            {resetPassword.isPending ? "Resetting..." : "Reset"}
          </Button>
      </Modal>
    </div>
  );
}
