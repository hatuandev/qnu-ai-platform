/**
 * Dev-server-only bridge for local auto-login and workspace configuration.
 *
 * Runs inside the Vite dev server (Node).
 * Reads the dev access key from local environment and calls backend `/auth/login`.
 * Safety rules:
 * - Bridge only enabled when `QNU_DEV_AUTO_LOGIN=true`.
 * - Only runs in Vite dev server (never in build or preview).
 * - Only responds to same-origin POST requests on loopback host.
 * - Key stays on server, only token and safe workspace code are returned.
 */

import type { IncomingMessage, ServerResponse } from "node:http";
import type { Plugin } from "vite";

export const DEV_AUTO_LOGIN_PATH = "/__qnu_dev/auto-login";
export const DEV_CONFIG_PATH = "/__qnu_dev/config";

export const DEV_AUTO_LOGIN_ENV_FLAG = "QNU_DEV_AUTO_LOGIN";
export const DEV_AUTO_LOGIN_ENV_KEY = "QNU_DEV_ACCESS_KEY";
export const DEV_WORKSPACE_CODE_KEY = "QNU_DEV_WORKSPACE_CODE";

const LOOPBACK_HOSTNAMES = new Set(["localhost", "127.0.0.1", "::1"]);

export type DevAutoLoginConfig = {
  enabled: boolean;
  accessKey: string | null;
  workspaceCode: string | null;
  apiTarget: string;
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
  const accessKey =
    env[DEV_AUTO_LOGIN_ENV_KEY]?.trim() ||
    env.DEV_ACCESS_PASSWORD?.trim() ||
    null;
  const workspaceCode =
    env[DEV_WORKSPACE_CODE_KEY]?.trim() ||
    env.VITE_DEV_WORKSPACE_CODE?.trim() ||
    "shl";
  const apiTarget = env.QNU_API_PROXY_TARGET?.trim() || "http://127.0.0.1:8002";

  if (!requested) {
    return {
      enabled: false,
      accessKey,
      workspaceCode,
      apiTarget,
      note: `${DEV_AUTO_LOGIN_ENV_FLAG} is not "true"; dev auto-login stays off.`,
    };
  }

  if (!options.devServer) {
    return {
      enabled: false,
      accessKey,
      workspaceCode,
      apiTarget,
      note: "Auto-login only runs in the Vite dev server, never in build or preview.",
    };
  }

  if (!accessKey) {
    return {
      enabled: true,
      accessKey: null,
      workspaceCode,
      apiTarget,
      note: `${DEV_AUTO_LOGIN_ENV_FLAG}=true but ${DEV_AUTO_LOGIN_ENV_KEY} is missing.`,
    };
  }

  return {
    enabled: true,
    accessKey,
    workspaceCode,
    apiTarget,
    note: `Dev auto-login bridge active (target: ${apiTarget}, workspace: ${workspaceCode}).`,
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

    // GET /__qnu_dev/config
    if (pathname === DEV_CONFIG_PATH && req.method === "GET") {
      if (!isLoopbackHost(req.headers.host)) {
        sendError(
          res,
          403,
          "dev_bridge_forbidden",
          "Chỉ phục vụ host loopback.",
        );
        return;
      }
      sendJson(res, 200, {
        enabled: config.enabled,
        workspace_code: config.workspaceCode,
        api_target: config.apiTarget,
      });
      return;
    }

    if (pathname !== DEV_AUTO_LOGIN_PATH) {
      next();
      return;
    }

    if (!config.enabled) {
      sendError(
        res,
        404,
        "dev_bridge_disabled",
        "Tự đăng nhập local đang tắt. Đặt QNU_DEV_AUTO_LOGIN=true trong frontendV2/.env.local.",
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

    if (!config.accessKey) {
      sendError(
        res,
        500,
        "dev_bridge_misconfigured",
        `Thiếu ${DEV_AUTO_LOGIN_ENV_KEY} trong frontendV2/.env.local.`,
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
          `${config.apiTarget.replace(/\/$/, "")}/platform/v1alpha1/auth/login`,
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
          "Không kết nối được backendV1 tại cổng 8002.",
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
        if (upstream.status === 401) {
          sendError(
            res,
            401,
            "invalid_credentials",
            "Dev access key không đúng. Kiểm tra DEV_ACCESS_PASSWORD ở backendV1 và QNU_DEV_ACCESS_KEY ở frontendV2/.env.local.",
          );
          return;
        }
        if (upstream.status === 403) {
          sendError(
            res,
            403,
            "dev_gate_disabled",
            "BackendV1 đang tắt dev gate (DEV_AUTH_ENABLED=false).",
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

      const candidate = payload as Record<string, unknown> | null;
      const token = candidate?.access_token;
      if (typeof token !== "string" || !token.trim()) {
        sendError(
          res,
          502,
          "invalid_login_response",
          "Phản hồi đăng nhập thiếu access_token.",
        );
        return;
      }

      sendJson(res, 200, {
        access_token: token,
        token_type: candidate?.token_type || "bearer",
        expires_in: candidate?.expires_in || 28800,
        default_workspace_code: config.workspaceCode,
      });
    })();
  };
}

export function devAutoLoginPlugin(
  config: DevAutoLoginConfig,
  deps: DevAutoLoginDeps = {},
): Plugin {
  return {
    name: "qnu-dev-auto-login",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use(createDevAutoLoginHandler(config, deps));
      if (config.enabled) {
        server.config.logger.info(`[qnu] ${config.note}`);
      }
    },
  };
}
