"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format } from "date-fns";
import { useMemo, useState } from "react";
import { MonthPicker, money } from "@/components/period";
import { Badge, Button, Card, FieldError, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import { gstBreakdown } from "@/lib/gst";
import type { VendorBill } from "@/lib/types";

const categories = [
  ["gst_filing", "GST filing"],
  ["ca_audit", "CA / audit"],
  ["legal", "Legal"],
  ["rent_office", "Rent / office"],
  ["tools", "Tools"],
  ["other", "Other"],
] as const;

function isPositiveNumber(val: string) {
  const t = val.trim();
  if (!t) return false;
  const n = Number(t);
  return Number.isFinite(n) && n > 0;
}

function isGstValid(val: string) {
  const t = val.trim();
  if (!t) return false;
  const n = Number(t);
  return Number.isFinite(n) && n >= 0 && n <= 100;
}

export default function BillsPage() {
  const now = new Date();
  const today = format(now, "yyyy-MM-dd");
  const qc = useQueryClient();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<VendorBill | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({
    vendor_name: "",
    category: "ca_audit",
    amount: "",
    gst_percent: "18",
    bill_date: today,
    note: "",
  });

  const billTotals = useMemo(() => gstBreakdown(form.amount, form.gst_percent), [form.amount, form.gst_percent]);
  const errors = {
    vendor_name: !form.vendor_name.trim()
      ? "Vendor name is required"
      : form.vendor_name.trim().length > 255
        ? "Max 255 characters"
        : "",
    amount: !isPositiveNumber(form.amount) ? "Amount must be greater than 0" : "",
    gst_percent: !isGstValid(form.gst_percent) ? "GST % must be between 0 and 100" : "",
    bill_date: !form.bill_date ? "Bill date is required" : "",
  };
  const hasErrors = Object.values(errors).some(Boolean);

  function closeModal() {
    setOpen(false);
    setEditing(null);
    setSubmitted(false);
    create.reset();
    update.reset();
  }

  const bills = useQuery({
    queryKey: ["bills", year, month],
    queryFn: () => api<VendorBill[]>(`/bills?year=${year}&month=${month}`),
  });
  const create = useMutation({
    mutationFn: () =>
      api<VendorBill>("/bills", {
        method: "POST",
        body: JSON.stringify({
          vendor_name: form.vendor_name.trim(),
          category: form.category,
          amount: form.amount.trim(),
          gst_percent: form.gst_percent.trim(),
          gst_amount: billTotals.gst,
          bill_date: form.bill_date,
          note: form.note.trim(),
        }),
      }),
    onSuccess: (created) => {
      void qc.invalidateQueries({ queryKey: ["bills"] });
      setYear(String(created.year));
      setMonth(String(created.month));
      toast.success("Vendor bill added");
      closeModal();
    },
  });
  const update = useMutation({
    mutationFn: () =>
      api<VendorBill>(`/bills/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          vendor_name: form.vendor_name.trim(),
          category: form.category,
          amount: form.amount.trim(),
          gst_percent: form.gst_percent.trim(),
          gst_amount: billTotals.gst,
          bill_date: form.bill_date,
          note: form.note.trim(),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bills"] });
      toast.success("Vendor bill updated");
      closeModal();
    },
  });
  const pay = useMutation({
    mutationFn: (id: string) =>
      api(`/bills/${id}/paid?paid_date=${today}`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bills"] });
      toast.success("Bill marked paid");
    },
  });

  const isSaving = editing ? update.isPending : create.isPending;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink/60">CA, GST filing, rent and tools are vendor bills — not a GST return product.</p>
        <Button
          onClick={() => {
            create.reset();
            update.reset();
            setSubmitted(false);
            setEditing(null);
            setForm({
              vendor_name: "",
              category: "ca_audit",
              amount: "",
              gst_percent: "18",
              bill_date: today,
              note: "",
            });
            setOpen(true);
          }}
        >
          Add bill
        </Button>
      </div>
      <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
      {pay.error ? <p className="text-sm text-red-700">{pay.error.message}</p> : null}
      {bills.data?.map((bill) => (
        <Card key={bill.id} className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{bill.vendor_name}</p>
            <p className="text-sm text-ink/60">
              {bill.category.replace("_", " ")} · {money(bill.amount)} + GST {money(bill.gst_amount)} ={" "}
              {money(String(Number(bill.amount) + Number(bill.gst_amount)))}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={bill.status === "paid" ? "good" : "warn"}>{bill.status}</Badge>
            <IconButton
              label="Edit bill"
              onClick={() => {
                create.reset();
                update.reset();
                setSubmitted(false);
                setEditing(bill);
                setForm({
                  vendor_name: bill.vendor_name,
                  category: bill.category,
                  amount: bill.amount,
                  gst_percent:
                    Number(bill.amount) > 0
                      ? String(Math.round((Number(bill.gst_amount) / Number(bill.amount)) * 10000) / 100)
                      : "18",
                  bill_date: bill.bill_date,
                  note: bill.note || "",
                });
                setOpen(true);
              }}
            />
            {bill.status !== "paid" && (
              <Button
                disabled={pay.isPending}
                loading={pay.isPending && pay.variables === bill.id}
                onClick={() => pay.mutate(bill.id)}
              >
                {pay.isPending && pay.variables === bill.id ? "Marking paid..." : "Mark paid"}
              </Button>
            )}
          </div>
        </Card>
      ))}
      {!bills.data?.length && <Card>No vendor bills this month.</Card>}
      <Modal open={open} title={editing ? "Edit vendor bill" : "Vendor bill"} onClose={closeModal}>
        <div className="grid gap-3">
          <div>
            <Label>Vendor</Label>
            <Input
              maxLength={255}
              disabled={isSaving}
              value={form.vendor_name}
              onChange={(e) => setForm((p) => ({ ...p, vendor_name: e.target.value }))}
            />
            {submitted && <FieldError message={errors.vendor_name} />}
          </div>
          <div>
            <Label>Category</Label>
            <Select disabled={isSaving} value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}>
              {categories.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Amount (before GST)</Label>
            <Input
              type="number"
              min="0.01"
              step="0.01"
              disabled={isSaving}
              value={form.amount}
              onChange={(e) => setForm((p) => ({ ...p, amount: e.target.value }))}
            />
            {submitted && <FieldError message={errors.amount} />}
          </div>
          <div>
            <Label>GST %</Label>
            <Input
              type="number"
              min="0"
              max="100"
              step="0.01"
              disabled={isSaving}
              value={form.gst_percent}
              onChange={(e) => setForm((p) => ({ ...p, gst_percent: e.target.value }))}
            />
            {submitted && <FieldError message={errors.gst_percent} />}
          </div>
          <Card className="bg-mist/40 text-sm">
            <p>GST: {money(billTotals.gst)}</p>
            <p className="mt-1 font-semibold">Payable total: {money(billTotals.total)}</p>
          </Card>
          <div>
            <Label>Bill date</Label>
            <Input
              type="date"
              disabled={isSaving}
              value={form.bill_date}
              onChange={(e) => setForm((p) => ({ ...p, bill_date: e.target.value }))}
            />
            {submitted && <FieldError message={errors.bill_date} />}
          </div>
          <div>
            <Label>Note</Label>
            <Input
              maxLength={500}
              disabled={isSaving}
              value={form.note}
              onChange={(e) => setForm((p) => ({ ...p, note: e.target.value }))}
            />
          </div>
          {(editing ? update.error : create.error) ? (
            <p className="text-sm text-red-700">{(editing ? update.error : create.error)?.message}</p>
          ) : null}
          <Button
            loading={isSaving}
            onClick={() => {
              setSubmitted(true);
              if (!hasErrors) {
                if (editing) update.mutate();
                else create.mutate();
              }
            }}
          >
            {editing
              ? isSaving ? "Saving..." : "Save changes"
              : isSaving ? "Saving..." : "Save bill"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
