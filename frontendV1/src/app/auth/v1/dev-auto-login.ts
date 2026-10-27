import { ApiProblemError, createV1Client } from "@/app/api/v1/client";

/**
 * Local auto-login (development only).
 *
 * The dev access key never reaches the browser: `POST /__qnu_dev/auto-login`
 * is served by the Vite dev server (see `dev/dev-auto-login.ts`), which reads
 * the key from an uncommitted local env file and calls the existing
 * `POST /platform/v1alpha1/auth/login` endpoint. This module only receives the
 * token and keeps it in memory, exactly like a manual dev-key login.
 *
 * Everything here is inert in a production bundle: `import.meta.env.DEV` is
 * false, so `isDevAutoLoginAvailable()` returns false and no request is made.
 */

export const DEV_AUTO_LOGIN_PATH = "/__qnu_dev/auto-login";

/**
 * The bridge is served by the Vite dev server, not by backendV1: it needs no
 * `/platform/v1alpha1` prefix and must never receive a bearer token, so this
 * client has no token getter. Routing the call through the shared v1 client
 * keeps every browser request inside one audited module.
 */
const bridgeClient = createV1Client({ prefix: "" });

/** Non-secret marker: remembers an explicit logout inside this tab. */
const SUPPRESSION_STORAGE_KEY = "qnu.dev-auto-login.suppressed";

export type DevAutoLoginErrorCode =
  | "dev_bridge_disabled"
  | "dev_bridge_forbidden"
  | "dev_bridge_misconfigured"
  | "dev_bridge_method_not_allowed"
  | "invalid_credentials"
  | "dev_gate_disabled"
  | "backend_not_ready"
  | "backend_error"
  | "backend_unreachable"
  | "invalid_login_response"
  | "network_unreachable";

export class DevAutoLoginError extends Error {
  readonly code: DevAutoLoginErrorCode;

  constructor(code: DevAutoLoginErrorCode, message: string) {
    super(message);
    this.name = "DevAutoLoginError";
    this.code = code;
  }
}

/** True only inside the Vite dev server build of the app. */
export function isDevAutoLoginAvailable(): boolean {
  if (typeof import.meta === "undefined") return false;
  return Boolean(import.meta.env?.DEV) && !import.meta.env?.PROD;
}

function readSuppression(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(SUPPRESSION_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * After an explicit logout the bridge must not sign the user back in on its
 * own. The flag lives in `sessionStorage` (a boolean, never a credential) so a
 * reload in the same tab does not silently undo the logout.
 */
export function isDevAutoLoginSuppressed(): boolean {
  return readSuppression();
}

export function suppressDevAutoLogin(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(SUPPRESSION_STORAGE_KEY, "1");
  } catch {
    // Private mode or blocked storage: the in-memory guard still applies.
  }
}

export function clearDevAutoLoginSuppression(): void {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.removeItem(SUPPRESSION_STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}

/**
 * The SSO callback page owns the token exchange while it is on screen.
 *
 * The provider mounts above the router, so it cannot read the current route.
 * The callback route therefore announces itself here: auto-login stays off
 * until the callback either completes or leaves the screen, and then resumes
 * on the next render instead of staying disabled for the whole tab.
 */
let ssoCallbackActive = false;
const ssoCallbackListeners = new Set<() => void>();

export function isSsoCallbackActive(): boolean {
  return ssoCallbackActive;
}

export function setSsoCallbackActive(active: boolean): void {
  if (ssoCallbackActive === active) return;
  ssoCallbackActive = active;
  for (const listener of ssoCallbackListeners) listener();
}

export function subscribeSsoCallback(listener: () => void): () => void {
  ssoCallbackListeners.add(listener);
  return () => {
    ssoCallbackListeners.delete(listener);
  };
}

/** Test seam: forgets the callback flag. */
export function resetSsoCallbackState(): void {
  ssoCallbackActive = false;
}

function asErrorCode(value: unknown): DevAutoLoginErrorCode | null {
  switch (value) {
    case "dev_bridge_disabled":
    case "dev_bridge_forbidden":
    case "dev_bridge_misconfigured":
    case "dev_bridge_method_not_allowed":
    case "invalid_credentials":
    case "dev_gate_disabled":
    case "backend_not_ready":
    case "backend_error":
    case "backend_unreachable":
    case "invalid_login_response":
      return value;
    default:
      return null;
  }
}

/**
 * Single in-flight request: React StrictMode runs mount effects twice, and a
 * second concurrent login would either race or double the token issuance.
 */
let inFlight: Promise<string> | null = null;

/**
 * Maps a bridge failure onto the codes this module exposes.
 *
 * `ApiProblemError.code` already carries the bridge's own code, so the mapping
 * is mostly a pass-through; anything unrecognised stays a generic bridge error.
 */
function toDevAutoLoginError(error: unknown): DevAutoLoginError {
  if (error instanceof ApiProblemError) {
    // Client-side codes: a timeout or a refused connection both mean the
    // bridge never answered. They are not server codes, so `asErrorCode`
    // (which only parses what the bridge sends) does not cover them.
    if (
      error.code === "request_aborted" ||
      error.code === "network_unreachable"
    ) {
      return new DevAutoLoginError("network_unreachable", error.message);
    }
    const code = asErrorCode(error.code);
    return new DevAutoLoginError(code ?? "backend_error", error.message);
  }
  return new DevAutoLoginError(
    "network_unreachable",
    "Không gọi được cầu nối đăng nhập của dev server.",
  );
}

async function performDevAutoLogin(): Promise<string> {
  if (!isDevAutoLoginAvailable()) {
    throw new DevAutoLoginError(
      "dev_bridge_disabled",
      "Tự đăng nhập local chỉ hoạt động trong Vite dev server.",
    );
  }

  let payload: unknown;
  try {
    payload = await bridgeClient.request<unknown>(DEV_AUTO_LOGIN_PATH, {
      method: "POST",
    });
  } catch (error) {
    throw toDevAutoLoginError(error);
  }

  const token =
    payload && typeof payload === "object"
      ? (payload as Record<string, unknown>).access_token
      : undefined;
  if (typeof token !== "string" || token.trim().length === 0) {
    throw new DevAutoLoginError(
      "invalid_login_response",
      "Cầu nối đăng nhập không trả access_token.",
    );
  }
  return token;
}

/**
 * Asks the dev bridge for a token. Concurrent callers share one request; the
 * cached promise is dropped on failure so an explicit retry can run again.
 */
export function requestDevAutoLogin(): Promise<string> {
  if (!inFlight) {
    inFlight = performDevAutoLogin().finally(() => {
      inFlight = null;
    });
  }
  return inFlight;
}

/** Test seam: forgets the shared promise. */
export function resetDevAutoLoginState(): void {
  inFlight = null;
}
