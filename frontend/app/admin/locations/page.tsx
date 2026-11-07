"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import type { Location } from "@/lib/types";

export default function LocationsPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [city, setCity] = useState("");
  const [country, setCountry] = useState("India");
  const { data } = useQuery({ queryKey: ["locations-admin"], queryFn: () => api<Location[]>("/admin/locations") });
  const create = useMutation({
    mutationFn: () => api("/admin/locations", { method: "POST", body: JSON.stringify({ name, code, city, country }) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["locations-admin"] });
      void qc.invalidateQueries({ queryKey: ["locations"] });
      setName("");
      setCode("");
      setCity("");
    },
  });
  const toggle = useMutation({
    mutationFn: (loc: Location) =>
      api(`/admin/locations/${loc.id}`, { method: "PATCH", body: JSON.stringify({ is_active: !loc.is_active }) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["locations-admin"] });
      void qc.invalidateQueries({ queryKey: ["locations"] });
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <Card className="p-0">
        <table className="w-full text-left text-sm">
          <thead className="bg-mist text-xs uppercase text-ink/60">
            <tr>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">City</th>
              <th className="px-4 py-3">Country</th>
              <th className="px-4 py-3">Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data?.map((loc) => (
              <tr key={loc.id} className="border-t border-ink/5">
                <td className="px-4 py-3 font-semibold">{loc.name}</td>
                <td className="px-4 py-3">{loc.code}</td>
                <td className="px-4 py-3">{loc.city}</td>
                <td className="px-4 py-3">{loc.country}</td>
                <td className="px-4 py-3">
                  <Badge tone={loc.is_active ? "good" : "bad"}>{loc.is_active ? "Active" : "Inactive"}</Badge>
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="ghost"
                    loading={toggle.isPending && toggle.variables?.id === loc.id}
                    onClick={() => toggle.mutate(loc)}
                  >
                    {loc.is_active ? "Deactivate" : "Activate"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card>
        <h3 className="font-display text-2xl">Add location</h3>
        <p className="mt-1 text-sm text-ink/60">Holidays and payroll can be scoped to a location.</p>
        <div className="mt-4 space-y-3">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label>Code</Label>
            <Input value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div>
            <Label>City</Label>
            <Input value={city} onChange={(e) => setCity(e.target.value)} />
          </div>
          <div>
            <Label>Country</Label>
            <Input value={country} onChange={(e) => setCountry(e.target.value)} />
          </div>
          <Button loading={create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Saving..." : "Save"}</Button>
        </div>
      </Card>
    </div>
  );
}
