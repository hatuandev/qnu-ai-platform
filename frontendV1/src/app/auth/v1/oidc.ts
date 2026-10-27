import {
  InMemoryWebStorage,
  type User as OidcUser,
  UserManager,
  type UserManagerSettings,
  WebStorageStateStore,
} from "oidc-client-ts";
import { clearAccessToken, setAccessToken } from "@/app/api/v1/session-token";

let userManagerInstance: UserManager | null = null;

export function isLoopbackHostname(hostname: string): boolean {
  const clean = hostname.replace(/^\[|\]$/g, "").toLowerCase();
  return clean === "localhost" || clean === "127.0.0.1" || clean === "::1";
}

export function resolveOidcAuthority(
  rawAuthority: string | undefined | null,
  fallbackAuthority: string,
  isProduction: boolean = false,
): string {
  const candidate = rawAuthority?.trim() || fallbackAuthority?.trim();
  if (!candidate) {
    throw new Error(
      "SSO authority is required but neither rawAuthority nor fallbackAuthority was provided.",
    );
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch (err) {
    throw new Error(
      `Invalid SSO authority '${candidate}': ${(err as Error).message}`,
    );
  }

  if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
    throw new Error(
      `Invalid SSO authority protocol '${parsed.protocol}', only HTTP and HTTPS are permitted. Received '${candidate}'`,
    );
  }

  const isLoopback = isLoopbackHostname(parsed.hostname);

  if (isProduction) {
    if (parsed.protocol !== "https:") {
      throw new Error(
        `Production security violation: SSO authority must use HTTPS protocol, received '${candidate}'`,
      );
    }
    if (isLoopback) {
      throw new Error(
        `Production security violation: SSO authority must not point to loopback address (${parsed.hostname}), received '${candidate}'`,
      );
    }
  } else {
    if (parsed.protocol === "http:" && !isLoopback) {
      throw new Error(
        `Invalid SSO authority: HTTP is only permitted for loopback hosts (localhost, 127.0.0.1, ::1), received '${candidate}'`,
      );
    }
  }

  const normalizedPath = parsed.pathname.replace(/\/+$/, "");
  return `${parsed.origin}${normalizedPath}${parsed.search || ""}${parsed.hash || ""}`;
}

export function resolveOidcUrl(
  rawUrl: string | undefined,
  defaultPath: string,
  origin: string,
  isProduction: boolean = false,
): string {
  const candidate = rawUrl?.trim() || defaultPath;
  let parsed: URL;
  try {
    parsed = new URL(candidate, origin);
  } catch (err) {
    throw new Error(
      `Invalid SSO URL '${candidate}': ${(err as Error).message}`,
    );
  }

  const isLoopback = isLoopbackHostname(parsed.hostname);

  if (isProduction) {
    if (parsed.protocol !== "https:") {
      throw new Error(
        `Production security violation: SSO redirect URI must use HTTPS protocol, received '${parsed.href}'`,
      );
    }
  } else {
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      throw new Error(
        `Invalid SSO redirect URI scheme '${parsed.protocol}', only HTTP and HTTPS are permitted.`,
      );
    }
    if (parsed.protocol === "http:" && !isLoopback) {
      throw new Error(
        `Invalid SSO redirect URI: HTTP is only permitted on localhost, received '${parsed.href}'`,
      );
    }
  }

  return parsed.href;
}

export function normalizeOidcScopes(rawScope: string | undefined): string {
  const fallback = "openid profile email roles offline_access ai.api";
  const candidate = rawScope?.trim() ? rawScope.trim() : fallback;

  const tokens = candidate.split(/\s+/).filter(Boolean);
  const uniqueScopes = Array.from(new Set(tokens));

  if (!uniqueScopes.includes("openid")) {
    throw new Error(
      `Invalid SSO scope: 'openid' is required, received '${rawScope}'`,
    );
  }

  if (!uniqueScopes.includes("ai.api")) {
    throw new Error(
      `Invalid SSO scope: 'ai.api' resource scope is required, received '${rawScope}'`,
    );
  }

  return uniqueScopes.join(" ");
}

export function sanitizeReturnUrl(returnUrl: unknown): string {
  if (typeof returnUrl !== "string") return "/workspaces";
  const trimmed = returnUrl.trim();
  if (
    !trimmed.startsWith("/") ||
    trimmed.startsWith("//") ||
    trimmed.includes("\\")
  ) {
    return "/workspaces";
  }
  try {
    const parsed = new URL(trimmed, "http://localhost");
    if (parsed.pathname === "/signin-oidc" || parsed.pathname === "/sign-in") {
      return "/workspaces";
    }
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return "/workspaces";
  }
}

export function getOidcConfig() {
  const isProd =
    typeof import.meta !== "undefined" &&
    Boolean(import.meta.env?.PROD || import.meta.env?.MODE === "production");

  const defaultOrigin =
    typeof window !== "undefined"
      ? window.location.origin
      : "http://localhost:3001";

  const defaultFallbackAuthority = isProd
    ? "https://sso.qnu.edu.vn"
    : typeof window !== "undefined" &&
        isLoopbackHostname(window.location.hostname)
      ? "http://localhost:5000"
      : "https://sso.qnu.edu.vn";

  return {
    authority: resolveOidcAuthority(
      import.meta.env?.VITE_SSO_AUTHORITY,
      defaultFallbackAuthority,
      isProd,
    ),
    clientId: import.meta.env?.VITE_SSO_CLIENT_ID || "qnu-ai-platform",
    redirectUri: resolveOidcUrl(
      import.meta.env?.VITE_SSO_REDIRECT_URI,
      "/signin-oidc",
      defaultOrigin,
      isProd,
    ),
    postLogoutRedirectUri: resolveOidcUrl(
      import.meta.env?.VITE_SSO_POST_LOGOUT_REDIRECT_URI,
      "/sign-in",
      defaultOrigin,
      isProd,
    ),
    scope: normalizeOidcScopes(import.meta.env?.VITE_SSO_SCOPE),
  };
}

export function createOidcUserManager(
  customSettings?: Partial<UserManagerSettings>,
): UserManager {
  const config = getOidcConfig();

  const settings: UserManagerSettings = {
    authority: config.authority.replace(/\/$/, ""),
    client_id: config.clientId,
    redirect_uri: config.redirectUri,
    post_logout_redirect_uri: config.postLogoutRedirectUri,
    response_type: "code",
    scope: config.scope,
    // Never persist tokens into localStorage or sessionStorage
    userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() }),
    // Persist only transient transaction state (PKCE verifier, nonce, state) across browser redirect
    stateStore:
      typeof window !== "undefined"
        ? new WebStorageStateStore({
            store: window.sessionStorage,
            prefix: "qnu_ai_oidc_txn_",
          })
        : undefined,
    automaticSilentRenew: false,
    loadUserInfo: true,
    ...customSettings,
  };

  return new UserManager(settings);
}

export function getOidcUserManager(): UserManager {
  if (!userManagerInstance) {
    userManagerInstance = createOidcUserManager();
  }
  return userManagerInstance;
}

export function resetOidcUserManager(): void {
  userManagerInstance = null;
}

export async function loginWithSso(returnUrl?: string): Promise<void> {
  const mgr = getOidcUserManager();
  const safeReturn = sanitizeReturnUrl(
    returnUrl ||
      (typeof window !== "undefined"
        ? window.location.pathname
        : "/workspaces"),
  );
  await mgr.signinRedirect({
    state: safeReturn,
  });
}

export async function handleSsoCallback(url?: string): Promise<{
  user: OidcUser;
  accessToken: string;
  returnUrl: string;
}> {
  const mgr = getOidcUserManager();
  const user = await mgr.signinCallback(url);
  if (!user?.access_token) {
    throw new Error("Không nhận được access token từ QNU SSO.");
  }
  setAccessToken(user.access_token);
  const returnUrl = sanitizeReturnUrl(
    typeof user.state === "string" ? user.state : "/workspaces",
  );

  if (typeof window !== "undefined" && window.history?.replaceState) {
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  return { user, accessToken: user.access_token, returnUrl };
}

export async function logoutSso(): Promise<void> {
  clearAccessToken();
  const mgr = getOidcUserManager();
  try {
    await mgr.signoutRedirect();
  } catch {
    if (typeof window !== "undefined") {
      window.location.href = "/sign-in";
    }
  }
}
