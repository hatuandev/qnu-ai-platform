/**
 * TanStack Query hooks for assistant answer reviews.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createAnswerReview,
  getAnswerReview,
  labelAnswerReviewItem,
  listAnswerReviews,
} from "./requests";
import type {
  AnswerReview,
  AnswerReviewCreateRequest,
  AnswerReviewLabelRequest,
} from "./types";

export const answerReviewKeys = {
  all: ["v1", "answer-reviews"] as const,
  list: (workspaceId: string, assistantId: string) =>
    [...answerReviewKeys.all, "list", workspaceId, assistantId] as const,
  detail: (workspaceId: string, assistantId: string, reviewId: string) =>
    [
      ...answerReviewKeys.all,
      "detail",
      workspaceId,
      assistantId,
      reviewId,
    ] as const,
};

const RUNNING_POLL_MS = 4000;

export function useAnswerReviewsQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId
        ? answerReviewKeys.list(workspaceId, assistantId)
        : [...answerReviewKeys.all, "list", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return listAnswerReviews(
        workspaceId,
        assistantId,
        { limit: 20 },
        { signal },
      );
    },
    enabled: Boolean(workspaceId && assistantId),
    refetchInterval: (query) =>
      query.state.data?.some((review) => review.status === "running")
        ? RUNNING_POLL_MS
        : false,
  });
}

export function useAnswerReviewQuery(
  workspaceId?: string | null,
  assistantId?: string | null,
  reviewId?: string | null,
) {
  return useQuery({
    queryKey:
      workspaceId && assistantId && reviewId
        ? answerReviewKeys.detail(workspaceId, assistantId, reviewId)
        : [...answerReviewKeys.all, "detail", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId || !assistantId || !reviewId) {
        throw new Error("workspaceId, assistantId and reviewId are required");
      }
      return getAnswerReview(workspaceId, assistantId, reviewId, { signal });
    },
    enabled: Boolean(workspaceId && assistantId && reviewId),
  });
}

export function useCreateAnswerReviewMutation(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      data,
      idempotencyKey,
    }: {
      data: AnswerReviewCreateRequest;
      idempotencyKey: string;
    }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return createAnswerReview(workspaceId, assistantId, data, {
        idempotencyKey,
      });
    },
    onSuccess: (review) => {
      if (workspaceId && assistantId) {
        queryClient.setQueryData(
          answerReviewKeys.detail(workspaceId, assistantId, review.id),
          review,
        );
        void queryClient.invalidateQueries({
          queryKey: answerReviewKeys.list(workspaceId, assistantId),
        });
      }
    },
  });
}

export function useLabelAnswerReviewItemMutation(
  workspaceId?: string | null,
  assistantId?: string | null,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reviewId,
      itemId,
      data,
    }: {
      reviewId: string;
      itemId: string;
      data: AnswerReviewLabelRequest;
    }) => {
      if (!workspaceId || !assistantId) {
        throw new Error("workspaceId and assistantId are required");
      }
      return labelAnswerReviewItem(
        workspaceId,
        assistantId,
        reviewId,
        itemId,
        data,
      );
    },
    onSuccess: (review: AnswerReview) => {
      if (workspaceId && assistantId) {
        queryClient.setQueryData(
          answerReviewKeys.detail(workspaceId, assistantId, review.id),
          review,
        );
        void queryClient.invalidateQueries({
          queryKey: answerReviewKeys.list(workspaceId, assistantId),
        });
      }
    },
  });
}
