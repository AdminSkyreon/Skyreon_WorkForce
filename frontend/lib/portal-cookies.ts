import type { User } from "./types";

const WEEK = 7 * 24 * 60 * 60;

export function hasSessionCookie(): boolean {
  if (typeof document === "undefined") return false
  return /(?:^|;\s*)swp_role=/.test(document.cookie);
}

export function syncPortalCookies(user: User) {
  if (typeof document === "undefined") return;
  document.cookie = `swp_role=${encodeURIComponent(user.role)}; path=/; max-age=${WEEK}; samesite=lax`;
  document.cookie = `swp_workspace=${user.employee_id ? "1" : "0"}; path=/; max-age=${WEEK}; samesite=lax`;
  document.cookie = `swp_must_change=${user.must_change_password ? "1" : "0"}; path=/; max-age=${WEEK}; samesite=lax`;
}

export function clearPortalCookies() {
  if (typeof document === "undefined") return;
  for (const name of ["swp_role", "swp_workspace", "swp_must_change"]) {
    document.cookie = `${name}=; path=/; max-age=0; samesite=lax`;
  }
}


