"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
  Bell,
  BriefcaseBusiness,
  Building2,
  CalendarCheck,
  CalendarDays,
  CalendarRange,
  Clock,
  FileSpreadsheet,
  Files,
  FolderKanban,
  Handshake,
  Landmark,
  Laptop,
  LayoutDashboard,
  Palmtree,
  PieChart,
  Receipt,
  ScrollText,
  Shield,
  Star,
  Users,
  Wallet,
} from "lucide-react";
import { AppShell, type NavSection } from "@/components/app-shell";
import { PageSkeleton } from "@/components/page-skeleton";
import { useAuth } from "@/lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (loading) return;
    if (!user) window.location.replace("/login");
  }, [user, loading, router]);

  const nav = useMemo(() => {
    const sections: NavSection[] = [
      {
        title: "Overview",
        items: [
          { href: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard },
          { href: "/admin/company-month", label: "Company month", icon: CalendarRange },
        ],
      },
      {
        title: "People",
        items: [
          { href: "/admin/employees", label: "People", icon: Users },
          { href: "/admin/attendance", label: "Attendance", icon: CalendarCheck },
          { href: "/admin/leave", label: "Leave", icon: Palmtree },
          { href: "/admin/extra-work", label: "Extra work", icon: Clock },
          { href: "/admin/hiring", label: "Hiring", icon: BriefcaseBusiness },
          { href: "/admin/documents", label: "Documents", icon: Files },
          { href: "/admin/assets", label: "Assets", icon: Laptop },
          { href: "/admin/reviews", label: "Reviews", icon: Star },
        ],
      },
      {
        title: "Work",
        items: [
          { href: "/admin/projects", label: "Projects", icon: FolderKanban },
          { href: "/admin/timesheets", label: "Timesheets", icon: Clock },
        ],
      },
      {
        title: "Money",
        items: [
          { href: "/admin/reimbursements", label: "Claims", icon: Receipt },
          { href: "/admin/billing", label: "Billing", icon: Wallet },
          { href: "/admin/bills", label: "Vendor bills", icon: FileSpreadsheet },
          { href: "/admin/contractors", label: "Contractors", icon: Handshake },
          { href: "/admin/payroll", label: "Payroll", icon: Landmark },
        ],
      },
      {
        title: "Company",
        items: [
          { href: "/admin/holidays", label: "Holidays", icon: CalendarDays },
          { href: "/admin/notifications", label: "Notifications", icon: Bell },
        ],
      },
    ];
    if (user?.role === "super_admin") {
      sections[3].items.push({ href: "/admin/finance", label: "Finance", icon: PieChart });
      sections[4].items.push(
        { href: "/admin/admins", label: "Admins", icon: Shield },
        { href: "/admin/company", label: "Company", icon: Building2 },
        { href: "/admin/audit", label: "Audit", icon: ScrollText },
      );
    }
    return sections;
  }, [user?.role]);

  if (loading) {
    return (
      <div className="min-h-screen bg-paper p-4 sm:p-6 lg:pl-64">
        <PageSkeleton />
      </div>
    );
  }
  if (!user) return <div className="flex min-h-screen items-center justify-center bg-paper text-ink/50">Taking you to sign in…</div>;

  return (
    <AppShell title={user?.role === "super_admin" ? "Super admin" : "Administration"} nav={nav}>
      {children}
    </AppShell>
  );
}
