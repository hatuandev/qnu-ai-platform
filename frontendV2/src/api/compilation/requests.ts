/**
 * HTTP request functions for Compilation domain.
 */

import { v1Client } from "../v1-client";
import { compilationPaths } from "./endpoints";
import type {
  CompilationCreatedResponse,
  CompilationDraftResponse,
  CompilationProgressResponse,
  EditCommitRequest,
  EditContextResponse,
  EditPreviewRequest,
  EditPreviewResponse,
} from "./types";

export async function getCompilationDraft(
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationDraftResponse> {
  return v1Client.get<CompilationDraftResponse>(
    compilationPaths.draft(workspaceId, collectionId, runId),
    options,
  );
}

export async function getCompilationMarkdown(
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<string> {
  return v1Client.requestText(
    compilationPaths.markdown(workspaceId, collectionId, runId),
    options,
  );
}

export async function getEditContext(
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
): Promise<EditContextResponse> {
  return v1Client.get<EditContextResponse>(
    compilationPaths.editContext(workspaceId, collectionId, runId),
    options,
  );
}

export async function createEditPreview(
  workspaceId: string,
  collectionId: string,
  runId: string,
  data: EditPreviewRequest,
  options?: { signal?: AbortSignal },
): Promise<EditPreviewResponse> {
  return v1Client.post<EditPreviewResponse>(
    compilationPaths.editPreviews(workspaceId, collectionId, runId),
    data,
    options,
  );
}

export async function commitEdits(
  workspaceId: string,
  collectionId: string,
  runId: string,
  data: EditCommitRequest,
  idempotencyKey?: string,
  options?: { signal?: AbortSignal },
): Promise<CompilationCreatedResponse> {
  return v1Client.post<CompilationCreatedResponse>(
    compilationPaths.edits(workspaceId, collectionId, runId),
    data,
    {
      idempotencyKey,
      signal: options?.signal,
    },
  );
}

export function getCompilationProgress(
  workspaceId: string,
  collectionId: string,
  runId: string,
  options?: { signal?: AbortSignal },
) {
  return v1Client.get<CompilationProgressResponse>(
    compilationPaths.progress(workspaceId, collectionId, runId),
    options,
  );
}
