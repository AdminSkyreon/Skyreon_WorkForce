import { syncPortalCookies } from "./portal-cookies";
import type { User } from "./types";
import { toast } from "@/components/toast";

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

type ApiOptions = RequestInit & { skipAuth?: boolean; _retryCount?: number };

function humanizeErrorMessage(status: number, detail: string): string {
  if (status === 401) {
    if (detail.toLowerCase().includes("invalid email or password")) {
      return "Incorrect email or password. Please check your credentials and try again.";
    }
    return "Your session has expired. Please sign in again.";
  }
  if (status === 403) {
    return "You do not have permission to perform this action.";
  }
  if (status === 404) {
    return "The requested information could not be found.";
  }
  if (status === 429) {
    return "The server is receiving too many requests. Please wait a moment and try again.";
  }
  if (status >= 500) {
    return "Our servers encountered a temporary issue. Please try again in a few moments.";
  }
  if (detail && typeof detail === "string" && !detail.startsWith("{")) {
    return detail;
  }
  return "An unexpected error occurred. Please try again.";
}

async function parseError(res: Response): Promise<ApiError> {
  let detail = "";
  try {
    const body = await res.json();
    if (Array.isArray(body.detail)) {
      detail = body.detail.map((err: { msg?: string; loc?: string[] }) => err.msg || "Invalid field").join(", ");
    } else if (typeof body.detail === "string") {
      detail = body.detail;
    } else {
      detail = JSON.stringify(body.detail);
    }
  } catch {
    detail = res.statusText;
  }

  const humanMessage = humanizeErrorMessage(res.status, detail);
  return new ApiError(res.status, humanMessage);
}

// -------------------------------------------------------------
// 1. Preemptive JWT Expiration Check (Zero external libraries)
// -------------------------------------------------------------
function isTokenExpired(token: string | null): boolean {
  if (!token) return true;
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return true;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(window.atob(base64));
    // Buffer by 30 seconds so we never send a token that expires mid-flight
    return Date.now() >= (payload.exp * 1000) - 30_000;
  } catch {
    return true;
  }
}

// -------------------------------------------------------------
// 2. Concurrency Limiter: Caps in-flight requests to max 3
// -------------------------------------------------------------
const MAX_CONCURRENT_REQUESTS = 3;
let activeRequests = 0;
const pendingQueue: (() => void)[] = [];

function acquireSlot(): Promise<void> {
  if (activeRequests < MAX_CONCURRENT_REQUESTS) {
    activeRequests++;
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    pendingQueue.push(resolve);
  });
}

function releaseSlot(): void {
  activeRequests--;
  const next = pendingQueue.shift();
  if (next) {
    activeRequests++;
    next();
  }
}

const AUTH_TIMEOUT_MS = 45_000;
let refreshPromise: Promise<User | null> | null = null;

export async function refreshAccess(): Promise<User | null> {
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);

    let res: Response;
    try {
      res = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
        signal: controller.signal,
      });
    } catch (_err) {
      accessToken = null;
      return null;
    } finally {
      window.clearTimeout(timeout);
    }

    if (!res.ok) {
      accessToken = null;
      return null;
    }

    try {
      const body = (await res.json()) as { access_token: string; user: User };
      accessToken = body.access_token;
      syncPortalCookies(body.user);
      return body.user;
    } catch {
      accessToken = null;
      return null;
    }
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  // Preemptive check: If auth is required, verify token validity BEFORE dispatching
  if (!options.skipAuth) {
    if (isTokenExpired(accessToken)) {
      await refreshAccess();
    } else if (refreshPromise) {
      await refreshPromise;
    }
  }

  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken && !options.skipAuth) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let res: Response;

  // Acquire concurrency slot to throttle parallel bursts
  await acquireSlot();
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch (_err) {
    const errorMsg = "Unable to connect to the server. Please check your internet connection.";
    toast.error("Connection Error", errorMsg);
    throw new ApiError(0, errorMsg);
  } finally {
    releaseSlot();
  }

  // Graceful 429 backoff using Retry-After header (or minimum 6 seconds)
  if (res.status === 429 && (options._retryCount ?? 0) < 1) {
    const retryAfter = Number(res.headers.get("Retry-After")) || 6;
    await new Promise((r) => setTimeout(r, retryAfter * 1000));
    return api<T>(path, { ...options, _retryCount: (options._retryCount ?? 0) + 1 });
  }

  // Fallback 401 handling
  if (res.status === 401 && !path.startsWith("/auth/")) {
    const user = await refreshAccess();
    if (user) return api<T>(path, options);
  }

  if (!res.ok) {
    const parsed = await parseError(res);
    if (!path.includes("/auth/refresh")) {
      toast.error("Action Failed", parsed.detail);
    }
    throw parsed;
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function downloadPdf(path: string, filename: string) {
  if (isTokenExpired(accessToken)) {
    await refreshAccess();
  }
  const headers = new Headers();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  
  await acquireSlot();
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, { headers, credentials: "include" });
  } finally {
    releaseSlot();
  }

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