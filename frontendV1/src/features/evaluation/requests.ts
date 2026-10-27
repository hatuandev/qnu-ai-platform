import { indexingPaths, type V1Client } from "@/app/api/v1";
import type {
  EvaluationRequest,
  EvaluationResult,
  IndexManifest,
} from "./types";
export function getEvaluationManifest(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  runId: string,
  signal?: AbortSignal,
) {
  return client.get<IndexManifest>(
    indexingPaths.manifest(workspaceId, collectionId, runId),
    { signal },
  );
}
export function runEvaluation(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  body: EvaluationRequest,
) {
  return client.post<EvaluationResult>(
    indexingPaths.evaluations(workspaceId, collectionId),
    body,
  );
}
