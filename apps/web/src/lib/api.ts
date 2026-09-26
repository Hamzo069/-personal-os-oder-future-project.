/**
 * Minimal typed API client.
 *
 * - The access token lives in memory only (never localStorage) and is attached
 *   as a Bearer header.
 * - The refresh token is an httpOnly cookie the browser sends automatically to
 *   /api/v1/auth/*; JavaScript never sees it.
 * - On a 401 the client refreshes once and retries the original request. All
 *   concurrent requests share the same in-flight refresh.
 */

import type { ApiErrorBody, TokenResponse } from "@/types";

const BASE_URL = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let accessToken: string | null = null;
let refreshInFlight: Promise<boolean> | null = null;
let onSessionExpired: (() => void) | null = null;

/**
 * The refresh cookie is httpOnly, so the app cannot see whether one exists. A
 * harmless marker in localStorage records that a session was started on this
 * browser, which lets the start-up code skip a pointless refresh call (and the
 * resulting 401 in the console) for first-time visitors. It carries no secret.
 */
const SESSION_MARKER = "ledgerlens:session";

export function markSession(active: boolean): void {
  try {
    if (active) localStorage.setItem(SESSION_MARKER, "1");
    else localStorage.removeItem(SESSION_MARKER);
  } catch {
    // storage unavailable (private mode, blocked) - refresh will simply be attempted
  }
}

export function hasSessionMarker(): boolean {
  try {
    return localStorage.getItem(SESSION_MARKER) === "1";
  } catch {
    return true;
  }
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

async function parseError(response: Response): Promise<ApiError> {
  let body: ApiErrorBody | null = null;
  try {
    body = (await response.json()) as ApiErrorBody;
  } catch {
    // non-JSON error body
  }
  const error = body?.error;
  if (!error && [502, 503, 504].includes(response.status)) {
    // No JSON error envelope: the request never reached the API (dev proxy or nginx
    // could not connect). Say so instead of showing a bare "Bad Gateway".
    return new ApiError(
      response.status,
      "api_unreachable",
      "The server is not reachable. Make sure the backend is running on port 8000.",
    );
  }
  return new ApiError(
    response.status,
    error?.code ?? "http_error",
    error?.message ?? (response.statusText || "Request failed"),
    error?.details,
  );
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const response = await fetch(`${BASE_URL}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        });
        if (!response.ok) {
          accessToken = null;
          markSession(false);
          return false;
        }
        const data = (await response.json()) as TokenResponse;
        accessToken = data.access_token;
        markSession(true);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | undefined | null>;
  auth?: boolean;
  retryOn401?: boolean;
}

function buildQuery(query?: RequestOptions["query"]): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, query, auth = true, retryOn401 = true } = options;
  const headers: Record<string, string> = {};
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(`${BASE_URL}${path}${buildQuery(query)}`, {
    method,
    headers,
    credentials: "include",
    body: formData ?? (body !== undefined ? JSON.stringify(body) : undefined),
  });

  if (response.status === 401 && auth && retryOn401) {
    const refreshed = await refreshSession();
    if (refreshed) return request<T>(path, { ...options, retryOn401: false });
    onSessionExpired?.();
  }
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return (await response.json()) as T;
  return (await response.text()) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions["query"]) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  delete: <T = void>(path: string, body?: unknown) => request<T>(path, { method: "DELETE", body }),
  upload: <T>(path: string, formData: FormData) => request<T>(path, { method: "POST", formData }),
};

export function apiUrl(path: string): string {
  return `${BASE_URL}${path}`;
}
