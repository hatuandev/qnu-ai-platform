/**
 * Global API configurations, prefixes, and permissions for QNU AI v1 API.
 */

export const API_V1_PREFIX = "/platform/v1alpha1";

/** Default backendV1 port; the Vite dev proxy forwards the prefix here. */
export const API_V1_DEFAULT_TARGET = "http://127.0.0.1:8002";

/** Permissions enforced by backendV1 for the screens in this batch. */
export const QNU_PERMISSIONS = {
  workspacesManage: "ai.workspaces.manage",
  modelsManage: "ai.models.manage",
} as const;

/** Routes owned by the v1 client; everything else stays on the KTX template. */
export const V1_ROUTE_PREFIXES = [
  "/workspaces",
  "/modelops",
  "/dashboard",
  "/providers",
] as const;

export function isV1Route(pathname: string): boolean {
  return V1_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}
