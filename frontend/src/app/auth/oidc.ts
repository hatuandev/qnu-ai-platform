import {
  type User as OidcUser,
  UserManager,
  type UserManagerSettings,
  WebStorageStateStore,
} from "oidc-client-ts";
import type { CurrentUser } from "./types";

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

  // Normalize: remove trailing slash for stable oidc-client-ts discovery
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
  const fallback = "openid profile email roles ai.api offline_access";
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

const isProduction =
  typeof import.meta !== "undefined" &&
  (import.meta.env?.PROD || import.meta.env?.MODE === "production");

const defaultOrigin =
  typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:3000";

const defaultFallbackAuthority = isProduction
  ? "https://sso.qnu.edu.vn"
  : typeof window !== "undefined" &&
      isLoopbackHostname(window.location.hostname)
    ? "http://localhost:5000"
    : "https://sso.qnu.edu.vn";

export const OIDC_CONFIG = {
  authority: resolveOidcAuthority(
    import.meta.env?.VITE_SSO_AUTHORITY,
    defaultFallbackAuthority,
    Boolean(isProduction),
  ),
  clientId: import.meta.env?.VITE_SSO_CLIENT_ID || "qnu-ai-platform",
  redirectUri: resolveOidcUrl(
    import.meta.env?.VITE_SSO_REDIRECT_URI,
    "/signin-oidc",
    defaultOrigin,
    Boolean(isProduction),
  ),
  postLogoutRedirectUri: resolveOidcUrl(
    import.meta.env?.VITE_SSO_POST_LOGOUT_REDIRECT_URI,
    "/sign-in",
    defaultOrigin,
    Boolean(isProduction),
  ),
  scope: normalizeOidcScopes(import.meta.env?.VITE_SSO_SCOPE),
};

let cachedAccessToken: string | null = null;

export function setCachedAccessToken(token: string | null): void {
  cachedAccessToken = token;
}

export function getAccessToken(): string | null {
  return cachedAccessToken;
}

export function getUserManager(): UserManager {
  if (!userManagerInstance) {
    const settings: UserManagerSettings = {
      authority: OIDC_CONFIG.authority.replace(/\/$/, ""),
      client_id: OIDC_CONFIG.clientId,
      redirect_uri: OIDC_CONFIG.redirectUri,
      post_logout_redirect_uri: OIDC_CONFIG.postLogoutRedirectUri,
      response_type: "code",
      scope: OIDC_CONFIG.scope,
      automaticSilentRenew: true,
      loadUserInfo: true,
      userStore:
        typeof window !== "undefined"
          ? new WebStorageStateStore({ store: window.sessionStorage })
          : undefined,
    };

    userManagerInstance = new UserManager(settings);

    // Track access token lifetime, renewal & revocation
    userManagerInstance.events.addUserLoaded((user) => {
      setCachedAccessToken(user.access_token);
    });

    userManagerInstance.events.addUserUnloaded(() => {
      setCachedAccessToken(null);
    });

    userManagerInstance.events.addAccessTokenExpired(() => {
      setCachedAccessToken(null);
    });

    userManagerInstance.events.addSilentRenewError(() => {
      setCachedAccessToken(null);
    });

    userManagerInstance.events.addUserSignedOut(() => {
      setCachedAccessToken(null);
    });
  }
  return userManagerInstance;
}

export function parseOidcUser(oidcUser: OidcUser | null): CurrentUser | null {
  if (!oidcUser || oidcUser.expired) {
    setCachedAccessToken(null);
    return null;
  }

  if (oidcUser.access_token) {
    setCachedAccessToken(oidcUser.access_token);
  }

  const profile = oidcUser.profile || {};
  const rawRoles = profile.role || profile.roles || [];
  const roles = Array.isArray(rawRoles)
    ? (rawRoles as string[]).map((r) => String(r).trim()).filter(Boolean)
    : typeof rawRoles === "string" && rawRoles.trim()
      ? [rawRoles.trim()]
      : [];

  const rawPermissions = profile.permission || profile.permissions || [];
  const rawPermList = Array.isArray(rawPermissions)
    ? (rawPermissions as string[]).map((p) => String(p).trim()).filter(Boolean)
    : typeof rawPermissions === "string" && rawPermissions.trim()
      ? [rawPermissions.trim()]
      : [];

  // Reject wildcard "*" from SSO tokens according to strict security contract
  const permissions = rawPermList.filter((p) => p !== "*");

  const rawUserType =
    (profile.user_type as string) || (profile.userType as string) || "user";

  const userType = String(rawUserType).toLowerCase();

  return {
    sub: oidcUser.profile.sub || "sso-user",
    name:
      oidcUser.profile.name ||
      oidcUser.profile.preferred_username ||
      "Cán bộ QNU",
    email: oidcUser.profile.email || "",
    roles,
    userType,
    studentId: (profile.student_id as string) || undefined,
    permissions,
    roleMetadata: [],
    accessToken: oidcUser.access_token,
  };
}

export async function loginWithSso(returnUrl?: string): Promise<void> {
  const mgr = getUserManager();
  await mgr.signinRedirect({
    state:
      returnUrl ||
      (typeof window !== "undefined" ? window.location.pathname : "/dashboard"),
  });
}

export async function handleSsoCallback(): Promise<{
  user: OidcUser;
  returnUrl?: string;
}> {
  const mgr = getUserManager();
  const user = await mgr.signinCallback();
  if (!user) {
    throw new Error("Không nhận được dữ liệu xác thực từ QNU SSO.");
  }
  const returnUrl = typeof user.state === "string" ? user.state : undefined;
  return { user, returnUrl };
}

export async function logoutSso(): Promise<void> {
  setCachedAccessToken(null);
  const mgr = getUserManager();
  try {
    await mgr.signoutRedirect();
  } catch {
    await mgr.removeUser();
    window.location.href = "/sign-in";
  }
}

export async function getStoredOidcUser(): Promise<CurrentUser | null> {
  try {
    const mgr = getUserManager();
    const user = await mgr.getUser();
    return parseOidcUser(user);
  } catch {
    return null;
  }
}
