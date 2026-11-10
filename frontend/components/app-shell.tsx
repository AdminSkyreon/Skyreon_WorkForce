"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeftRight, Bell, LogOut, Menu, X, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getAccessToken, refreshAccess } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isStaff } from "@/lib/types";
import { cn } from "@/lib/utils";
import { ChangePasswordModal } from "./change-password-modal";
import { setNavigationLoading } from "./global-loading-indicator";
import { MiniTimer } from "./mini-timer";
import { SkyreonLogo } from "./skyreon-logo";
import { Button, Modal } from "./ui";

export type NavLink = { href: string; label: string; icon?: LucideIcon };
export type NavSection = { title: string; items: NavLink[] };

export function AppShell({
  title,
  nav,
  children,
}: {
  title: string;
  nav: NavSection[];
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const [pendingHref, setPendingHref] = useState<string | null>(null);

  // Logout Confirmation & Loading State
  const [logoutModalOpen, setLogoutModalOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  // When pathname changes (navigation completed), clear the pending state
  useEffect(() => {
    setPendingHref(null);
    setNavigationLoading(false);
  }, [pathname]);

  async function switchPortal(href: string) {
    setSwitching(true);
    setNavigationLoading(true);
    try {
      if (!getAccessToken()) {
        await refreshAccess();
      }
      router.push(href);
    } finally {
      setSwitching(false);
    }
  }

  async function handleConfirmLogout() {
    setIsLoggingOut(true);
    try {
      await logout();
    } catch {
      // Force redirect to login even if network call drops
      window.location.replace("/login");
    } finally {
      setIsLoggingOut(false);
      setLogoutModalOpen(false);
    }
  }

  const notificationsHref = isStaff(user?.role) ? "/admin/notifications" : "/employee/notifications";
  const current = useMemo(() => {
    const flat = nav.flatMap((section) => section.items);
    return [...flat]
      .sort((a, b) => b.href.length - a.href.length)
      .find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`));
  }, [nav, pathname]);

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(`${href}/`);
  }

  function handleNavClick(e: React.MouseEvent, href: string) {
    if (isActive(href)) {
      e.preventDefault();
      return;
    }
    // Instant 0ms visual feedback: mark this item as pending and start progress bar
    setPendingHref(href);
    setNavigationLoading(true);
    setOpen(false);
  }

  const links = (
    <nav className="space-y-3">
      {nav.map((section) => (
        <div key={section.title}>
          <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/35">
            {section.title}
          </p>
          <div className="space-y-0.5">
            {section.items.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              const isPending = pendingHref === item.href;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  prefetch
                  scroll={false}
                  onClick={(e) => handleNavClick(e, item.href)}
                  className={cn(
                    "relative flex items-center justify-between rounded-lg px-3 py-1.5 text-[13px] font-medium transition",
                    active
                      ? "bg-forest text-white shadow-sm"
                      : isPending
                        ? "bg-white/15 text-white ring-1 ring-white/20"
                        : "text-white/65 hover:bg-white/10 hover:text-white",
                  )}
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    {Icon ? (
                      <Icon
                        className={cn(
                          "h-4 w-4 shrink-0 transition",
                          active
                            ? "text-white"
                            : isPending
                              ? "text-white animate-pulse"
                              : "text-white/45",
                        )}
                      />
                    ) : null}
                    <span className="truncate">{item.label}</span>
                  </div>

                  {/* Subtle, elegant inline spinner shown right on the clicked item */}
                  {isPending && (
                    <div className="ml-2 flex shrink-0 items-center">
                      <svg
                        className="h-3.5 w-3.5 animate-spin text-white/80"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        />
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                        />
                      </svg>
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );

  const brand = (
    <div className="border-b border-white/10 px-4 py-3">
      <div className="rounded-xl bg-white px-2.5 py-1.5">
        <SkyreonLogo className="h-6" />
      </div>
      <p className="mt-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-copper">{title}</p>
    </div>
  );

  const account = (
    <div className="border-t border-white/10 px-4 py-3">
      <p className="truncate text-sm font-medium text-white">{user?.name || user?.email}</p>
      <p className="mt-0.5 text-xs capitalize text-white/45">{user?.role?.replace("_", " ")}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-paper text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 flex-col bg-[#06101c] text-white lg:flex">
        {brand}
        <div className="flex-1 overflow-y-auto px-3 py-4">{links}</div>
        {account}
      </aside>
      {open && (
        <div className="fixed inset-0 z-40 bg-ink/70 lg:hidden" onClick={() => setOpen(false)}>
          <aside className="flex h-full w-64 flex-col bg-[#06101c] text-white" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-white/10 px-4 py-4">
              <SkyreonLogo className="h-6 rounded-lg bg-white px-2 py-1" />
              <button onClick={() => setOpen(false)} className="rounded-full bg-white/10 p-2" aria-label="Close menu">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-4">{links}</div>
            {account}
          </aside>
        </div>
      )}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-ink/5 bg-paper/90 px-4 py-3 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button className="rounded-full bg-white p-2 shadow-card lg:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
              <Menu className="h-4 w-4" />
            </button>
            <div className="min-w-0">
              <p className="text-xs uppercase tracking-[0.25em] text-copper">{title}</p>
              <h2 className="truncate font-display text-xl sm:text-2xl">{current?.label}</h2>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            {user?.employee_id && <MiniTimer />}
            {isStaff(user?.role) && user?.employee_id ? (
              <button
                type="button"
                disabled={switching}
                onClick={() =>
                  void switchPortal(pathname.startsWith("/admin") ? "/employee/dashboard" : "/admin/dashboard")
                }
                className="hidden items-center gap-2 rounded-full bg-white px-3 py-2 text-xs font-semibold shadow-card disabled:opacity-60 sm:inline-flex"
              >
                <ArrowLeftRight className="h-3.5 w-3.5" />
                {pathname.startsWith("/admin") ? "My workspace" : "Administration"}
              </button>
            ) : isStaff(user?.role) ? (
              <span
                className="hidden max-w-[11rem] text-right text-[11px] leading-snug text-ink/50 sm:block"
                title="Link this login to an employee record (same email on People) to use My workspace."
              >
                My workspace needs a linked employee profile
              </span>
            ) : null}
            <Link href={notificationsHref} className="rounded-full bg-white p-2 shadow-card">
              <Bell className="h-4 w-4" />
            </Link>
            <ChangePasswordModal />
            
            {/* Replaced Icon with "Logout" Text Button */}
            <Button
              variant="outline"
              onClick={() => setLogoutModalOpen(true)}
              className="px-3 py-1.5 text-xs text-ink/75 hover:text-red-700 hover:border-red-200"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span>Logout</span>
            </Button>
          </div>
        </header>
        <main className="p-4 sm:p-6">{children}</main>
      </div>

      {/* Confirmation Modal Before Logging Out */}
      <Modal
        open={logoutModalOpen}
        title="Confirm Logout"
        onClose={() => !isLoggingOut && setLogoutModalOpen(false)}
      >
        <div className="space-y-4">
          <p className="text-sm text-ink/70 leading-relaxed">
            Are you sure you want to log out of your Skyreon Workforce account?
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              type="button"
              disabled={isLoggingOut}
              onClick={() => setLogoutModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              type="button"
              disabled={isLoggingOut}
              onClick={() => void handleConfirmLogout()}
            >
              {isLoggingOut ? (
                <>
                  <svg
                    className="h-4 w-4 animate-spin text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  <span>Logging out...</span>
                </>
              ) : (
                "Log out"
              )}
            </Button>
          </div>
        </div>
      </Modal>

      {user?.must_change_password && <ChangePasswordModal forced />}
    </div>
  );
}
