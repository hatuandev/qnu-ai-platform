/**
 * Dev-server-only bridge for local auto-login.
 *
 * The browser never sees the dev access key: this module runs inside the Vite
 * dev server (Node), reads the key from an uncommitted local env file and calls
 * the existing `POST /platform/v1alpha1/auth/login` endpoint on the local
 * backend. The response only carries the short-lived token.
 *
 * Safety rules enforced here, before any network call:
 * - the bridge must be explicitly enabled (`QNU_DEV_AUTO_LOGIN=true`);
 * - it only exists in the dev server (never in build, preview or production);
 * - the request must be same-origin, POST, and addressed to a loopback host;
 * - the backend target must be loopback, so the key is never sent off-machine.
 */

import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";
import { API_V1_PREFIX } from "../src/app/api/v1/endpoints";

/** Namespaced path; the SPA router never uses this prefix. */
export const DEV_AUTO_LOGIN_PATH = "/__qnu_dev/auto-login";

export const DEV_AUTO_LOGIN_ENV_FLAG = "QNU_DEV_AUTO_LOGIN";
export const DEV_AUTO_LOGIN_ENV_KEY = "QNU_DEV_ACCESS_KEY";

const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "::1"]);

export type DevAutoLoginConfig = {
  enabled: boolean;
  accessKey: string | null;
  apiTarget: string;
  /** Human-readable startup note; never contains the key. */
  note: string;
};

export type DevAutoLoginFetch = (
  input: string,
  init?: RequestInit,
) => Promise<Response>;

export type DevAutoLoginDeps = {
  fetchImpl?: DevAutoLoginFetch;
};

type BridgeErrorCode =
  | "dev_bridge_disabled"
  | "dev_bridge_forbidden"
  | "dev_bridge_misconfigured"
  | "dev_bridge_method_not_allowed"
  | "invalid_credentials"
  | "dev_gate_disabled"
  | "backend_not_ready"
  | "backend_error"
  | "backend_unreachable"
  | "invalid_login_response";

/** Splits `host[:port]`, including bracketed IPv6 literals. */
export function parseHostHeader(
  host: string | undefined | null,
): { hostname: string; port: string | null } | null {
  if (!host) return null;
  const value = host.trim().toLowerCase();
  if (!value) return null;
  if (value.startsWith("[")) {
    const end = value.indexOf("]");
    if (end < 0) return null;
    const hostname = value.slice(1, end);
    const rest = value.slice(end + 1);
    const port = rest.startsWith(":") ? rest.slice(1) : null;
    return { hostname, port };
  }
  const lastColon = value.lastIndexOf(":");
  if (lastColon === -1) return { hostname: value, port: null };
  return {
    hostname: value.slice(0, lastColon),
    port: value.slice(lastColon + 1),
  };
}

export function isLoopbackHost(host: string | undefined | null): boolean {
  const parsed = parseHostHeader(host);
  return parsed !== null && LOOPBACK_HOSTNAMES.has(parsed.hostname);
}

/** True only for an absolute http(s) URL whose host is loopback. */
export function isLoopbackUrl(target: string): boolean {
  try {
    const url = new URL(target);
    if (url.protocol !== "http:" && url.protocol !== "https:") return false;
    const hostname = url.hostname.replace(/^\[|\]$/g, "").toLowerCase();
    return LOOPBACK_HOSTNAMES.has(hostname);
  } catch {
    return false;
  }
}

/**
 * Same-origin check for the bridge call.
 *
 * Browsers always send `Origin` on a same-origin POST, so a missing header is
 * rejected instead of treated as trusted.
 */
export function isSameOriginRequest(
  origin: string | undefined,
  host: string | undefined,
): boolean {
  if (!origin || !host) return false;
  let parsed: URL;
  try {
    parsed = new URL(origin);
  } catch {
    return false;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
  return parsed.host.toLowerCase() === host.trim().toLowerCase();
}

export function resolveDevAutoLoginConfig(
  env: Record<string, string | undefined>,
  options: { devServer: boolean },
): DevAutoLoginConfig {
  const requested =
    env[DEV_AUTO_LOGIN_ENV_FLAG]?.trim().toLowerCase() === "true";
  const accessKey = env[DEV_AUTO_LOGIN_ENV_KEY]?.trim() || null;
  const apiTarget = env.QNU_API_PROXY_TARGET?.trim() || "http://127.0.0.1:8002";

  if (!requested) {
    return {
      enabled: false,
      accessKey,
      apiTarget,
      note: `${DEV_AUTO_LOGIN_ENV_FLAG} is not "true"; auto-login stays off.`,
    };
  }
  if (!options.devServer) {
    return {
      enabled: false,
      accessKey,
      apiTarget,
      note: "Auto-login only runs in the Vite dev server, never in build or preview.",
    };
  }
  if (!accessKey) {
    return {
      enabled: true,
      accessKey: null,
      apiTarget,
      note: `${DEV_AUTO_LOGIN_ENV_FLAG}=true but ${DEV_AUTO_LOGIN_ENV_KEY} is empty.`,
    };
  }
  return {
    enabled: true,
    accessKey,
    apiTarget,
    note: `Auto-login bridge enabled for loopback clients (target ${apiTarget}).`,
  };
}

function sendJson(
  res: ServerResponse,
  status: number,
  payload: Record<string, unknown>,
): void {
  const body = JSON.stringify(payload);
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Pragma", "no-cache");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Vary", "Origin");
  res.end(body);
}

function sendError(
  res: ServerResponse,
  status: number,
  code: BridgeErrorCode,
  message: string,
): void {
  sendJson(res, status, { code, message });
}

function readUpstreamToken(payload: unknown): {
  access_token: string;
  token_type: string;
  expires_in: number;
} | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Record<string, unknown>;
  const token = candidate.access_token;
  if (typeof token !== "string" || token.trim().length === 0) return null;
  return {
    access_token: token,
    token_type:
      typeof candidate.token_type === "string"
        ? candidate.token_type
        : "bearer",
    expires_in:
      typeof candidate.expires_in === "number" ? candidate.expires_in : 0,
  };
}

/**
 * Builds the connect middleware. Requests that do not target the bridge path
 * are passed through untouched, so the dev server behaves exactly as before.
 */
export function createDevAutoLoginHandler(
  config: DevAutoLoginConfig,
  deps: DevAutoLoginDeps = {},
) {
  const fetchImpl = deps.fetchImpl ?? globalThis.fetch;

  return function devAutoLoginMiddleware(
    req: IncomingMessage,
    res: ServerResponse,
    next: (error?: unknown) => void,
  ): void {
    const requestUrl = req.url ?? "";
    const pathname = requestUrl.split("?")[0];
    if (pathname !== DEV_AUTO_LOGIN_PATH) {
      next();
      return;
    }

    if (!config.enabled) {
      sendError(
        res,
        404,
        "dev_bridge_disabled",
        "Tự đăng nhập local đang tắt. Đặt QNU_DEV_AUTO_LOGIN=true trong frontendV1/.env.local.",
      );
      return;
    }

    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      sendError(
        res,
        405,
        "dev_bridge_method_not_allowed",
        "Cầu nối đăng nhập chỉ nhận POST.",
      );
      return;
    }

    if (!isLoopbackHost(req.headers.host)) {
      sendError(
        res,
        403,
        "dev_bridge_forbidden",
        "Cầu nối đăng nhập chỉ phục vụ host loopback.",
      );
      return;
    }

    if (!isSameOriginRequest(req.headers.origin, req.headers.host)) {
      sendError(
        res,
        403,
        "dev_bridge_forbidden",
        "Yêu cầu phải cùng origin với dev server.",
      );
      return;
    }

    const fetchSite = req.headers["sec-fetch-site"];
    if (typeof fetchSite === "string" && fetchSite !== "same-origin") {
      sendError(
        res,
        403,
        "dev_bridge_forbidden",
        "Yêu cầu phải xuất phát từ chính dev server.",
      );
      return;
    }

    if (!config.accessKey) {
      sendError(
        res,
        500,
        "dev_bridge_misconfigured",
        `Thiếu ${DEV_AUTO_LOGIN_ENV_KEY} trong frontendV1/.env.local.`,
      );
      return;
    }

    if (!isLoopbackUrl(config.apiTarget)) {
      sendError(
        res,
        500,
        "dev_bridge_misconfigured",
        "QNU_API_PROXY_TARGET phải trỏ tới backend loopback thì mới bật tự đăng nhập.",
      );
      return;
    }

    void (async () => {
      let upstream: Response;
      try {
        upstream = await fetchImpl(
          `${config.apiTarget.replace(/\/$/, "")}${API_V1_PREFIX}/auth/login`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
            },
            body: JSON.stringify({ access_key: config.accessKey }),
            redirect: "error",
          },
        );
      } catch {
        sendError(
          res,
          502,
          "backend_unreachable",
          "Không kết nối được backendV1. Kiểm tra dịch vụ đang chạy ở cổng 8002.",
        );
        return;
      }

      let payload: unknown;
      try {
        payload = await upstream.json();
      } catch {
        payload = null;
      }

      if (!upstream.ok) {
        const upstreamCode =
          payload && typeof payload === "object"
            ? (payload as Record<string, unknown>).code
            : undefined;

        if (upstream.status === 401) {
          sendError(
            res,
            401,
            "invalid_credentials",
            "Dev access key không đúng. Kiểm tra DEV_ACCESS_PASSWORD ở backendV1 và QNU_DEV_ACCESS_KEY ở frontendV1/.env.local.",
          );
          return;
        }
        if (upstream.status === 403 || upstreamCode === "dev_gate_disabled") {
          sendError(
            res,
            403,
            "dev_gate_disabled",
            "BackendV1 đang tắt dev access gate (DEV_AUTH_ENABLED=false). Bật lại hoặc đăng nhập qua SSO.",
          );
          return;
        }
        if (upstream.status === 503) {
          sendError(
            res,
            503,
            "backend_not_ready",
            "BackendV1 chưa sẵn sàng ký token. Kiểm tra SECRET_KEY tối thiểu 32 byte.",
          );
          return;
        }
        sendError(
          res,
          502,
          "backend_error",
          `BackendV1 từ chối đăng nhập (HTTP ${String(upstream.status)}).`,
        );
        return;
      }

      const token = readUpstreamToken(payload);
      if (!token) {
        sendError(
          res,
          502,
          "invalid_login_response",
          "Phản hồi đăng nhập từ backendV1 không có access_token.",
        );
        return;
      }

      // Only the token leaves the dev server; the access key stays here.
      sendJson(res, 200, token);
    })();
  };
}

export function devAutoLoginPlugin(
  config: DevAutoLoginConfig,
  deps: DevAutoLoginDeps = {},
): Plugin {
  return {
    name: "qnu-dev-auto-login",
    // Never applied to `vite build`; preview has no configurePreviewServer hook.
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(createDevAutoLoginHandler(config, deps));
      if (config.enabled) {
        server.config.logger.info(`[qnu] ${config.note}`);
      } else if (config.note.includes(DEV_AUTO_LOGIN_ENV_FLAG)) {
        server.config.logger.info(`[qnu] ${config.note}`);
      }
    },
  };
}
