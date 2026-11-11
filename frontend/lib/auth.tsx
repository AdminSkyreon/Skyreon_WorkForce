"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, getLastRefreshFailureStatus, refreshAccess, setAccessToken } from "./api";
import { clearPortalCookies, hasSessionCookie, syncPortalCookies } from "./portal-cookies";
import { toast } from "@/components/toast";
import type { User } from "./types";

export type SessionError = "rate_limited" | "network" | null;

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  sessionError: SessionError;
  retrySession: () => void;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [sessionError, setSessionError] = useState<SessionError>(null);
  const [retryTick, setRetryTick] = useState(0);
  const router = useRouter();

  const retrySession = useCallback(() => {
    setLoading(true);
    setSessionError(null);
    setRetryTick((t) => t + 1);
  }, []);

  useEffect(() => {
    let active = true;

    const isProtectedRoute =
      typeof window !== "undefined" &&
      (window.location.pathname.startsWith("/admin") || window.location.pathname.startsWith("/employee"));

    // Only skip refresh on public pages (e.g. /login) when no session cookie exists
    if (!isProtectedRoute && !hasSessionCookie()) {
      setLoading(false);
      return;
    }

    const failSafe = window.setTimeout(() => {
      if (active) setLoading(false);
    }, 45_000);

    void refreshAccess()
      .then((refreshed) => {
        if (!active) return;
        if (!refreshed) {
          const failStatus = getLastRefreshFailureStatus();
          // Only clear session & kick to /login when the token is actually rejected (401/403).
          // On 429 (rate limit) or transient network/5xx errors, preserve cookies so the user isn't logged out.
          if (failStatus === 401 || failStatus === 403) {
            setAccessToken(null);
            setUser(null);
            setSessionError(null);
            clearPortalCookies();
            if (isProtectedRoute) {
              window.location.replace("/login");
            }
            return;
          }

          const errKind: SessionError = failStatus === 429 ? "rate_limited" : "network";
          setSessionError(errKind);
          if (failStatus === 429) {
            toast.error(
              "Server Busy",
              "The server is temporarily rate-limited. Wait a few seconds and click Retry — your session is safe.",
            );
          }
          return;
        }
        setSessionError(null);
        setUser(refreshed);
      })
      .catch(() => {
        if (active) setSessionError("network");
      })
      .finally(() => {
        if (active) setLoading(false);
        window.clearTimeout(failSafe);
      });

    return () => {
      active = false;
      window.clearTimeout(failSafe);
    };
  }, [retryTick]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      sessionError,
      retrySession,
      login: async (email, password) => {
        const body = await api<{ access_token: string; user: User }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        });
        setAccessToken(body.access_token);
        setSessionError(null);
        setUser(body.user);
        syncPortalCookies(body.user);
        return body.user;
      },
      logout: async () => {
        await api("/auth/logout", { method: "POST", skipAuth: true, silent: true }).catch(() => undefined);
        setAccessToken(null);
        setSessionError(null);
        setUser(null);
        clearPortalCookies();
        router.push("/login");
      },
      refreshUser: async () => {
        const me = await api<User>("/auth/me");
        setUser(me);
        syncPortalCookies(me);
      },
    }),
    [user, loading, sessionError, retrySession, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
