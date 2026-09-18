/** Base HTTP configuration and constants for API services */

export const BASE_URL = "/platform/v1alpha1";

export function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
