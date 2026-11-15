/**
 * QNU SSO (OpenIddict) sign-in for the admin SPA: authorization code + PKCE.
 *
 * Tokens are held only in module memory. A reload starts empty and bounces
 * through the SSO session cookie, which re-issues tokens without user input.
 * The PKCE transaction (state + verifier, 10 minute TTL) lives in
 * sessionStorage because the browser performs two full-page redirects; it
 * never contains tokens. Renewal uses the refresh_token grant, so no hidden
 * iframe or third-party cookie tricks are involved.
 */

import { clearSessionBootstrap } from "./session-bootstrap";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "./session-token";

const PENDING_KEY = "qnu.sso.pending";
const PENDING_TTL_MS = 10 * 60 * 1000;
const EXPIRY_SKEW_MS = 60 * 1000;
const RETRY_DELAY_MS = 30 * 1000;
const LOGOUT_METADATA_TIMEOUT_MS = 4 * 1000;
const DEFAULT_SCOPE = "openid profile email roles offline_access ai_api";
const DEFAULT_PROD_AUTHORITY = "https://sso.qnu.edu.vn";
const DEFAULT_CLIENT_ID = "qnu-ai-web";

export class SsoError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "SsoError";
    this.code = code;
  }
}

export type SsoEnvironment = {
  enabled: boolean;
  authority: string;
  clientId: string;
  scope: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
};

export type SsoCallbackResult = { returnTo: string };

type SsoMetadata = {
  authorizationEndpoint: string;
  tokenEndpoint: string;
  endSessionEndpoint: string;
};

type PendingTransaction = {
  state: string;
  verifier: string;
  returnTo: string;
  createdAt: number;
};

type TokenPayload = {
  access_token?: unknown;
  refresh_token?: unknown;
  id_token?: unknown;
  expires_in?: unknown;
  error?: unknown;
  error_description?: unknown;
};

type SsoSession = {
  accessToken: string;
  refreshToken: string | null;
  idToken: string | null;
  expiresAt: number;
};

let session: SsoSession | null = null;
let cachedEnvironment: SsoEnvironment | null = null;
let metadataPromise: Promise<SsoMetadata> | null = null;
let refreshPromise: Promise<boolean> | null = null;
let renewalTimer: number | null = null;
let loggingOut = false;
let callbackPromise: Promise<SsoCallbackResult> | null = null;

function readViteEnv(): Record<string, string | undefined> {
  return (
    (import.meta as unknown as { env?: Record<string, string | undefined> })
      .env ?? {}
  );
}

function isLoopbackHostname(hostname: string): boolean {
  const clean = hostname.replace(/^\[|\]$/g, "").toLowerCase();
  return clean === "localhost" || clean === "127.0.0.1" || clean === "::1";
}

export function sanitizeReturnTo(returnTo: string | undefined | null): string {
  if (!returnTo) return "/";
  const value = returnTo.trim();
  if (!value.startsWith("/") || value.startsWith("//")) return "/";
  if (value.includes("\\")) return "/";
  return value;
}

export function isSsoFlagEnabled(
  env: Record<string, string | undefined>,
  isDev: boolean,
): boolean {
  const flag = env.VITE_SSO_ENABLED?.trim().toLowerCase();
  if (flag === "true") return true;
  if (flag === "false") return false;
  return !isDev;
}

export function resolveSsoEnvironment(
  env: Record<string, string | undefined>,
  options: { origin: string; isDev: boolean },
): SsoEnvironment {
  const enabled = isSsoFlagEnabled(env, options.isDev);
  const redirectUri = `${options.origin}/signin-oidc`;
  // Land directly on the public portal: an intermediate callback page forced a
  // second full page load right after logout and could leave a blank screen.
  const postLogoutRedirectUri = `${options.origin}/`;

  if (!enabled) {
    return {
      enabled,
      authority: "",
      clientId: DEFAULT_CLIENT_ID,
      scope: DEFAULT_SCOPE,
      redirectUri,
      postLogoutRedirectUri,
    };
  }

  const rawAuthority = env.VITE_SSO_AUTHORITY?.trim() ?? "";
  const authority = (
    rawAuthority || (options.isDev ? "" : DEFAULT_PROD_AUTHORITY)
  ).replace(/\/+$/, "");
  if (!authority) {
    throw new SsoError(
      "sso_config",
      "Dev server đang bật SSO nhưng thiếu VITE_SSO_AUTHORITY (ví dụ https://localhost:7067).",
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(authority);
  } catch {
    throw new SsoError(
      "sso_config",
      `VITE_SSO_AUTHORITY không phải URL hợp lệ: ${authority}`,
    );
  }

  const isHttps = parsed.protocol === "https:";
  const isLoopbackHttp =
    parsed.protocol === "http:" && isLoopbackHostname(parsed.hostname);
  if (!isHttps && !isLoopbackHttp) {
    throw new SsoError(
      "sso_config",
      "VITE_SSO_AUTHORITY phải dùng HTTPS; HTTP chỉ được phép với localhost.",
    );
  }

  const scopeTokens = (env.VITE_SSO_SCOPE?.trim() || DEFAULT_SCOPE)
    .split(/\s+/)
    .filter(Boolean);
  const scope = Array.from(new Set(scopeTokens));
  if (!scope.includes("openid")) {
    throw new SsoError("sso_config", "VITE_SSO_SCOPE phải chứa scope openid.");
  }

  return {
    enabled,
    authority: `${parsed.origin}${parsed.pathname.replace(/\/+$/, "")}`,
    clientId: env.VITE_SSO_CLIENT_ID?.trim() || DEFAULT_CLIENT_ID,
    scope: scope.join(" "),
    redirectUri,
    postLogoutRedirectUri,
  };
}

export function getSsoEnvironment(): SsoEnvironment {
  if (!cachedEnvironment) {
    const env = readViteEnv();
    cachedEnvironment = resolveSsoEnvironment(env, {
      origin: window.location.origin,
      isDev: Boolean(env.DEV),
    });
  }
  return cachedEnvironment;
}

/**
 * Cheap gate selector: never throws on a half-configured authority, so the
 * gate can render a proper error card instead of crashing the app shell.
 */
export function isSsoEnabled(): boolean {
  if (cachedEnvironment) return cachedEnvironment.enabled;
  const env = readViteEnv();
  return isSsoFlagEnabled(env, Boolean(env.DEV));
}

export function isSsoLoggingOut(): boolean {
  return loggingOut;
}

function requireEndpoint(value: unknown, name: string): string {
  if (typeof value !== "string" || !value) {
    throw new SsoError(
      "sso_unreachable",
      `Tài liệu cấu hình QNU SSO thiếu trường ${name}.`,
    );
  }
  return value;
}

async function loadMetadata(environment: SsoEnvironment): Promise<SsoMetadata> {
  if (metadataPromise) return metadataPromise;
  metadataPromise = (async () => {
    let response: Response;
    try {
      response = await fetch(
        `${environment.authority}/.well-known/openid-configuration`,
        { headers: { Accept: "application/json" }, credentials: "omit" },
      );
    } catch {
      throw new SsoError(
        "sso_unreachable",
        "Không kết nối được tới QNU SSO. Kiểm tra mạng hoặc VITE_SSO_AUTHORITY.",
      );
    }
    if (!response.ok) {
      throw new SsoError(
        "sso_unreachable",
        `QNU SSO trả về HTTP ${response.status} cho tài liệu cấu hình.`,
      );
    }
    const document = (await response.json().catch(() => null)) as Record<
      string,
      unknown
    > | null;
    return {
      authorizationEndpoint: requireEndpoint(
        document?.authorization_endpoint,
        "authorization_endpoint",
      ),
      tokenEndpoint: requireEndpoint(
        document?.token_endpoint,
        "token_endpoint",
      ),
      endSessionEndpoint: requireEndpoint(
        document?.end_session_endpoint,
        "end_session_endpoint",
      ),
    };
  })().catch((error: unknown) => {
    metadataPromise = null;
    throw error;
  });
  return metadataPromise;
}

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return window
    .btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function randomBase64Url(length: number): string {
  const buffer = new Uint8Array(length);
  window.crypto.getRandomValues(buffer);
  return base64UrlEncode(buffer);
}

async function computeCodeChallenge(verifier: string): Promise<string> {
  const digest = await window.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(verifier),
  );
  return base64UrlEncode(new Uint8Array(digest));
}

function readPending(): PendingTransaction | null {
  try {
    const raw = window.sessionStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PendingTransaction>;
    if (
      typeof parsed.state !== "string" ||
      typeof parsed.verifier !== "string" ||
      typeof parsed.createdAt !== "number"
    ) {
      return null;
    }
    return {
      state: parsed.state,
      verifier: parsed.verifier,
      returnTo: sanitizeReturnTo(parsed.returnTo),
      createdAt: parsed.createdAt,
    };
  } catch {
    return null;
  }
}

function writePending(pending: PendingTransaction): void {
  try {
    window.sessionStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  } catch {
    throw new SsoError(
      "sso_storage",
      "Trình duyệt đang chặn sessionStorage nên không thể bắt đầu đăng nhập.",
    );
  }
}

function clearPending(): void {
  try {
    window.sessionStorage.removeItem(PENDING_KEY);
  } catch {
    // Storage may be unavailable; nothing to clean up then.
  }
}

function scheduleRenewal(environment: SsoEnvironment): void {
  if (renewalTimer) {
    window.clearTimeout(renewalTimer);
    renewalTimer = null;
  }
  const current = session;
  if (!current?.refreshToken) return;
  const delay = Math.max(
    current.expiresAt - Date.now() - EXPIRY_SKEW_MS,
    10_000,
  );
  renewalTimer = window.setTimeout(() => {
    void renewSsoSession(environment);
  }, delay);
}

function applyTokenPayload(
  environment: SsoEnvironment,
  payload: TokenPayload,
  previous?: Pick<SsoSession, "refreshToken" | "idToken"> | null,
): void {
  if (typeof payload.access_token !== "string" || !payload.access_token) {
    throw new SsoError(
      "sso_token_invalid",
      "QNU SSO không trả về access token hợp lệ.",
    );
  }
  const expiresIn =
    typeof payload.expires_in === "number" &&
    Number.isFinite(payload.expires_in) &&
    payload.expires_in > 0
      ? payload.expires_in
      : 900;
  session = {
    accessToken: payload.access_token,
    refreshToken:
      typeof payload.refresh_token === "string" && payload.refresh_token
        ? payload.refresh_token
        : (previous?.refreshToken ?? null),
    idToken:
      typeof payload.id_token === "string" && payload.id_token
        ? payload.id_token
        : (previous?.idToken ?? null),
    expiresAt: Date.now() + expiresIn * 1000,
  };
  setAccessToken(session.accessToken);
  scheduleRenewal(environment);
}

async function postToken(
  metadata: SsoMetadata,
  form: URLSearchParams,
): Promise<TokenPayload> {
  let response: Response;
  try {
    response = await fetch(metadata.tokenEndpoint, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form.toString(),
      credentials: "omit",
    });
  } catch {
    throw new SsoError(
      "sso_unreachable",
      "Không kết nối được tới QNU SSO để đổi phiên đăng nhập.",
    );
  }
  const payload = (await response
    .json()
    .catch(() => null)) as TokenPayload | null;
  if (!response.ok) {
    const errorCode = typeof payload?.error === "string" ? payload.error : "";
    if (!errorCode) {
      throw new SsoError(
        "sso_unreachable",
        `QNU SSO từ chối yêu cầu đăng nhập (HTTP ${response.status}).`,
      );
    }
    throw new SsoError(
      `sso_${errorCode}`,
      `QNU SSO từ chối yêu cầu đăng nhập (${errorCode}).`,
    );
  }
  if (!payload) {
    throw new SsoError(
      "sso_token_invalid",
      "QNU SSO trả về dữ liệu phiên không hợp lệ.",
    );
  }
  return payload;
}

export async function beginSsoLogin(returnTo?: string): Promise<void> {
  const environment = getSsoEnvironment();
  if (!environment.enabled) return;
  const metadata = await loadMetadata(environment);
  const state = randomBase64Url(32);
  const verifier = randomBase64Url(64);
  const challenge = await computeCodeChallenge(verifier);
  writePending({
    state,
    verifier,
    returnTo: sanitizeReturnTo(returnTo),
    createdAt: Date.now(),
  });
  const url = new URL(metadata.authorizationEndpoint);
  url.searchParams.set("client_id", environment.clientId);
  url.searchParams.set("redirect_uri", environment.redirectUri);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("response_mode", "query");
  url.searchParams.set("scope", environment.scope);
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge", challenge);
  url.searchParams.set("code_challenge_method", "S256");
  window.location.assign(url.toString());
}

export function completeSsoLogin(): Promise<SsoCallbackResult> {
  if (!callbackPromise) {
    callbackPromise = runSsoCallback().catch((error: unknown) => {
      callbackPromise = null;
      throw error;
    });
  }
  return callbackPromise;
}

async function runSsoCallback(): Promise<SsoCallbackResult> {
  if (!getSsoEnvironment().enabled) {
    throw new SsoError(
      "sso_disabled",
      "QNU SSO chưa được bật cho bản chạy này.",
    );
  }
  const environment = getSsoEnvironment();
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");
  if (error) {
    clearPending();
    const description = params.get("error_description")?.slice(0, 200);
    if (error === "access_denied") {
      throw new SsoError(
        "sso_access_denied",
        "Bạn đã hủy đăng nhập tại QNU SSO.",
      );
    }
    throw new SsoError(
      `sso_${error}`,
      `QNU SSO trả về lỗi ${error}${description ? `: ${description}` : "."}`,
    );
  }
  const code = params.get("code");
  const state = params.get("state");
  const pending = readPending();
  clearPending();
  if (!code || !state || !pending || pending.state !== state) {
    throw new SsoError(
      "sso_callback_invalid",
      "Phiên đăng nhập trên trình duyệt đã hết hạn hoặc không khớp. Hãy đăng nhập lại.",
    );
  }
  if (Date.now() - pending.createdAt > PENDING_TTL_MS) {
    throw new SsoError(
      "sso_callback_expired",
      "Yêu cầu đăng nhập đã quá cũ. Hãy đăng nhập lại.",
    );
  }
  const metadata = await loadMetadata(environment);
  const form = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: environment.redirectUri,
    client_id: environment.clientId,
    code_verifier: pending.verifier,
  });
  const payload = await postToken(metadata, form);
  applyTokenPayload(environment, payload);
  return { returnTo: pending.returnTo };
}

export function renewSsoSession(
  environment: SsoEnvironment = getSsoEnvironment(),
): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  const previous = session;
  const refreshToken = previous?.refreshToken;
  if (!refreshToken) return Promise.resolve(false);
  refreshPromise = (async () => {
    try {
      const metadata = await loadMetadata(environment);
      const form = new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: refreshToken,
        client_id: environment.clientId,
      });
      const payload = await postToken(metadata, form);
      applyTokenPayload(environment, payload, previous);
      return true;
    } catch (error) {
      const permanent =
        error instanceof SsoError && error.code !== "sso_unreachable";
      if (permanent) {
        clearSsoSession({ expired: true });
        return false;
      }
      // Infrastructure hiccup: keep the current token until it really expires.
      if (session && Date.now() < session.expiresAt - 15_000) {
        if (renewalTimer) window.clearTimeout(renewalTimer);
        renewalTimer = window.setTimeout(() => {
          void renewSsoSession(environment);
        }, RETRY_DELAY_MS);
        return false;
      }
      clearSsoSession({ expired: true });
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

function clearSsoSession(options: { expired: boolean }): void {
  session = null;
  if (renewalTimer) {
    window.clearTimeout(renewalTimer);
    renewalTimer = null;
  }
  clearAccessToken({ expired: options.expired });
}

export async function ensureSsoSession(): Promise<boolean> {
  const environment = getSsoEnvironment();
  if (!environment.enabled) return true;
  const current = session;
  const inMemoryToken = getAccessToken();
  if (current && inMemoryToken !== current.accessToken) {
    // A 401 cleared the API token; the backend no longer trusts it.
    if (current.refreshToken) return renewSsoSession(environment);
    session = null;
    return false;
  }
  if (current && Date.now() < current.expiresAt - 5_000) return true;
  if (current?.refreshToken) return renewSsoSession(environment);
  return false;
}

async function loadLogoutMetadata(
  environment: SsoEnvironment,
): Promise<SsoMetadata> {
  let timeout: number | null = null;
  try {
    return await Promise.race([
      loadMetadata(environment),
      new Promise<never>((_, reject) => {
        timeout = window.setTimeout(() => {
          reject(
            new SsoError("sso_unreachable", "QNU SSO không phản hồi kịp."),
          );
        }, LOGOUT_METADATA_TIMEOUT_MS);
      }),
    ]);
  } finally {
    if (timeout !== null) window.clearTimeout(timeout);
  }
}

export async function logoutSso(): Promise<void> {
  const idToken = session?.idToken ?? null;
  let environment: SsoEnvironment | null = null;
  try {
    environment = getSsoEnvironment();
  } catch {
    // Broken SSO settings must not keep the user signed in locally.
    environment = null;
  }

  loggingOut = true;
  session = null;
  if (renewalTimer) {
    window.clearTimeout(renewalTimer);
    renewalTimer = null;
  }
  clearAccessToken();
  clearSessionBootstrap();

  if (!environment?.enabled) {
    window.location.assign("/");
    return;
  }
  try {
    const metadata = await loadLogoutMetadata(environment);
    const url = new URL(metadata.endSessionEndpoint);
    url.searchParams.set("client_id", environment.clientId);
    url.searchParams.set(
      "post_logout_redirect_uri",
      environment.postLogoutRedirectUri,
    );
    if (idToken) url.searchParams.set("id_token_hint", idToken);
    window.location.assign(url.toString());
  } catch {
    window.location.assign("/");
  }
}
