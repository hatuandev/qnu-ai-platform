import { createV1Client } from "./client";
import { API_V1_PREFIX } from "./endpoints";
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

export type {
  BlobResponse,
  ProblemDetail,
  QueryValue,
  V1Client,
  V1ErrorKind,
  V1RequestOptions,
} from "./client";
export {
  ApiProblemError,
  parseContentDispositionFileName,
} from "./client";
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
} from "./endpoints";
export type { V1TokenState } from "./session-token";
export {
  clearAccessToken,
  getAccessToken,
  getTokenState,
  setAccessToken,
  subscribeToken,
} from "./session-token";
