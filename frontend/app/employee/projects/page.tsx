"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { labels } from "@/lib/utils";

export default function EmployeeProjectsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["my-projects"],
    queryFn: () => api<Project[]>("/me/projects"),
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink/60">
        Open a project to add a task, then start a timer on My Tasks or type hours on your Timesheet.
      </p>
      {isLoading ? <p className="text-sm text-ink/50">Loading projects…</p> : null}
      {!isLoading && !data?.length ? (
        <Card>
          <h3 className="font-display text-2xl">You are not on a project yet</h3>
          <p className="mt-2 text-sm text-ink/60">Ask an admin to add you to a project team. Then you can add tasks and track time.</p>
        </Card>
      ) : null}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.map((project) => (
          <Card key={project.id}>
            <p className="text-xs uppercase tracking-widest text-copper">{project.project_code}</p>
            <h3 className="mt-1 font-display text-3xl">{project.name}</h3>
            <p className="text-sm text-ink/60">{project.client_name}</p>
            <div className="mt-3 flex items-center justify-between gap-3">
              <Badge>{labels.projectStatus[project.status]}</Badge>
              <Link
                href={`/employee/projects/${project.id}`}
                className="inline-flex items-center justify-center rounded-full bg-forest px-4 py-2 text-sm font-semibold text-white hover:bg-[#004e8a]"
              >
                Open project
              </Link>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
