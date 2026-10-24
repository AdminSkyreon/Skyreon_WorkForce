"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Card, IconButton, Input, Label, Modal, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Holiday, Location } from "@/lib/types";

export default function HolidaysPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [locationId, setLocationId] = useState("");
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<Holiday | null>(null);
  const [editName, setEditName] = useState("");
  const [editDate, setEditDate] = useState("");
  const [editLocationId, setEditLocationId] = useState("");
  const locations = useQuery({ queryKey: ["locations-admin"], queryFn: () => api<Location[]>("/admin/locations") });
  const { data } = useQuery({
    queryKey: ["holidays", filter],
    queryFn: () => api<Holiday[]>(`/holidays${filter ? `?location_id=${filter}` : ""}`),
  });
  const create = useMutation({
    mutationFn: () =>
      api("/admin/holidays", {
        method: "POST",
        body: JSON.stringify({ name, date, location_id: locationId || null }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["holidays"] });
      setName("");
      setDate("");
    },
  });
  const update = useMutation({
    mutationFn: () =>
      api(`/admin/holidays/${editing?.id}`, {
        method: "PATCH",
        body: JSON.stringify({ name: editName, date: editDate, location_id: editLocationId || null }),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["holidays"] });
      setEditing(null);
    },
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/admin/holidays/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["holidays"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="space-y-4">
        <Select value={filter} onChange={(e) => setFilter(e.target.value)} className="max-w-xs">
          <option value="">All locations + company-wide</option>
          {locations.data?.map((loc) => (
            <option key={loc.id} value={loc.id}>
              {loc.name}
            </option>
          ))}
        </Select>
        <Card className="p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-mist text-xs uppercase text-ink/60">
              <tr>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Holiday</th>
                <th className="px-4 py-3">Location</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data?.map((h) => (
                <tr key={h.id} className="border-t border-ink/5">
                  <td className="px-4 py-3">{h.date}</td>
                  <td className="px-4 py-3 font-semibold">{h.name}</td>
                  <td className="px-4 py-3">{h.location_name || "All locations"}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <IconButton
                        label="Edit holiday"
                        onClick={() => {
                          setEditing(h);
                          setEditName(h.name);
                          setEditDate(h.date);
                          setEditLocationId(h.location_id || "");
                        }}
                      />
                      <Button variant="ghost" onClick={() => remove.mutate(h.id)}>
                        Remove
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <Card>
        <h3 className="font-display text-2xl">Add holiday</h3>
        <p className="mt-1 text-sm text-ink/60">Leave location empty for a company-wide holiday.</p>
        <div className="mt-4 space-y-3">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label>Date</Label>
            <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          <div>
            <Label>Location</Label>
            <Select value={locationId} onChange={(e) => setLocationId(e.target.value)}>
              <option value="">All locations</option>
              {locations.data
                ?.filter((loc) => loc.is_active)
                .map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
            </Select>
          </div>
          <Button onClick={() => create.mutate()}>Save</Button>
        </div>
      </Card>
      <Modal open={!!editing} title="Edit holiday" onClose={() => setEditing(null)}>
        <div className="grid gap-3">
          <div>
            <Label>Name</Label>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </div>
          <div>
            <Label>Date</Label>
            <Input type="date" value={editDate} onChange={(e) => setEditDate(e.target.value)} />
          </div>
          <div>
            <Label>Location</Label>
            <Select value={editLocationId} onChange={(e) => setEditLocationId(e.target.value)}>
              <option value="">All locations</option>
              {locations.data
                ?.filter((loc) => loc.is_active)
                .map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
            </Select>
          </div>
          {update.error ? <p className="text-sm text-red-700">{update.error.message}</p> : null}
          <Button onClick={() => update.mutate()} disabled={!editName || !editDate}>
            Save changes
          </Button>
        </div>
      </Modal>
    </div>
  );
}
