// Thin API client for the Django REST backend.
//
// The JWT is NOT stored here. It lives in HttpOnly cookies the browser attaches
// on its own, so no script — including one injected through an XSS — can read
// or exfiltrate it. What this module reads is only a flag saying a session
// exists (`ym_auth`, set by the backend, no secret in it) plus the CSRF token,
// which is meant to be readable.
const BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8020/api";

// Set by the backend on login; readable on purpose. It answers "is somebody
// signed in?" for UI decisions that have to be synchronous — it is not a
// credential and the server never trusts it.
const FLAG_COOKIE = "ym_auth";
const CSRF_COOKIE = "csrftoken";

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${name.replace(/([.$?*|{}()[\]\\/+^])/g, "\\$1")}=([^;]*)`)
  );
  return match ? decodeURIComponent(match[1]) : null;
}

/** True when a session cookie is present. Says nothing about its validity —
 *  only the server can judge that; this just avoids pointless requests and
 *  keeps the guest-cart badge honest. */
export function hasSession(): boolean {
  return readCookie(FLAG_COOKIE) === "1";
}

/** Forget a session locally when the server has already told us it is gone.
 *  Clears only the readable flag; the HttpOnly cookies are the server's to
 *  remove, which is what /accounts/logout/ is for. */
export function clearSessionFlag() {
  if (typeof document !== "undefined") {
    document.cookie = `${FLAG_COOKIE}=; Max-Age=0; path=/`;
  }
}

type Opts = { auth?: boolean; raw?: boolean; _retried?: boolean };

/** Error thrown by the API client; `status` is the HTTP status when known. */
export type ApiError = Error & { status?: number };

const DEFAULT_ERROR = "خطایی رخ داد. لطفاً دوباره تلاش کنید.";

/** A message that can be shown to the user for any thrown value. */
export function errorMessage(error: unknown, fallback: string = DEFAULT_ERROR): string {
  return error instanceof Error && error.message ? error.message : fallback;
}

/** HTTP status of an API error, if the error came from a response. */
export function errorStatus(error: unknown): number | undefined {
  return error instanceof Error ? (error as ApiError).status : undefined;
}

const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function request<T = any>(
  method: string,
  path: string,
  body?: any,
  opts: Opts = {}
): Promise<T> {
  const headers: Record<string, string> = {};
  const isForm = body instanceof FormData;
  if (body && !isForm) headers["Content-Type"] = "application/json";

  // Cookies ride along automatically, which is exactly why a write needs a
  // second factor that an attacker's page cannot supply.
  if (UNSAFE.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? (isForm ? body : JSON.stringify(body)) : undefined,
    // Same origin in production (the site and /api share a domain), but be
    // explicit so the cookies travel under any deployment shape.
    credentials: "include",
  });

  if (!res.ok) {
    // An expired access cookie is the normal case after 30 minutes, not an
    // error the user should ever see: swap it for a fresh one and retry once.
    // The refresh token never passes through JavaScript — the browser sends
    // the cookie and the server sets the new one.
    if (res.status === 401 && !opts._retried && opts.auth !== false && hasSession()) {
      if (await refreshSession()) {
        return request<T>(method, path, body, { ...opts, _retried: true });
      }
    }

    let detail = DEFAULT_ERROR;
    try {
      const data = await res.json();
      if (typeof data === "string") detail = data;
      else if (data.detail) detail = data.detail;
      else {
        // DRF field errors: {"field": ["msg", ...]} -> first readable message.
        const first = Object.values(data)[0];
        if (Array.isArray(first)) detail = String(first[0]);
        else if (first) detail = String(first);
      }
    } catch {}
    // Carry the status so callers can tell "your session ended" (401/403) apart
    // from "the network hiccupped" — auth.tsx must only drop the session for
    // the former, and pages need it to decide between a redirect and a retry.
    const err = new Error(detail) as ApiError;
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// One in-flight refresh shared by every caller: a page that fires several
// requests at once would otherwise rotate the refresh token concurrently, and
// with blacklist-after-rotation on, every rotation but the first is rejected —
// which would log the user out precisely when the page is busiest.
let refreshInFlight: Promise<boolean> | null = null;

export function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    const csrf = readCookie(CSRF_COOKIE);
    refreshInFlight = fetch(`${BASE}/accounts/token/refresh/`, {
      method: "POST",
      credentials: "include",
      headers: csrf ? { "X-CSRFToken": csrf } : {},
    })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

export const api = {
  get: <T = any>(p: string, opts?: Opts) => request<T>("GET", p, undefined, opts),
  post: <T = any>(p: string, b?: any, opts?: Opts) => request<T>("POST", p, b, opts),
  patch: <T = any>(p: string, b?: any, opts?: Opts) => request<T>("PATCH", p, b, opts),
  del: <T = any>(p: string, b?: any, opts?: Opts) => request<T>("DELETE", p, b, opts),
  base: BASE,
};
