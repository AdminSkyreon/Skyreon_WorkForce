"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import type { AdminAccount } from "@/lib/types";

export default function AdminsPage() {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("TempPass123");
  const admins = useQuery({ queryKey: ["admins"], queryFn: () => api<AdminAccount[]>("/super/admins") });
  const create = useMutation({
    mutationFn: () => api("/super/admins", { method: "POST", body: JSON.stringify({ email, name, temporary_password: password }) }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admins"] });
      setEmail("");
      setName("");
    },
  });
  const deactivate = useMutation({
    mutationFn: (id: string) => api(`/super/admins/${id}/deactivate`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admins"] }),
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
      <Card className="space-y-3">
        <h3 className="font-display text-2xl">Admin accounts</h3>
        {admins.data?.map((admin) => (
          <div key={admin.id} className="flex items-center justify-between rounded-2xl bg-mist p-4">
            <div>
              <p className="font-semibold">{admin.email}</p>
              <Badge tone={admin.is_active ? "good" : "bad"}>{admin.is_active ? "active" : "inactive"}</Badge>
            </div>
            {admin.is_active && (
              <Button
                variant="ghost"
                loading={deactivate.isPending && deactivate.variables === admin.id}
                onClick={() => deactivate.mutate(admin.id)}
              >
                Deactivate
              </Button>
            )}
          </div>
        ))}
      </Card>
      <Card>
        <h3 className="font-display text-2xl">Add admin</h3>
        <div className="mt-4 space-y-3">
          <div><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} /></div>
          <div><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div><Label>Temporary password</Label><Input value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          {create.error ? <p className="text-sm text-red-700">{create.error.message}</p> : null}
          <Button loading={create.isPending} onClick={() => create.mutate()} disabled={!email || !name}>
            {create.isPending ? "Creating..." : "Create admin"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
