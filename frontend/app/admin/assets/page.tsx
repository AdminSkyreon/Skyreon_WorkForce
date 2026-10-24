"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { CompanyAsset, Employee, Page } from "@/lib/types";

export default function AssetsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CompanyAsset | null>(null);
  const [form, setForm] = useState({ name: "", asset_tag: "", category: "laptop", note: "" });
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => api<CompanyAsset[]>("/assets") });
  const people = useQuery({
    queryKey: ["employees", "assets"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });
  const create = useMutation({
    mutationFn: () => api("/assets", { method: "POST", body: JSON.stringify(form) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      setOpen(false);
      setEditing(null);
    },
  });
  const update = useMutation({
    mutationFn: () => api(`/assets/${editing?.id}`, { method: "PATCH", body: JSON.stringify(form) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      setOpen(false);
      setEditing(null);
    },
  });
  const assign = useMutation({
    mutationFn: ({ id, employeeId }: { id: string; employeeId: string }) =>
      api(`/assets/${id}/assign?employee_id=${employeeId}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });
  const ret = useMutation({
    mutationFn: (id: string) => api(`/assets/${id}/return`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assets"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Assign a laptop or phone, wait for acknowledgement, return it before deactivating someone.</p>
        <Button
          onClick={() => {
            setEditing(null);
            setForm({ name: "", asset_tag: "", category: "laptop", note: "" });
            setOpen(true);
          }}
        >
          Add asset
        </Button>
      </div>
      {assets.data?.map((asset) => (
        <Card key={asset.id} className="grid gap-3 md:grid-cols-[1fr_1fr_auto] md:items-center">
          <div>
            <p className="font-semibold">{asset.name}</p>
            <p className="text-xs text-ink/50">{asset.asset_tag} · {asset.category}</p>
          </div>
          <div>
            <Badge tone={asset.status === "assigned" ? "warn" : "good"}>{asset.status}</Badge>
            {asset.assigned_to_name && (
              <p className="mt-1 text-sm">{asset.assigned_to_name} {asset.acknowledged ? "· acknowledged" : "· waiting"}</p>
            )}
          </div>
          <div className="flex items-center justify-end gap-2">
            <IconButton
              label="Edit asset"
              onClick={() => {
                setEditing(asset);
                setForm({
                  name: asset.name,
                  asset_tag: asset.asset_tag,
                  category: asset.category,
                  note: asset.note || "",
                });
                setOpen(true);
              }}
            />
            {asset.status === "assigned" ? (
              <Button variant="outline" onClick={() => ret.mutate(asset.id)}>
                Return
              </Button>
            ) : (
              <Select onChange={(e) => e.target.value && assign.mutate({ id: asset.id, employeeId: e.target.value })}>
                <option value="">Assign…</option>
                {people.data?.items.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.name}
                  </option>
                ))}
              </Select>
            )}
          </div>
        </Card>
      ))}
      <Modal open={open} title={editing ? "Edit asset" : "New asset"} onClose={() => { setOpen(false); setEditing(null); }}>
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} />
          </div>
          <div>
            <Label>Tag</Label>
            <Input value={form.asset_tag} onChange={(e) => setForm((p) => ({ ...p, asset_tag: e.target.value }))} />
          </div>
          {(editing ? update.error : create.error) ? (
            <p className="text-sm text-red-700">{(editing ? update.error : create.error)?.message}</p>
          ) : null}
          <Button onClick={() => (editing ? update.mutate() : create.mutate())}>
            {editing ? "Save changes" : "Save"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
