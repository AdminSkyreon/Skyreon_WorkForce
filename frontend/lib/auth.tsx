"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, refreshAccess, setAccessToken } from "./api";
import { clearPortalCookies, hasSessionCookie, syncPortalCookies } from "./portal-cookies";
import type { User } from "./types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let active = true;

    if (!hasSessionCookie()) {
      setLoading(false);
      return;
    }

    const failSafe = window.setTimeout(() => {
      if (active) setLoading(false);
    }, 45_000);

    void refreshAccess()
      .then(async (refreshed) => {
        if (!active) return;
        if (!refreshed) {
          setAccessToken(null);
          setUser(null);
          clearPortalCookies();
          await api("/auth/logout", { method: "POST" }).catch(() => undefined);
          const path = window.location.pathname;
          if (path.startsWith("/admin") || path.startsWith("/employee")) {
            window.location.replace("/login");
          }
          return;
        }
        setUser(refreshed);
      })
      .catch(() => {
        if (active) setUser(null);
      })
      .finally(() => {
        if (active) setLoading(false);
        window.clearTimeout(failSafe);
      });

    return () => {
      active = false;
      window.clearTimeout(failSafe);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (email, password) => {
        const body = await api<{ access_token: string; user: User }>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password }),
          skipAuth: true,
        });
        setAccessToken(body.access_token);
        setUser(body.user);
        syncPortalCookies(body.user);
        return body.user;
      },
      logout: async () => {
        await api("/auth/logout", { method: "POST" });
        setAccessToken(null);
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
    [user, loading, router],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}