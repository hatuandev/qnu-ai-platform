import { assistantPaths } from "@/api/assistants/endpoints";

/** Answer reviews live under the assistant they test. */
export const answerReviewPaths = {
  list: assistantPaths.answerReviews,
  detail: assistantPaths.answerReview,
  item: assistantPaths.answerReviewItem,
} as const;
