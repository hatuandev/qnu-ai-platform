import { createV1Client } from "@/app/api/v1/client";
import { API_V1_PREFIX } from "@/app/api/v1/endpoints";
import {
  clearAccessToken,
  getAccessToken,
  getTokenState,
} from "@/app/api/v1/session-token";

/**
 * Same-origin by default: the Vite dev server proxies `/platform/v1alpha1` to
 * backendV1 on port 8002 (see `vite.config.ts`). Set `VITE_QNU_API_BASE_URL` to
 * an absolute origin only when the API is served from a different host.
 */
const configuredBaseUrl = (
  import.meta.env.VITE_QNU_API_BASE_URL as string | undefined
)?.trim();

export const v1ApiBaseUrl = (configuredBaseUrl ?? "").replace(/\/$/, "");

export const v1Client = createV1Client({
  baseUrl: v1ApiBaseUrl,
  prefix: API_V1_PREFIX,
  getToken: getAccessToken,
  getSessionId: () => getTokenState().sessionId,
  onUnauthorized: (context) =>
    clearAccessToken({ sessionId: context?.sessionId, expired: true }),
});

/**
 * Unauthenticated client for `/auth/login` only. A wrong access key must surface
 * as a credentials error, not as "your session expired", so this instance never
 * trips the shared 401 handler.
 */
export const v1PublicClient = createV1Client({
  baseUrl: v1ApiBaseUrl,
  prefix: API_V1_PREFIX,
});

export type {
  BlobResponse,
  ProblemDetail,
  QueryValue,
  V1Client,
  V1ErrorKind,
  V1RequestOptions,
} from "@/app/api/v1/client";
export {
  ApiProblemError,
  parseContentDispositionFileName,
} from "@/app/api/v1/client";
export {
  API_V1_DEFAULT_TARGET,
  API_V1_PREFIX,
  assistantPaths,
  authPaths,
  compilationPaths,
  conversationPaths,
  indexingPaths,
  isV1Route,
  knowledgePaths,
  lifecyclePaths,
  modelopsPaths,
  ocrPaths,
  operationsPaths,
  preparationPaths,
  QNU_PERMISSIONS,
  V1_ROUTE_PREFIXES,
  workspacePaths,
} from "@/app/api/v1/endpoints";
export type { V1TokenState } from "@/app/api/v1/session-token";
export {
  clearAccessToken,
  getAccessToken,
  getTokenState,
  setAccessToken,
  subscribeToken,
} from "@/app/api/v1/session-token";
