/**
 * HTTP request functions for Compiled Documents and Publication domain.
 */

import { v1Client } from "../v1-client";
import { compiledDocumentPaths } from "./endpoints";
import type {
  AutomaticMetadataPreview,
  CreateDocumentRequest,
  DecisionCommitRequest,
  DecisionPreviewRequest,
  DecisionPreviewResponse,
  DecisionResponse,
  DocumentResponse,
  DocumentSummaryResponse,
  RegisterVersionRequest,
  RegistrationResponse,
  ReviewGateResponse,
  VersionResponse,
} from "./types";

export async function createCompiledDocument(
  workspaceId: string,
  collectionId: string,
  data: CreateDocumentRequest,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<RegistrationResponse> {
  return v1Client.post<RegistrationResponse>(
    compiledDocumentPaths.documents(workspaceId, collectionId),
    data,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function registerCompiledDocumentVersion(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  data: RegisterVersionRequest,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<RegistrationResponse> {
  return v1Client.post<RegistrationResponse>(
    compiledDocumentPaths.versions(workspaceId, collectionId, documentId),
    data,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function getCompiledVersion(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  options?: { signal?: AbortSignal },
): Promise<VersionResponse> {
  return v1Client.get<VersionResponse>(
    compiledDocumentPaths.version(
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ),
    options,
  );
}

export async function listCompiledDocuments(
  workspaceId: string,
  collectionId: string,
  options?: { signal?: AbortSignal },
): Promise<DocumentResponse[]> {
  return v1Client.get<DocumentResponse[]>(
    compiledDocumentPaths.documents(workspaceId, collectionId),
    options,
  );
}

export async function getRegistrationMetadata(
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<AutomaticMetadataPreview> {
  return v1Client.get<AutomaticMetadataPreview>(
    compiledDocumentPaths.registrationMetadata(
      workspaceId,
      collectionId,
      runId,
    ),
    options,
  );
}

export async function getReviewGate(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  options?: { signal?: AbortSignal },
): Promise<ReviewGateResponse> {
  return v1Client.get<ReviewGateResponse>(
    compiledDocumentPaths.versionReviewGate(
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ),
    options,
  );
}

export async function createDecisionPreview(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  data: DecisionPreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<DecisionPreviewResponse> {
  return v1Client.post<DecisionPreviewResponse>(
    compiledDocumentPaths.decisionPreview(
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ),
    data,
    options,
  );
}

export async function commitDecision(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  versionId: string,
  data: DecisionCommitRequest,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<DecisionResponse> {
  return v1Client.post<DecisionResponse>(
    compiledDocumentPaths.decisions(
      workspaceId,
      collectionId,
      documentId,
      versionId,
    ),
    data,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export async function getDocumentSummary(
  workspaceId: string,
  collectionId: string,
  documentId: string,
  options?: { signal?: AbortSignal },
): Promise<DocumentSummaryResponse> {
  return v1Client.get<DocumentSummaryResponse>(
    compiledDocumentPaths.summary(workspaceId, collectionId, documentId),
    options,
  );
}
