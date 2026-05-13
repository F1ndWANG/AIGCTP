import type { User } from "./types";

export const API_BASE = "/api";

const REQUEST_TIMEOUT_MS = 30_000;
const MAX_RETRIES = 2;
const RETRY_BASE_DELAY = 500;

let refreshPromise: Promise<boolean> | null = null;

function formatApiDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return "";
        })
        .filter(Boolean)
        .join("；") || "请求失败"
    );
  }
  if (detail && typeof detail === "object") {
    if ("message" in detail) return String((detail as { message: unknown }).message);
    if ("detail" in detail) return formatApiDetail((detail as { detail: unknown }).detail);
  }
  return "请求失败";
}

export async function checkAuth(): Promise<User | null> {
  try {
    return await fetch(`${API_BASE}/auth/me`, { credentials: "include" }).then((r) =>
      r.ok ? r.json() : null
    );
  } catch {
    return null;
  }
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = doRefreshAccessToken().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

async function doRefreshAccessToken(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
    });
    return resp.ok;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  code?: string;

  constructor(message: string, status: number, detail: unknown, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
  }

  get isRetryable(): boolean {
    return this.status >= 500;
  }

  get isAuthExpired(): boolean {
    return this.code === "ERR_AUTH_EXPIRED" || this.status === 401;
  }
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let lastError: Error | null = null;
  let refreshedAfterAuthError = false;
  const maxAttempts = MAX_RETRIES + 1;

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    try {
      const { signal: _extSignal, ...restOptions } = options;
      const resp = await fetch(`${API_BASE}${path}`, {
        ...restOptions,
        signal: controller.signal,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(options.headers as Record<string, string>),
        },
      });

      if (!resp.ok) {
        let detail: unknown;
        let code: string | undefined;
        try {
          const body = await resp.json();
          detail = body.detail || body.error || resp.statusText;
          code = body.error;
        } catch {
          const text = await resp.text().catch(() => "");
          detail = text ? text.slice(0, 200) : resp.statusText;
        }
        const err = new ApiError(formatApiDetail(detail), resp.status, detail, code);
        if (err.isAuthExpired && !refreshedAfterAuthError) {
          refreshedAfterAuthError = true;
          const refreshed = await refreshAccessToken();
          if (refreshed) continue;
        }
        if (err.isRetryable && attempt < MAX_RETRIES) {
          lastError = err;
          const baseDelay = RETRY_BASE_DELAY * Math.pow(2, attempt);
          await sleep(baseDelay * (0.5 + Math.random() * 0.5));
          continue;
        }
        throw err;
      }

      if (resp.status === 204 || resp.headers.get("content-length") === "0") {
        return undefined as T;
      }

      const text = await resp.text();
      if (!text) return undefined as T;
      return JSON.parse(text) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      if (err instanceof Error && err.name === "AbortError") {
        throw new ApiError("请求超时", 504, "Request timed out");
      }
      if (attempt < MAX_RETRIES) {
        lastError = err instanceof Error ? err : new Error(String(err));
        const baseDelay = RETRY_BASE_DELAY * Math.pow(2, attempt);
        await sleep(baseDelay * (0.5 + Math.random() * 0.5));
        continue;
      }
      throw lastError || new ApiError("Network error", 0, err);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  throw lastError || new Error("Unexpected error");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
