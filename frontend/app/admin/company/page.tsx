"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Button, Card, Input, Label, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import type { CompanyProfile } from "@/lib/types";

export default function CompanyPage() {
  const qc = useQueryClient();
  const profile = useQuery({ queryKey: ["company"], queryFn: () => api<CompanyProfile>("/super/company") });
  const [form, setForm] = useState({
    legal_name: "Skyreon",
    address: "",
    phone: "",
    website: "https://www.skyreon.com",
    signatory_name: "",
    signatory_title: "",
    signature_image: null as string | null,
  });
  useEffect(() => {
    if (!profile.data) return;
    setForm((prev) => ({
      ...prev,
      legal_name: profile.data.legal_name,
      address: profile.data.address,
      phone: profile.data.phone,
      website: profile.data.website,
      signatory_name: profile.data.signatory_name,
      signatory_title: profile.data.signatory_title,
    }));
  }, [profile.data]);
  const save = useMutation({
    mutationFn: () => api("/super/company", { method: "PUT", body: JSON.stringify(form) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["company"] }),
  });

  return (
    <Card className="max-w-2xl space-y-3">
      <h3 className="font-display text-2xl">Company letterhead</h3>
      <p className="text-sm text-ink/60">Used on payslips. Upload the authorized signature photo when you have it.</p>
      {(["legal_name", "phone", "website", "signatory_name", "signatory_title"] as const).map((key) => (
        <div key={key}>
          <Label>{key.replace("_", " ")}</Label>
          <Input value={form[key]} onChange={(e) => setForm((p) => ({ ...p, [key]: e.target.value }))} />
        </div>
      ))}
      <div>
        <Label>Address</Label>
        <Textarea value={form.address} onChange={(e) => setForm((p) => ({ ...p, address: e.target.value }))} />
      </div>
      <div>
        <Label>Signature image</Label>
        <Input
          type="file"
          accept="image/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => setForm((p) => ({ ...p, signature_image: String(reader.result) }));
            reader.readAsDataURL(file);
          }}
        />
        <p className="mt-1 text-xs text-ink/50">{profile.data?.has_signature ? "A signature is already stored." : "No signature uploaded yet."}</p>
      </div>
      {save.error ? <p className="text-sm text-red-700">{save.error.message}</p> : null}
      <Button onClick={() => save.mutate()}>Save letterhead</Button>
    </Card>
  );
}
