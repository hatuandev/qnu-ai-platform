import {
  type User as OidcUser,
  UserManager,
  type UserManagerSettings,
  WebStorageStateStore,
} from "oidc-client-ts";
import type { CurrentUser } from "@/app/auth/types";

let userManagerInstance: UserManager | null = null;

export const OIDC_CONFIG = {
  authority:
    import.meta.env.VITE_SSO_AUTHORITY ||
    (typeof window !== "undefined" && window.location.hostname === "localhost"
      ? "http://localhost:5000"
      : "https://sso.qnu.edu.vn"),
  clientId: import.meta.env.VITE_SSO_CLIENT_ID || "qnu-ai-platform",
  redirectUri:
    typeof window !== "undefined"
      ? `${window.location.origin}/signin-oidc`
      : "http://localhost:3000/signin-oidc",
  postLogoutRedirectUri:
    typeof window !== "undefined"
      ? `${window.location.origin}/sign-in`
      : "http://localhost:3000/sign-in",
  scope: "openid profile email roles ai.api offline_access",
};

let cachedAccessToken: string | null = null;

export function setCachedAccessToken(token: string | null): void {
  cachedAccessToken = token;
}

export function getAccessToken(): string | null {
  if (cachedAccessToken) return cachedAccessToken;
  if (typeof window === "undefined") return null;

  try {
    const authority = OIDC_CONFIG.authority.replace(/\/$/, "");
    const clientId = OIDC_CONFIG.clientId;
    const key = `oidc.user:${authority}:${clientId}`;
    const raw = window.localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed?.access_token) {
        cachedAccessToken = parsed.access_token;
        return parsed.access_token;
      }
    }
  } catch {
    // ignore
  }
  return null;
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
          ? new WebStorageStateStore({ store: window.localStorage })
          : undefined,
    };

    userManagerInstance = new UserManager(settings);

    // Track access token lifetime & renewal
    userManagerInstance.events.addUserLoaded((user) => {
      setCachedAccessToken(user.access_token);
    });

    userManagerInstance.events.addUserUnloaded(() => {
      setCachedAccessToken(null);
    });
  }
  return userManagerInstance;
}

export function parseOidcUser(oidcUser: OidcUser | null): CurrentUser | null {
  if (!oidcUser || oidcUser.expired) return null;

  if (oidcUser.access_token) {
    setCachedAccessToken(oidcUser.access_token);
  }

  const profile = oidcUser.profile || {};
  const rawRoles = profile.role || profile.roles || [];
  const roles = Array.isArray(rawRoles)
    ? rawRoles
    : typeof rawRoles === "string"
      ? [rawRoles]
      : [];

  const rawPermissions = profile.permission || profile.permissions || [];
  const permissions = Array.isArray(rawPermissions)
    ? (rawPermissions as string[])
    : typeof rawPermissions === "string"
      ? [rawPermissions]
      : [];

  const rawUserType =
    (profile.user_type as string) ||
    (profile.userType as string) ||
    (roles.some((r) => r.toLowerCase().includes("admin"))
      ? "admin"
      : roles.some(
            (r) =>
              r.toLowerCase().includes("lecturer") ||
              r.toLowerCase().includes("teacher"),
          )
        ? "lecturer"
        : roles.some(
              (r) =>
                r.toLowerCase().includes("staff") ||
                r.toLowerCase().includes("officer"),
            )
          ? "staff"
          : "student");

  const userType = String(rawUserType).toLowerCase();

  // Mặc định quyền cơ bản nếu chưa được gán role chuyên biệt
  const defaultPermissions =
    userType === "student"
      ? ["ai.access.read", "ai.chat.access", "ai.chat.export"]
      : [
          "ai.access.read",
          "ai.chat.access",
          "ai.chat.export",
          "ai.assistants.view",
          "ai.knowledge.view",
        ];

  return {
    sub: oidcUser.profile.sub || "sso-user",
    name:
      oidcUser.profile.name ||
      oidcUser.profile.preferred_username ||
      "Cán bộ QNU",
    email: oidcUser.profile.email || "",
    roles: roles.length > 0 ? roles : [userType],
    userType,
    studentId: (profile.student_id as string) || undefined,
    permissions: permissions.length > 0 ? permissions : defaultPermissions,
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
