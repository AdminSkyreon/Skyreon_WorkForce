import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function isStaff(role?: string) {
  return role === "admin" || role === "super_admin";
}

export function middleware(request: NextRequest) {
  const role = request.cookies.get("swp_role")?.value;
  const path = request.nextUrl.pathname;

  if (path.startsWith("/admin")) {
    if (!isStaff(role)) {
      return NextResponse.redirect(new URL(role === "employee" ? "/employee/dashboard" : "/login", request.url));
    }
  }
  if (path.startsWith("/employee")) {
    const hasWorkspace = request.cookies.get("swp_workspace")?.value === "1";
    if (role !== "employee" && !(isStaff(role) && hasWorkspace)) {
      return NextResponse.redirect(new URL(isStaff(role) ? "/admin/dashboard" : "/login", request.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/employee/:path*", "/login"],
};
