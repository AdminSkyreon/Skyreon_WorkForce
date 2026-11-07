"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { Review } from "@/lib/types";

export default function MyReviewsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["my-reviews"], queryFn: () => api<Review[]>("/me/reviews") });
  const ack = useMutation({
    mutationFn: (id: string) => api(`/me/reviews/${id}/acknowledge`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-reviews"] }),
  });
  return (
    <div className="space-y-3">
      {data?.map((row) => (
        <Card key={row.id}>
          <div className="flex justify-between">
            <p className="font-semibold">Review</p>
            <Badge tone={row.acknowledged ? "good" : "warn"}>{row.acknowledged ? "Acknowledged" : "To acknowledge"}</Badge>
          </div>
          <p className="mt-2 text-sm text-ink/70">{row.summary}</p>
          {!row.acknowledged && (
            <Button
              className="mt-3"
              loading={ack.isPending && ack.variables === row.id}
              onClick={() => ack.mutate(row.id)}
            >
              Acknowledge
            </Button>
          )}
        </Card>
      ))}
      {!data?.length && <Card>No reviews yet.</Card>}
    </div>
  );
}
