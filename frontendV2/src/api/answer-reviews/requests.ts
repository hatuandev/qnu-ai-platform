/**
 * HTTP request functions for assistant answer reviews.
 * Mirrors `backendV1/qnu/domains/answer_review/router.py`.
 *
 * A review runs the real answer pipeline synchronously, so creating one can
 * take minutes; the default 30s client timeout would abort a healthy run.
 */

import { v1Client } from "../v1-client";
import { answerReviewPaths } from "./endpoints";
import type {
  AnswerReview,
  AnswerReviewCreateRequest,
  AnswerReviewLabelRequest,
} from "./types";

export const ANSWER_REVIEW_RUN_TIMEOUT_MS = 600_000;

export async function listAnswerReviews(
  workspaceId: string,
  assistantId: string,
  params?: { limit?: number; offset?: number },
  options?: { signal?: AbortSignal },
): Promise<AnswerReview[]> {
  return v1Client.get<AnswerReview[]>(
    answerReviewPaths.list(workspaceId, assistantId),
    {
      searchParams: {
        limit: params?.limit ?? 20,
        offset: params?.offset ?? 0,
      },
      signal: options?.signal,
    },
  );
}

export async function createAnswerReview(
  workspaceId: string,
  assistantId: string,
  data: AnswerReviewCreateRequest,
  options: { idempotencyKey: string; signal?: AbortSignal },
): Promise<AnswerReview> {
  return v1Client.post<AnswerReview>(
    answerReviewPaths.list(workspaceId, assistantId),
    data,
    {
      idempotencyKey: options.idempotencyKey,
      signal: options.signal,
      timeoutMs: ANSWER_REVIEW_RUN_TIMEOUT_MS,
    },
  );
}

export async function getAnswerReview(
  workspaceId: string,
  assistantId: string,
  reviewId: string,
  options?: { signal?: AbortSignal },
): Promise<AnswerReview> {
  return v1Client.get<AnswerReview>(
    answerReviewPaths.detail(workspaceId, assistantId, reviewId),
    { signal: options?.signal },
  );
}

export async function labelAnswerReviewItem(
  workspaceId: string,
  assistantId: string,
  reviewId: string,
  itemId: string,
  data: AnswerReviewLabelRequest,
  options?: { signal?: AbortSignal },
): Promise<AnswerReview> {
  return v1Client.put<AnswerReview>(
    answerReviewPaths.item(workspaceId, assistantId, reviewId, itemId),
    data,
    { signal: options?.signal },
  );
}
