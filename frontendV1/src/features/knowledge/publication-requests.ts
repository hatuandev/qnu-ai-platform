import { ApiProblemError, type V1Client } from "../../app/api/v1/client.ts";
import { compiledDocumentPaths } from "../../app/api/v1/endpoints.ts";
import type { DraftDocumentResponse } from "./compilation-types.ts";
import type {
  AutomaticMetadataPreview,
  CreateDocumentRequest,
  DecisionCommitRequest,
  DecisionPreviewRequest,
  DecisionPreviewResponse,
  DecisionResponse,
  DocumentResponse,
  PublishedResponse,
  RegisterVersionRequest,
  RegistrationResponse,
  ReviewGateResponse,
  VersionResponse,
} from "./publication-types.ts";

export function getRegistrationMetadata(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  signal?: AbortSignal,
): Promise<AutomaticMetadataPreview> {
  const path = compiledDocumentPaths.documents(workspaceId, collectionId);
  return client.get(
    `${path}/registration-metadata/${encodeURIComponent(runId)}`,
    { signal },
  );
}

export async function createCompiledDocument(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  input: CreateDocumentRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<RegistrationResponse> {
  const path = compiledDocumentPaths.documents(workspaceId, collectionId);
  return client.post<RegistrationResponse>(path, input, {
    idempotencyKey,
    signal: options?.signal,
  });
}

export async function listCompiledDocuments(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  limit = 20,
  offset = 0,
  options?: { signal?: AbortSignal },
): Promise<DocumentResponse[]> {
  const path = compiledDocumentPaths.documents(workspaceId, collectionId);
  return client.get<DocumentResponse[]>(path, {
    searchParams: { limit, offset },
    signal: options?.signal,
  });
}

export async function getCompiledDocument(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  options?: { signal?: AbortSignal },
): Promise<DocumentResponse> {
  const path = compiledDocumentPaths.document(
    workspaceId,
    collectionId,
    documentId,
  );
  return client.get<DocumentResponse>(path, {
    signal: options?.signal,
  });
}

export async function createCompiledVersion(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  input: RegisterVersionRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<RegistrationResponse> {
  const path = compiledDocumentPaths.versions(
    workspaceId,
    collectionId,
    documentId,
  );
  return client.post<RegistrationResponse>(path, input, {
    idempotencyKey,
    signal: options?.signal,
  });
}

export async function listCompiledVersions(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  limit = 20,
  offset = 0,
  options?: { signal?: AbortSignal },
): Promise<VersionResponse[]> {
  const path = compiledDocumentPaths.versions(
    workspaceId,
    collectionId,
    documentId,
  );
  return client.get<VersionResponse[]>(path, {
    searchParams: { limit, offset },
    signal: options?.signal,
  });
}

export async function getCompiledVersion(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  options?: { signal?: AbortSignal },
): Promise<VersionResponse> {
  const path = compiledDocumentPaths.version(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  return client.get<VersionResponse>(path, {
    signal: options?.signal,
  });
}

export async function getCompiledVersionDraft(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  options?: { signal?: AbortSignal },
): Promise<DraftDocumentResponse> {
  const path = compiledDocumentPaths.versionDraft(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  return client.get<DraftDocumentResponse>(path, {
    searchParams: { group_by_source: true },
    signal: options?.signal,
  });
}

export async function getCompiledVersionReviewGate(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  options?: { signal?: AbortSignal },
): Promise<ReviewGateResponse> {
  const path = compiledDocumentPaths.versionReviewGate(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  return client.get<ReviewGateResponse>(path, {
    signal: options?.signal,
  });
}

export async function createDecisionPreview(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  input: DecisionPreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<DecisionPreviewResponse> {
  const path = compiledDocumentPaths.decisionPreview(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  return client.post<DecisionPreviewResponse>(path, input, {
    signal: options?.signal,
  });
}

export async function commitDecision(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  input: DecisionCommitRequest,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<DecisionResponse> {
  const path = compiledDocumentPaths.decisions(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  return client.post<DecisionResponse>(path, input, {
    idempotencyKey,
    signal: options?.signal,
  });
}

export async function getCompiledDocumentHistory(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  limit = 50,
  offset = 0,
  options?: { signal?: AbortSignal },
): Promise<DecisionResponse[]> {
  const path = compiledDocumentPaths.history(
    workspaceId,
    collectionId,
    documentId,
  );
  return client.get<DecisionResponse[]>(path, {
    searchParams: { limit, offset },
    signal: options?.signal,
  });
}

/**
 * Reads the currently published version of a document.
 *
 * Only the exact "this document has no active publication" answer means
 * "empty": HTTP 404 carrying `published_compilation_not_found`. Every other
 * 404 (unknown document, `resource_unavailable`, …), a 5xx that happens to
 * carry the same code, permission, storage and network failures stay errors —
 * turning them into an empty state would tell an operator to publish again
 * while the real status is still unknown.
 */
export const PUBLISHED_COMPILATION_NOT_FOUND =
  "published_compilation_not_found";

export function isEmptyPublicationAnswer(error: unknown): boolean {
  return (
    error instanceof ApiProblemError &&
    error.status === 404 &&
    error.code === PUBLISHED_COMPILATION_NOT_FOUND
  );
}

export async function getPublishedCompiledDocument(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  documentId: string,
  options?: { signal?: AbortSignal },
): Promise<PublishedResponse | null> {
  const path = compiledDocumentPaths.published(
    workspaceId,
    collectionId,
    documentId,
  );
  try {
    return await client.get<PublishedResponse>(path, {
      signal: options?.signal,
    });
  } catch (err) {
    if (isEmptyPublicationAnswer(err)) return null;
    throw err;
  }
}
