import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  createAnswerReview,
  labelAnswerReviewItem,
  listAnswerReviews,
} from "@/features/answer-review/requests";
import type {
  AnswerReview,
  AnswerReviewCreateInput,
  AnswerReviewLabelInput,
} from "@/features/answer-review/types";

export const answerReviewKeys = {
  root: (sessionId: number, workspaceId: string, assistantId: string) =>
    [
      "v1",
      sessionId,
      "workspaces",
      workspaceId,
      "assistants",
      "answer-reviews",
      assistantId,
    ] as const,

  list: (sessionId: number, workspaceId: string, assistantId: string) =>
    [
      ...answerReviewKeys.root(sessionId, workspaceId, assistantId),
      "list",
    ] as const,
};

const REVIEW_LIST_LIMIT = 50;

export function useAnswerReviewsQuery(
  workspaceId: string,
  assistantId: string,
  options: { enabled?: boolean } = {},
) {
  const { sessionId } = useV1Auth();
  return useQuery<AnswerReview[]>({
    queryKey: answerReviewKeys.list(sessionId, workspaceId, assistantId),
    queryFn: ({ signal }) =>
      listAnswerReviews(
        v1Client,
        workspaceId,
        assistantId,
        { limit: REVIEW_LIST_LIMIT },
        { signal },
      ),
    enabled: Boolean(workspaceId && assistantId && options.enabled !== false),
    // Only observe a run another tab started; the UI never fakes progress.
    refetchInterval: (query) =>
      query.state.data?.some((review) => review.status === "running")
        ? 4000
        : false,
  });
}

export function useCreateAnswerReview(
  workspaceId: string,
  assistantId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    AnswerReview,
    Error,
    { input: AnswerReviewCreateInput; idempotencyKey: string }
  >({
    mutationFn: ({ input, idempotencyKey }) =>
      createAnswerReview(
        v1Client,
        workspaceId,
        assistantId,
        input,
        idempotencyKey,
      ),
    onSuccess: (review) => {
      queryClient.setQueryData<AnswerReview[]>(
        answerReviewKeys.list(sessionId, workspaceId, assistantId),
        (current) =>
          current
            ? [review, ...current.filter((item) => item.id !== review.id)]
            : [review],
      );
    },
  });
}

export function useLabelAnswerReviewItem(
  workspaceId: string,
  assistantId: string,
) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();

  return useMutation<
    AnswerReview,
    Error,
    {
      reviewId: string;
      itemId: string;
      input: AnswerReviewLabelInput;
    }
  >({
    mutationFn: ({ reviewId, itemId, input }) =>
      labelAnswerReviewItem(
        v1Client,
        workspaceId,
        assistantId,
        reviewId,
        itemId,
        input,
      ),
    onSuccess: (review) => {
      queryClient.setQueryData<AnswerReview[]>(
        answerReviewKeys.list(sessionId, workspaceId, assistantId),
        (current) =>
          current?.map((item) => (item.id === review.id ? review : item)) ?? [
            review,
          ],
      );
    },
  });
}
