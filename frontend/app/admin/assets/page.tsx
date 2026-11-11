"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, FieldError, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { toast } from "@/components/toast";
import { api } from "@/lib/api";
import type { CompanyAsset, Employee, Page } from "@/lib/types";

export default function AssetsPage() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CompanyAsset | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({ name: "", asset_tag: "", category: "laptop", note: "" });
  const assets = useQuery({ queryKey: ["assets"], queryFn: () => api<CompanyAsset[]>("/assets") });
  const people = useQuery({
    queryKey: ["employees", "assets"],
    queryFn: () => api<Page<Employee>>("/admin/employees?status=active&page_size=100"),
  });

  const errors = {
    name: !form.name.trim() ? "Asset name is required" : form.name.trim().length > 255 ? "Max 255 characters" : "",
    asset_tag: !form.asset_tag.trim() ? "Asset tag is required" : form.asset_tag.trim().length > 80 ? "Max 80 characters" : "",
  };
  const hasErrors = Object.values(errors).some(Boolean);

  function closeModal() {
    setOpen(false);
    setEditing(null);
    setSubmitted(false);
    create.reset();
    update.reset();
  }

  const create = useMutation({
    mutationFn: () =>
      api("/assets", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          asset_tag: form.asset_tag.trim(),
          category: form.category.trim() || "laptop",
          note: form.note.trim(),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset added");
      closeModal();
    },
  });
  const update = useMutation({
    mutationFn: () =>
      api(`/assets/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: form.name.trim(),
          asset_tag: form.asset_tag.trim(),
          category: form.category.trim() || "laptop",
          note: form.note.trim(),
        }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset updated");
      closeModal();
    },
  });
  const assign = useMutation({
    mutationFn: ({ id, employeeId }: { id: string; employeeId: string }) =>
      api(`/assets/${id}/assign?employee_id=${employeeId}`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset assigned");
    },
  });
  const ret = useMutation({
    mutationFn: (id: string) => api(`/assets/${id}/return`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["assets"] });
      toast.success("Asset returned");
    },
  });

  const isSaving = editing ? update.isPending : create.isPending;

  return (
    <div className="space-y-4">
      <div className="flex justify-between">
        <p className="text-sm text-ink/60">Assign a laptop or phone, wait for acknowledgement, return it before deactivating someone.</p>
        <Button
          onClick={() => {
            create.reset();
            update.reset();
            setSubmitted(false);
            setEditing(null);
            setForm({ name: "", asset_tag: "", category: "laptop", note: "" });
            setOpen(true);
          }}
        >
          Add asset
        </Button>
      </div>
      {assign.error ? <p className="text-sm text-red-700">{assign.error.message}</p> : null}
      {ret.error ? <p className="text-sm text-red-700">{ret.error.message}</p> : null}
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
                create.reset();
                update.reset();
                setSubmitted(false);
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
              <Button
                variant="outline"
                disabled={ret.isPending}
                loading={ret.isPending && ret.variables === asset.id}
                onClick={() => ret.mutate(asset.id)}
              >
                {ret.isPending && ret.variables === asset.id ? "Returning..." : "Return"}
              </Button>
            ) : (
              <Select
                disabled={assign.isPending && assign.variables?.id === asset.id}
                value=""
                onChange={(e) => e.target.value && assign.mutate({ id: asset.id, employeeId: e.target.value })}
              >
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
      <Modal open={open} title={editing ? "Edit asset" : "New asset"} onClose={closeModal}>
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input
              maxLength={255}
              disabled={isSaving}
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
            {submitted && <FieldError message={errors.name} />}
          </div>
          <div>
            <Label>Tag</Label>
            <Input
              maxLength={80}
              disabled={isSaving}
              value={form.asset_tag}
              onChange={(e) => setForm((p) => ({ ...p, asset_tag: e.target.value }))}
            />
            {submitted && <FieldError message={errors.asset_tag} />}
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
              ? isSaving
                ? "Saving..."
                : "Save changes"
              : isSaving
                ? "Saving..."
                : "Save"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
