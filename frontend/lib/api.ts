import { syncPortalCookies } from "./portal-cookies";
import type { User } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

type ApiOptions = RequestInit & { skipAuth?: boolean };

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    return new ApiError(res.status, detail);
  } catch {
    return new ApiError(res.status, res.statusText);
  }
}

const AUTH_TIMEOUT_MS = 8_000;

async function refreshAccess(): Promise<User | null> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      signal: controller.signal,
    });
  } catch {
    accessToken = null;
    return null;
  } finally {
    window.clearTimeout(timeout);
  }
  if (!res.ok) {
    accessToken = null;
    return null;
  }
  const body = (await res.json()) as { access_token: string; user: User };
  accessToken = body.access_token;
  syncPortalCookies(body.user);
  return body.user;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken && !options.skipAuth) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }
  const res = await fetch(`${API_URL}/api/v1${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (res.status === 401 && !path.startsWith("/auth/")) {
    const user = await refreshAccess();
    if (user) return api<T>(path, options);
  }
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function downloadPdf(path: string, filename: string) {
  if (!accessToken) await refreshAccess();
  const headers = new Headers();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const res = await fetch(`${API_URL}/api/v1${path}`, { headers, credentials: "include" });
  if (res.status === 401) {
    const user = await refreshAccess();
    if (user) return downloadPdf(path, filename);
  }
  if (!res.ok) throw await parseError(res);
  const blob = await res.blob();
  const pdf = new Blob([await blob.arrayBuffer()], { type: "application/pdf" });
  const url = URL.createObjectURL(pdf);
  const opened = window.open(url, "_blank", "noopener,noreferrer");
  if (!opened) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.click();
  }
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export { refreshAccess };
