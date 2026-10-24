import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatHours(seconds: number): string {
  const abs = Math.abs(seconds);
  const h = Math.floor(abs / 3600);
  const m = Math.floor((abs % 3600) / 60);
  const s = abs % 60;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${h}:${pad(m)}:${pad(s)}`;
}

export function remainingLabel(remainingSeconds: number): string {
  if (remainingSeconds >= 0) return formatHours(remainingSeconds);
  return `+${formatHours(remainingSeconds)}`;
}

export const labels = {
  projectStatus: {
    planned: "Planned",
    active: "Active",
    on_hold: "On Hold",
    completed: "Completed",
  } as Record<string, string>,
  contract: {
    fixed: "Fixed",
    time_and_material: "Time & Material",
  } as Record<string, string>,
  taskStatus: {
    not_started: "Not Started",
    in_progress: "In Progress",
    paused: "Paused",
    completed: "Completed",
  } as Record<string, string>,
  priority: {
    low: "Low",
    medium: "Medium",
    high: "High",
  } as Record<string, string>,
  leave: {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    cancelled: "Cancelled",
  } as Record<string, string>,
  timesheet: {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    rejected: "Rejected",
  } as Record<string, string>,
};
