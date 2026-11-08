import type { V1Client } from "@/app/api/v1";
import { assistantPaths } from "@/app/api/v1";
import type {
  AnswerReview,
  AnswerReviewCreateInput,
  AnswerReviewLabelInput,
  AnswerReviewListParams,
} from "@/features/answer-review/types";

/**
 * Lists the assistant's small answer test runs.
 * The backend returns `AnswerReviewResponse[]`.
 */
export function listAnswerReviews(
  client: V1Client,
  workspaceId: string,
  assistantId: string,
  params: AnswerReviewListParams = {},
  options?: { signal?: AbortSignal },
): Promise<AnswerReview[]> {
  return client.get<AnswerReview[]>(
    assistantPaths.answerReviews(workspaceId, assistantId),
    {
      searchParams: {
        limit: params.limit ?? 20,
        offset: params.offset ?? 0,
      },
      signal: options?.signal,
    },
  );
}

/**
 * Runs 1-3 questions through the real answer pipeline on published content.
 *
 * `timeoutMs: null` is deliberate: each question performs retrieval and live
 * model generation, so a 30s default would abort a valid run.
 */
export function createAnswerReview(
  client: V1Client,
  workspaceId: string,
  assistantId: string,
  input: AnswerReviewCreateInput,
  idempotencyKey: string,
  options?: { signal?: AbortSignal },
): Promise<AnswerReview> {
  return client.post<AnswerReview>(
    assistantPaths.answerReviews(workspaceId, assistantId),
    { questions: input.questions.map((question) => question.trim()) },
    {
      idempotencyKey,
      timeoutMs: null,
      signal: options?.signal,
    },
  );
}

export function labelAnswerReviewItem(
  client: V1Client,
  workspaceId: string,
  assistantId: string,
  reviewId: string,
  itemId: string,
  input: AnswerReviewLabelInput,
  options?: { signal?: AbortSignal },
): Promise<AnswerReview> {
  return client.put<AnswerReview>(
    assistantPaths.answerReviewItem(workspaceId, assistantId, reviewId, itemId),
    {
      label: input.label,
      note: input.note?.trim() ?? "",
    },
    { signal: options?.signal },
  );
}
