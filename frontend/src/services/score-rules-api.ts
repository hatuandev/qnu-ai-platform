import type {
  ScorePreviewResult,
  ScoreRuleAction,
  ScoreRuleDefinition,
  ScoreRuleRegistry,
} from "@/types/score-rules";
import { BASE_URL, getAuthHeaders } from "./http-client";
import { extractErrorMessage } from "./knowledge-api";

async function request<T>(
  collectionId: string,
  path = "",
  body?: unknown,
): Promise<T> {
  const response = await fetch(
    `${BASE_URL}/knowledge/collections/${encodeURIComponent(collectionId)}/score-rules${path}`,
    {
      method: body === undefined ? "GET" : "POST",
      credentials: "include",
      headers: getAuthHeaders(
        body === undefined ? undefined : { "Content-Type": "application/json" },
      ),
      body: body === undefined ? undefined : JSON.stringify(body),
    },
  );
  if (!response.ok) {
    const error: unknown = await response.json().catch(() => null);
    throw new Error(
      extractErrorMessage(
        error,
        `Không thể xử lý quy tắc (HTTP ${response.status}).`,
      ),
    );
  }
  return response.json() as Promise<T>;
}

export const scoreRulesApi = {
  list: (collectionId: string) => request<ScoreRuleRegistry>(collectionId),
  importDrafts: (
    collectionId: string,
    definitions: Record<string, unknown>[],
    version: number,
    requestId: string,
  ) =>
    request<ScoreRuleRegistry>(collectionId, "/import", {
      definitions,
      expected_version: version,
      request_id: requestId,
    }),
  create: (
    collectionId: string,
    definition: ScoreRuleDefinition,
    version: number,
    requestId: string,
  ) =>
    request<ScoreRuleRegistry>(collectionId, "", {
      definition,
      expected_version: version,
      request_id: requestId,
    }),
  act: (
    collectionId: string,
    ruleId: string,
    action: ScoreRuleAction,
    reason: string,
    version: number,
    requestId: string,
  ) =>
    request<ScoreRuleRegistry>(
      collectionId,
      `/${encodeURIComponent(ruleId)}/actions`,
      {
        action,
        reason,
        expected_version: version,
        request_id: requestId,
        confirmed: true,
      },
    ),
  preview: (
    collectionId: string,
    ruleId: string,
    combination: string,
    score: string,
    version: number,
  ) =>
    request<ScorePreviewResult>(
      collectionId,
      `/${encodeURIComponent(ruleId)}/preview`,
      {
        combination,
        score,
        expected_version: version,
      },
    ),
};
