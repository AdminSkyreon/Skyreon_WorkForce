"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { CompanyAsset } from "@/lib/types";

export default function MyAssetsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["my-assets"], queryFn: () => api<CompanyAsset[]>("/me/assets") });
  const ack = useMutation({
    mutationFn: (id: string) => api(`/me/assets/${id}/acknowledge`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-assets"] }),
  });
  return (
    <div className="space-y-3">
      {data?.map((asset) => (
        <Card key={asset.id} className="flex items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{asset.name}</p>
            <p className="text-xs text-ink/50">{asset.asset_tag}</p>
          </div>
          {asset.acknowledged ? (
            <Badge tone="good">Acknowledged</Badge>
          ) : (
            <Button loading={ack.isPending && ack.variables === asset.id} onClick={() => ack.mutate(asset.id)}>{ack.isPending && ack.variables === asset.id ? "Acknowledging..." : "Acknowledge"}</Button>
          )}
        </Card>
      ))}
      {!data?.length && <Card>No assets assigned to you.</Card>}
    </div>
  );
}
