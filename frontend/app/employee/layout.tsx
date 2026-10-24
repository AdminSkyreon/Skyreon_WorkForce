"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  CalendarCheck,
  CalendarDays,
  FileText,
  FolderKanban,
  Laptop,
  LayoutDashboard,
  ListChecks,
  Palmtree,
  Receipt,
  Star,
  Users,
  Wallet,
} from "lucide-react";
import { AppShell, type NavLink, type NavSection } from "@/components/app-shell";
import { PageSkeleton } from "@/components/page-skeleton";
import { useAuth } from "@/lib/auth";

export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    if (!user) window.location.replace("/login");
  }, [user, loading, router]);

  const nav = useMemo(() => {
    const sections: NavSection[] = [
      {
        title: "Work",
        items: [
          { href: "/employee/dashboard", label: "Dashboard", icon: LayoutDashboard },
          { href: "/employee/projects", label: "Projects", icon: FolderKanban },
          { href: "/employee/tasks", label: "My Tasks", icon: ListChecks },
          { href: "/employee/timesheet", label: "Timesheet", icon: CalendarDays },
        ],
      },
      {
        title: "Me",
        items: [
          { href: "/employee/attendance", label: "Attendance", icon: CalendarCheck },
          { href: "/employee/leave", label: "Leave", icon: Palmtree },
          { href: "/employee/reimbursements", label: "Reimbursements", icon: Receipt },
          { href: "/employee/documents", label: "Documents", icon: FileText },
          { href: "/employee/assets", label: "Assets", icon: Laptop },
          { href: "/employee/reviews", label: "Reviews", icon: Star },
          { href: "/employee/payslips", label: "My payslips", icon: Wallet },
        ],
      },
    ];

    if (user?.is_people_manager || user?.is_project_manager) {
      const team: NavLink[] = [];
      if (user.is_people_manager) team.push({ href: "/employee/team", label: "My team", icon: Users });
      if (user.is_project_manager) {
        team.push({ href: "/employee/team-timesheets", label: "Team timesheets", icon: CalendarDays });
        team.push({ href: "/employee/billing", label: "Project billing", icon: Wallet });
      }
      sections.push({ title: "Team", items: team });
    }

    sections.push({
      title: "More",
      items: [{ href: "/employee/notifications", label: "Notifications", icon: Bell }],
    });
    return sections;
  }, [user?.is_people_manager, user?.is_project_manager]);

  if (loading) {
    return (
      <div className="min-h-screen bg-paper p-4 sm:p-6 lg:pl-64">
        <PageSkeleton />
      </div>
    );
  }
  if (!user) return <div className="flex min-h-screen items-center justify-center bg-paper text-ink/50">Taking you to sign in…</div>;

  return (
    <AppShell title="My workspace" nav={nav}>
      {children}
    </AppShell>
  );
}
