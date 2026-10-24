"use client";

import { useQuery } from "@tanstack/react-query";
import { format, startOfMonth } from "date-fns";
import { Badge, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { AttendanceDay } from "@/lib/types";

export default function MyAttendancePage() {
  const start = format(startOfMonth(new Date()), "yyyy-MM-dd");
  const end = format(new Date(), "yyyy-MM-dd");
  const { data } = useQuery({
    queryKey: ["my-attendance"],
    queryFn: () => api<AttendanceDay[]>(`/me/attendance?start=${start}&end=${end}`),
  });
  return (
    <div className="space-y-3">
      <p className="text-sm text-ink/60">Marks for this month.</p>
      {data?.map((row) => (
        <Card key={row.id} className="flex items-center justify-between">
          <p>{row.work_date}</p>
          <Badge>{row.mark.replace("_", " ")}</Badge>
        </Card>
      ))}
      {!data?.length && <Card>No attendance marks yet this month.</Card>}
    </div>
  );
}
