/**
 * Helper quyết định hành động thử lại (Retry) và banner hành động duy nhất
 * cho nguồn nhóm tài liệu trong Kho tri thức.
 *
 * Thứ tự ưu tiên banner:
 * 1. failed: Khi có lỗi lập chỉ mục hoặc xuất bản
 * 2. review: Khi có staging index chờ xuất bản
 * 3. updates: Khi có cập nhật mới cần đồng bộ
 * 4. none: Khi nguồn đã sẵn sàng hoặc rỗng bình thường
 */

export interface SourceBannerDecisionSource {
  status?: string | null;
  failed_count?: number | null;
  publishable_count?: number | null;
  awaiting_publish_count?: number | null;
  needs_build_count?: number | null;
}

export type SourceActionBanner = "failed" | "review" | "updates" | "none";

export function resolveSourceActionBanner(
  source?: SourceBannerDecisionSource | null,
): SourceActionBanner {
  if (!source) return "none";

  const isFailed = source.status === "failed" || (source.failed_count ?? 0) > 0;
  if (isFailed) {
    return "failed";
  }

  const isReviewRequired =
    source.status === "review_required" ||
    (source.publishable_count ?? 0) > 0 ||
    (source.awaiting_publish_count ?? 0) > 0;
  if (isReviewRequired) {
    return "review";
  }

  const hasUpdates =
    source.status === "updates_available" ||
    (source.needs_build_count ?? 0) > 0;
  if (hasUpdates) {
    return "updates";
  }

  return "none";
}

export interface RetryDecisionSource {
  publishable_count?: number | null;
  awaiting_publish_count?: number | null;
  needs_build_count?: number | null;
}

export type RetryAction = "publish" | "sync";

export function resolveRetryAction(source?: RetryDecisionSource | null): RetryAction {
  if (!source) return "sync";

  const hasAwaitingPublish =
    (source.publishable_count ?? 0) > 0 ||
    (source.awaiting_publish_count ?? 0) > 0;

  if (hasAwaitingPublish) {
    return "publish";
  }
  return "sync";
}
