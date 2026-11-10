/**
 * Configured V1 API clients for QNU AI Platform.
 *
 * Separated from `client.ts` (types and factory) and `index.ts` (barrel export)
 * to prevent circular dependencies with domain request modules.
 */

import { createV1Client } from "./client";
import { API_V1_PREFIX } from "./config";
import {
  clearAccessToken,
  getAccessToken,
  getTokenState,
} from "./session-token";

const configuredBaseUrl = (
  import.meta as unknown as { env: Record<string, string | undefined> }
).env?.VITE_QNU_API_BASE_URL?.trim();

export const v1ApiBaseUrl = (configuredBaseUrl ?? "").replace(/\/$/, "");

export const v1Client = createV1Client({
  baseUrl: v1ApiBaseUrl,
  prefix: API_V1_PREFIX,
  getToken: getAccessToken,
  getSessionId: () => getTokenState().sessionId,
  onUnauthorized: (context?: { sessionId?: number }) =>
    clearAccessToken({ sessionId: context?.sessionId, expired: true }),
});

export const v1PublicClient = createV1Client({
  baseUrl: v1ApiBaseUrl,
  prefix: API_V1_PREFIX,
});
