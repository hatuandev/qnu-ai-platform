export { describeDevAutoLoginError } from "@/app/auth/v1/auto-login-errors";
export type { DevAutoLoginErrorCode } from "@/app/auth/v1/dev-auto-login";
export {
  clearDevAutoLoginSuppression,
  DEV_AUTO_LOGIN_PATH,
  DevAutoLoginError,
  isDevAutoLoginAvailable,
  isDevAutoLoginSuppressed,
  isSsoCallbackActive,
  requestDevAutoLogin,
  resetDevAutoLoginState,
  resetSsoCallbackState,
  setSsoCallbackActive,
  subscribeSsoCallback,
  suppressDevAutoLogin,
} from "@/app/auth/v1/dev-auto-login";
export { describeV1AuthError, V1SessionGate } from "@/app/auth/v1/gate";
export {
  createOidcUserManager,
  getOidcConfig,
  getOidcUserManager,
  handleSsoCallback,
  isLoopbackHostname,
  loginWithSso,
  logoutSso,
  normalizeOidcScopes,
  resetOidcUserManager,
  resolveOidcAuthority,
  resolveOidcUrl,
  sanitizeReturnUrl,
} from "@/app/auth/v1/oidc";
export type {
  CallerWorkspaceRole,
  MembershipLike,
  WorkspaceRole,
} from "@/app/auth/v1/permissions";
export {
  canChooseWorkspaceDefaults,
  canManageMembers,
  hasAnyV1Permission,
  hasV1Permission,
  isModelAdmin,
  isPlatformWorkspaceAdmin,
  resolveCallerWorkspaceRole,
} from "@/app/auth/v1/permissions";
export type { V1AuthStatus, V1AutoLoginPhase } from "@/app/auth/v1/provider";
export {
  isValidActor,
  useV1Auth,
  V1AuthProvider,
  v1MeQueryKey,
} from "@/app/auth/v1/provider";
export type {
  V1Actor,
  V1ActorResponse,
  V1LoginResponse,
} from "@/app/auth/v1/types";
