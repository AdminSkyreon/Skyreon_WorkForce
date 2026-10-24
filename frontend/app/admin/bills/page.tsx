"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { MonthPicker, money } from "@/components/period";
import { Badge, Button, Card, IconButton, Input, Label, Modal, Select } from "@/components/ui";
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

export default function BillsPage() {
  const now = new Date();
  const qc = useQueryClient();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<VendorBill | null>(null);
  const [form, setForm] = useState({
    vendor_name: "",
    category: "ca_audit",
    amount: "",
    gst_percent: "18",
    bill_date: now.toISOString().slice(0, 10),
    note: "",
  });
  const billTotals = useMemo(() => gstBreakdown(form.amount, form.gst_percent), [form.amount, form.gst_percent]);
  const bills = useQuery({
    queryKey: ["bills", year, month],
    queryFn: () => api<VendorBill[]>(`/bills?year=${year}&month=${month}`),
  });
  const create = useMutation({
    mutationFn: () =>
      api("/bills", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          gst_amount: billTotals.gst,
          year: Number(year),
          month: Number(month),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bills"] });
      setOpen(false);
      setEditing(null);
    },
  });
  const update = useMutation({
    mutationFn: () =>
      api(`/bills/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ ...form, gst_amount: billTotals.gst }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bills"] });
      setOpen(false);
      setEditing(null);
    },
  });
  const pay = useMutation({
    mutationFn: (id: string) =>
      api(`/bills/${id}/paid?paid_date=${now.toISOString().slice(0, 10)}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["bills"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink/60">CA, GST filing, rent and tools are vendor bills — not a GST return product.</p>
        <Button
          onClick={() => {
            setEditing(null);
            setForm({
              vendor_name: "",
              category: "ca_audit",
              amount: "",
              gst_percent: "18",
              bill_date: now.toISOString().slice(0, 10),
              note: "",
            });
            setOpen(true);
          }}
        >
          Add bill
        </Button>
      </div>
      <MonthPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
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
            {bill.status !== "paid" && <Button onClick={() => pay.mutate(bill.id)}>Mark paid</Button>}
          </div>
        </Card>
      ))}
      {!bills.data?.length && <Card>No vendor bills this month.</Card>}
      <Modal open={open} title={editing ? "Edit vendor bill" : "Vendor bill"} onClose={() => { setOpen(false); setEditing(null); }}>
        <div className="grid gap-3">
          <div>
            <Label>Vendor</Label>
            <Input value={form.vendor_name} onChange={(e) => setForm((p) => ({ ...p, vendor_name: e.target.value }))} />
          </div>
          <div>
            <Label>Category</Label>
            <Select value={form.category} onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}>
              {categories.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label>Amount (before GST)</Label>
            <Input value={form.amount} onChange={(e) => setForm((p) => ({ ...p, amount: e.target.value }))} />
          </div>
          <div>
            <Label>GST %</Label>
            <Input value={form.gst_percent} onChange={(e) => setForm((p) => ({ ...p, gst_percent: e.target.value }))} />
          </div>
          <Card className="bg-mist/40 text-sm">
            <p>GST: {money(billTotals.gst)}</p>
            <p className="mt-1 font-semibold">Payable total: {money(billTotals.total)}</p>
          </Card>
          <div>
            <Label>Bill date</Label>
            <Input type="date" value={form.bill_date} onChange={(e) => setForm((p) => ({ ...p, bill_date: e.target.value }))} />
          </div>
          {(editing ? update.error : create.error) ? (
            <p className="text-sm text-red-700">{(editing ? update.error : create.error)?.message}</p>
          ) : null}
          <Button onClick={() => (editing ? update.mutate() : create.mutate())}>
            {editing ? "Save changes" : "Save bill"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
