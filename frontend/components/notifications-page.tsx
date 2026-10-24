"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { Notification } from "@/lib/types";

export function NotificationsPage() {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => api<Notification[]>("/me/notifications"),
  });
  const read = useMutation({
    mutationFn: (id: string) => api(`/me/notifications/${id}/read`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <div className="space-y-3">
      {data?.length === 0 && <Card>No notifications yet.</Card>}
      {data?.map((item) => (
        <Card key={item.id} className={item.is_read ? "opacity-60" : ""}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-display text-2xl">{item.title}</h3>
              <p className="text-sm text-ink/70">{item.body}</p>
              {item.link && (
                <Link href={item.link} className="mt-2 inline-block text-sm text-forest underline">
                  Open
                </Link>
              )}
            </div>
            {!item.is_read && (
              <button className="text-sm text-copper" onClick={() => read.mutate(item.id)}>
                Mark read
              </button>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}
