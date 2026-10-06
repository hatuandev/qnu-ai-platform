import { getAccessToken } from "@/app/auth/oidc";

export const BASE_URL = "/platform/v1alpha1";

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/**
 * Returns HTTP Headers with active QNU SSO Bearer Token if present.
 */
export function getAuthHeaders(headers?: HeadersInit): Headers {
  const h = new Headers(headers);
  const token = getAccessToken();
  if (token && !h.has("Authorization") && !h.has("authorization")) {
    h.set("Authorization", `Bearer ${token}`);
  }
  return h;
}
