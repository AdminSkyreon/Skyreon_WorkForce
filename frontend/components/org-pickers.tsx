"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Input, Label, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Location, NamedOption } from "@/lib/types";

const FIFTEEN_MINUTES = 15 * 60 * 1000;

export function DepartmentSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const items = useQuery({
    queryKey: ["departments"],
    queryFn: () => api<NamedOption[]>("/departments"),
    staleTime: FIFTEEN_MINUTES,
  });
  const create = useMutation({
    mutationFn: () => api<NamedOption>("/departments", { method: "POST", body: JSON.stringify({ name }) }),
    onSuccess: (row) => {
      void qc.invalidateQueries({ queryKey: ["departments"] });
      onChange(row.name);
      setAdding(false);
      setName("");
    },
  });
  return (
    <div>
      <Label>Department</Label>
      {adding ? (
        <div className="flex gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New department" />
          <Button type="button" onClick={() => create.mutate()} disabled={!name.trim()}>
            Save
          </Button>
        </div>
      ) : (
        <div className="flex gap-2">
          <Select value={value} onChange={(e) => onChange(e.target.value)}>
            <option value="">Select</option>
            {items.data?.map((row) => (
              <option key={row.id} value={row.name}>
                {row.name}
              </option>
            ))}
          </Select>
          <Button type="button" variant="outline" onClick={() => setAdding(true)}>
            Add
          </Button>
        </div>
      )}
    </div>
  );
}

export function DesignationSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const items = useQuery({
    queryKey: ["designations"],
    queryFn: () => api<NamedOption[]>("/designations"),
    staleTime: FIFTEEN_MINUTES,
  });
  const create = useMutation({
    mutationFn: () => api<NamedOption>("/designations", { method: "POST", body: JSON.stringify({ name }) }),
    onSuccess: (row) => {
      void qc.invalidateQueries({ queryKey: ["designations"] });
      onChange(row.name);
      setAdding(false);
      setName("");
    },
  });
  return (
    <div>
      <Label>Designation</Label>
      {adding ? (
        <div className="flex gap-2">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New designation" />
          <Button type="button" onClick={() => create.mutate()} disabled={!name.trim()}>
            Save
          </Button>
        </div>
      ) : (
        <div className="flex gap-2">
          <Select value={value} onChange={(e) => onChange(e.target.value)}>
            <option value="">Select</option>
            {items.data?.map((row) => (
              <option key={row.id} value={row.name}>
                {row.name}
              </option>
            ))}
          </Select>
          <Button type="button" variant="outline" onClick={() => setAdding(true)}>
            Add
          </Button>
        </div>
      )}
    </div>
  );
}

export function LocationSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const items = useQuery({
    queryKey: ["locations"],
    queryFn: () => api<Location[]>("/admin/locations"),
    staleTime: FIFTEEN_MINUTES,
  });
  return (
    <div>
      <Label>Office location</Label>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">Select</option>
        {items.data?.map((loc) => (
          <option key={loc.id} value={loc.id}>
            {loc.name} ({loc.city})
          </option>
        ))}
      </Select>
    </div>
  );
}