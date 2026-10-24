"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { MonthPicker, money } from "@/components/period";
import { Badge, Button, Card, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { gstBreakdown } from "@/lib/gst";
import type { InvoiceSuggest, Page, Project, ProjectInvoice, ProjectPayment } from "@/lib/types";
import { isStaff } from "@/lib/types";

function statusTone(status: string) {
  if (status === "paid") return "good" as const;
  if (status === "partial") return "warn" as const;
  return "warn" as const;
}

export default function BillingPage() {
  const now = new Date();
  const { user } = useAuth();
  const staff = isStaff(user?.role);
  const qc = useQueryClient();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [addInvoice, setAddInvoice] = useState(false);
  const [addPayment, setAddPayment] = useState(false);
  const [editInvoice, setEditInvoice] = useState<ProjectInvoice | null>(null);
  const [editPayment, setEditPayment] = useState<ProjectPayment | null>(null);
  const [search, setSearch] = useState("");
  const [invoiceForm, setInvoiceForm] = useState({
    project_id: "",
    invoice_no: "",
    invoice_date: now.toISOString().slice(0, 10),
    taxable_amount: "",
    gst_percent: "18",
    note: "",
  });
  const [suggestHint, setSuggestHint] = useState("");
  const [payForm, setPayForm] = useState({
    invoice_id: "",
    amount: "",
    received_date: now.toISOString().slice(0, 10),
    note: "",
  });

  const invoices = useQuery({
    queryKey: ["invoices", year, month],
    queryFn: () => api<ProjectInvoice[]>(`/invoices?year=${year}&month=${month}`),
  });
  const outstanding = useQuery({
    queryKey: ["invoices-open"],
    queryFn: () => api<ProjectInvoice[]>("/invoices?outstanding=true"),
  });
  const payments = useQuery({
    queryKey: ["payments", year, month],
    queryFn: () => api<ProjectPayment[]>(`/payments?year=${year}&month=${month}`),
    enabled: staff,
  });
  const projects = useQuery({
    queryKey: ["billing-projects", staff],
    queryFn: () =>
      staff
        ? api<Page<Project>>("/admin/projects?page_size=100").then((page) => page.items)
        : api<Project[]>("/me/projects"),
  });

  const invoiceTotals = useMemo(
    () => gstBreakdown(invoiceForm.taxable_amount, invoiceForm.gst_percent),
    [invoiceForm.taxable_amount, invoiceForm.gst_percent],
  );

  const suggestInvoice = useMutation({
    mutationFn: () => {
      const d = new Date(invoiceForm.invoice_date);
      return api<InvoiceSuggest>(
        `/invoices/suggest?project_id=${invoiceForm.project_id}&year=${d.getFullYear()}&month=${d.getMonth() + 1}&gst_percent=${invoiceForm.gst_percent}`,
      );
    },
    onSuccess: (data) => {
      setInvoiceForm((p) => ({
        ...p,
        taxable_amount: data.taxable_amount,
        gst_percent: data.gst_percent,
      }));
      setSuggestHint(data.detail);
    },
  });

  const createInvoice = useMutation({
    mutationFn: () =>
      api("/invoices", {
        method: "POST",
        body: JSON.stringify({
          project_id: invoiceForm.project_id,
          invoice_no: invoiceForm.invoice_no || null,
          invoice_date: invoiceForm.invoice_date,
          taxable_amount: invoiceForm.taxable_amount,
          gst_percent: invoiceForm.gst_percent,
          note: invoiceForm.note,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["invoices"] });
      void qc.invalidateQueries({ queryKey: ["invoices-open"] });
      setAddInvoice(false);
      setEditInvoice(null);
    },
  });
  const updateInvoice = useMutation({
    mutationFn: () =>
      api(`/invoices/${editInvoice?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          project_id: invoiceForm.project_id,
          invoice_no: invoiceForm.invoice_no || null,
          invoice_date: invoiceForm.invoice_date,
          taxable_amount: invoiceForm.taxable_amount,
          gst_percent: invoiceForm.gst_percent,
          note: invoiceForm.note,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["invoices"] });
      void qc.invalidateQueries({ queryKey: ["invoices-open"] });
      void qc.invalidateQueries({ queryKey: ["payments"] });
      setAddInvoice(false);
      setEditInvoice(null);
    },
  });
  const createPayment = useMutation({
    mutationFn: () =>
      api(`/invoices/${payForm.invoice_id}/payments`, {
        method: "POST",
        body: JSON.stringify({
          amount: payForm.amount,
          received_date: payForm.received_date,
          note: payForm.note,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["invoices"] });
      void qc.invalidateQueries({ queryKey: ["invoices-open"] });
      void qc.invalidateQueries({ queryKey: ["payments"] });
      setAddPayment(false);
      setEditPayment(null);
    },
  });
  const updatePayment = useMutation({
    mutationFn: () =>
      api(`/payments/${editPayment?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          invoice_id: payForm.invoice_id || editPayment?.invoice_id,
          amount: payForm.amount,
          received_date: payForm.received_date,
          note: payForm.note,
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["invoices"] });
      void qc.invalidateQueries({ queryKey: ["invoices-open"] });
      void qc.invalidateQueries({ queryKey: ["payments"] });
      setAddPayment(false);
      setEditPayment(null);
    },
  });

  function openEditInvoice(row: ProjectInvoice) {
    setEditInvoice(row);
    setInvoiceForm({
      project_id: row.project_id,
      invoice_no: row.invoice_no,
      invoice_date: row.invoice_date,
      taxable_amount: row.taxable_amount ?? row.amount,
      gst_percent: row.gst_percent ?? "18",
      note: row.note || "",
    });
    setSuggestHint("");
    setAddInvoice(true);
  }

  function openEditPayment(row: ProjectPayment) {
    setEditPayment(row);
    setPayForm({
      invoice_id: row.invoice_id || "",
      amount: row.amount,
      received_date: row.received_date,
      note: row.note || "",
    });
    setAddPayment(true);
  }

  const selectedOpen = outstanding.data?.find((row) => row.id === payForm.invoice_id);
  const q = search.trim().toLowerCase();
  const matchNo = (row: { invoice_no?: string | null; project_name?: string | null }) =>
    !q || `${row.invoice_no ?? ""} ${row.project_name ?? ""}`.toLowerCase().includes(q);
  const openRows = (outstanding.data ?? []).filter(matchNo);
  const monthRows = (invoices.data ?? []).filter(matchNo);
  const payRows = (payments.data ?? []).filter(matchNo);

  return (
    <div className="space-y-6">
      <p className="max-w-3xl text-sm text-ink/60">
        Raise each invoice as its own numbered row. Record cash against that invoice — even if the money arrives in a
        later month. Two invoices never overwrite each other.
      </p>
      <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
      <Input
        placeholder="Search invoice number or project"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-md"
      />

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-2xl">Still outstanding</h3>
        </div>
        {openRows.length ? (
          openRows.map((row) => (
            <Card key={row.id} className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold">
                  {row.invoice_no} · {row.project_name}
                </p>
                <p className="text-sm text-ink/60">
                  Raised {row.invoice_date} · {money(row.outstanding)} still due of {money(row.amount)}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={statusTone(row.status)}>{row.status}</Badge>
                <IconButton label="Edit invoice" onClick={() => openEditInvoice(row)} />
              </div>
            </Card>
          ))
        ) : (
          <Card className="text-sm text-ink/60">Nothing outstanding.</Card>
        )}
      </section>

      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-2xl">Invoices raised this month</h3>
          <Button
            onClick={() => {
              setEditInvoice(null);
              setInvoiceForm({
                project_id: "",
                invoice_no: "",
                invoice_date: now.toISOString().slice(0, 10),
                taxable_amount: "",
                gst_percent: "18",
                note: "",
              });
              setSuggestHint("");
              setAddInvoice(true);
            }}
          >
            Add invoice
          </Button>
        </div>
        <Card className="overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-mist text-xs uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Taxable</th>
                <th className="px-4 py-3">GST</th>
                <th className="px-4 py-3">Total</th>
                <th className="px-4 py-3">Received</th>
                <th className="px-4 py-3">Outstanding</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {monthRows.map((row) => (
                <tr key={row.id} className="border-t border-ink/5">
                  <td className="px-4 py-3 font-semibold">{row.invoice_no}</td>
                  <td className="px-4 py-3">{row.project_name}</td>
                  <td className="px-4 py-3">{row.invoice_date}</td>
                  <td className="px-4 py-3">{money(row.taxable_amount ?? row.amount)}</td>
                  <td className="px-4 py-3">
                    {money(row.gst_amount ?? "0")} ({row.gst_percent ?? "0"}%)
                  </td>
                  <td className="px-4 py-3 font-semibold">{money(row.amount)}</td>
                  <td className="px-4 py-3">{money(row.received)}</td>
                  <td className="px-4 py-3">{money(row.outstanding)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={statusTone(row.status)}>{row.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <IconButton label="Edit invoice" onClick={() => openEditInvoice(row)} />
                  </td>
                </tr>
              ))}
              {!monthRows.length && (
                <tr>
                  <td className="px-4 py-6 text-ink/50" colSpan={10}>
                    No invoices dated in this month.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Card>
      </section>

      {staff && (
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-display text-2xl">Payments received this month</h3>
            <Button
              variant="outline"
              onClick={() => {
                setEditPayment(null);
                setPayForm({
                  invoice_id: "",
                  amount: "",
                  received_date: now.toISOString().slice(0, 10),
                  note: "",
                });
                setAddPayment(true);
              }}
              disabled={!outstanding.data?.length}
            >
              Record received
            </Button>
          </div>
          {payRows.map((row) => (
            <Card key={row.id} className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-semibold">
                  {row.invoice_no || "Unlinked"} · {row.project_name}
                </p>
                <p className="text-sm text-ink/60">
                  {money(row.amount)} on {row.received_date}
                  {row.against_earlier_invoice ? " · against an earlier invoice" : ""}
                </p>
              </div>
              <IconButton label="Edit payment" onClick={() => openEditPayment(row)} />
            </Card>
          ))}
          {!payRows.length && <Card className="text-sm text-ink/60">No cash received this month.</Card>}
        </section>
      )}

      <Modal
        open={addInvoice}
        title={editInvoice ? "Edit invoice" : "Raise invoice"}
        onClose={() => {
          setAddInvoice(false);
          setEditInvoice(null);
        }}
      >
        <div className="grid gap-3">
          <div>
            <Label>Invoice number</Label>
            <Input
              value={invoiceForm.invoice_no}
              onChange={(e) => setInvoiceForm((p) => ({ ...p, invoice_no: e.target.value }))}
              placeholder="e.g. SKY/2026/014"
            />
            {!editInvoice ? (
              <p className="mt-1 text-xs text-ink/50">Leave blank to auto-assign INV-0001, INV-0002, …</p>
            ) : null}
          </div>
          <div>
            <Label>Project</Label>
            <Select
              value={invoiceForm.project_id}
              onChange={(e) => {
                setSuggestHint("");
                setInvoiceForm((p) => ({ ...p, project_id: e.target.value }));
              }}
            >
              <option value="">Select project</option>
              {projects.data?.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </Select>
            {invoiceForm.project_id ? (
              <Button
                type="button"
                variant="outline"
                className="mt-2"
                disabled={suggestInvoice.isPending}
                onClick={() => suggestInvoice.mutate()}
              >
                {suggestInvoice.isPending ? "Calculating…" : "Auto-calculate from approved hours"}
              </Button>
            ) : null}
            {suggestHint ? <p className="mt-1 text-xs text-ink/50">{suggestHint}</p> : null}
          </div>
          <div>
            <Label>Invoice date</Label>
            <Input
              type="date"
              value={invoiceForm.invoice_date}
              onChange={(e) => setInvoiceForm((p) => ({ ...p, invoice_date: e.target.value }))}
            />
          </div>
          <div>
            <Label>Taxable amount (before GST)</Label>
            <Input
              value={invoiceForm.taxable_amount}
              onChange={(e) => setInvoiceForm((p) => ({ ...p, taxable_amount: e.target.value }))}
            />
          </div>
          <div>
            <Label>GST %</Label>
            <Input
              value={invoiceForm.gst_percent}
              onChange={(e) => setInvoiceForm((p) => ({ ...p, gst_percent: e.target.value }))}
            />
          </div>
          <Card className="bg-mist/40 text-sm">
            <p>GST: {money(invoiceTotals.gst)}</p>
            <p className="mt-1 font-semibold">Invoice total: {money(invoiceTotals.total)}</p>
          </Card>
          <div>
            <Label>Note</Label>
            <Input value={invoiceForm.note} onChange={(e) => setInvoiceForm((p) => ({ ...p, note: e.target.value }))} />
          </div>
          {(editInvoice ? updateInvoice.error : createInvoice.error) ? (
            <p className="text-sm text-red-700">{(editInvoice ? updateInvoice.error : createInvoice.error)?.message}</p>
          ) : null}
          <Button
            onClick={() => (editInvoice ? updateInvoice.mutate() : createInvoice.mutate())}
            disabled={!invoiceForm.project_id || !invoiceForm.taxable_amount}
          >
            {editInvoice ? "Save changes" : "Save invoice"}
          </Button>
        </div>
      </Modal>

      <Modal
        open={addPayment}
        title={editPayment ? "Edit payment received" : "Record payment received"}
        onClose={() => {
          setAddPayment(false);
          setEditPayment(null);
        }}
      >
        <div className="grid gap-3">
          <div>
            <Label>Invoice</Label>
            <Select
              value={payForm.invoice_id}
              onChange={(e) => {
                const next = outstanding.data?.find((row) => row.id === e.target.value);
                setPayForm((p) => ({ ...p, invoice_id: e.target.value, amount: next?.outstanding ?? p.amount }));
              }}
            >
              <option value="">Choose an open invoice</option>
              {editPayment?.invoice_id && !outstanding.data?.some((row) => row.id === editPayment.invoice_id) ? (
                <option value={editPayment.invoice_id}>
                  {editPayment.invoice_no} · {editPayment.project_name}
                </option>
              ) : null}
              {outstanding.data?.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.invoice_no} · {row.project_name} · {row.invoice_date} · due {money(row.outstanding)}
                </option>
              ))}
            </Select>
          </div>
          {selectedOpen ? (
            <p className="text-sm text-ink/60">
              {selectedOpen.invoice_no} still has {money(selectedOpen.outstanding)} open.
            </p>
          ) : null}
          <div>
            <Label>Received date</Label>
            <Input
              type="date"
              value={payForm.received_date}
              onChange={(e) => setPayForm((p) => ({ ...p, received_date: e.target.value }))}
            />
          </div>
          <div>
            <Label>Amount</Label>
            <Input value={payForm.amount} onChange={(e) => setPayForm((p) => ({ ...p, amount: e.target.value }))} />
          </div>
          {(editPayment ? updatePayment.error : createPayment.error) ? (
            <p className="text-sm text-red-700">{(editPayment ? updatePayment.error : createPayment.error)?.message}</p>
          ) : null}
          <Button
            onClick={() => (editPayment ? updatePayment.mutate() : createPayment.mutate())}
            disabled={!payForm.invoice_id || !payForm.amount}
          >
            {editPayment ? "Save changes" : "Save payment"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
