import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import type { CompiledDocumentStatus } from "./publication-types.ts";
import type {
  SubmissionPreviewAction,
  SubmissionStatus,
} from "./review-types.ts";

const OPEN_STATUSES: readonly SubmissionStatus[] = [
  "pending",
  "changes_requested",
];

const SUBMITTABLE_VERSION_STATUSES: readonly CompiledDocumentStatus[] = [
  "draft",
  "superseded",
  "withdrawn",
];

export function isSubmittableVersionStatus(
  status: CompiledDocumentStatus,
): boolean {
  return SUBMITTABLE_VERSION_STATUSES.includes(status);
}

export function isOpenSubmissionStatus(status: SubmissionStatus): boolean {
  return OPEN_STATUSES.includes(status);
}

export function submissionStatusLabel(status: SubmissionStatus): string {
  switch (status) {
    case "pending":
      return "Chờ người duyệt";
    case "changes_requested":
      return "Đã yêu cầu sửa";
    case "resolved":
      return "Đã xử lý";
    case "cancelled":
      return "Đã rút";
    default:
      return status;
  }
}

export function submissionStatusVariant(
  status: SubmissionStatus,
): "info" | "warning" | "success" | "secondary" {
  switch (status) {
    case "pending":
      return "info";
    case "changes_requested":
      return "warning";
    case "resolved":
      return "success";
    case "cancelled":
      return "secondary";
    default:
      return "secondary";
  }
}

export function submissionActionLabel(action: SubmissionPreviewAction): {
  title: string;
  confirm: string;
} {
  switch (action) {
    case "submit":
      return { title: "Gửi duyệt phiên bản", confirm: "Gửi duyệt" };
    case "request_changes":
      return { title: "Yêu cầu sửa phiên bản", confirm: "Yêu cầu sửa" };
    case "cancel":
      return { title: "Rút yêu cầu duyệt", confirm: "Rút yêu cầu" };
    default:
      return { title: "Xử lý yêu cầu duyệt", confirm: "Xác nhận" };
  }
}

/** Submitting a draft requires the same rights as editing content. */
export function canSubmitForReview(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  return (
    role.kind === "member" && (role.role === "admin" || role.role === "editor")
  );
}

/** Reviewers do not need editor rights to request a fix. */
export function canRequestSubmissionChanges(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  return (
    role.kind === "member" &&
    (role.role === "admin" || role.role === "reviewer")
  );
}

/**
 * The submitter may withdraw their own open request; admins may withdraw any.
 * `submittedBy` is an opaque server value compared verbatim.
 */
export function canCancelSubmission(args: {
  role: CallerWorkspaceRole | null | undefined;
  actorRef: string | null | undefined;
  submittedBy: string | null | undefined;
}): boolean {
  const { role, actorRef, submittedBy } = args;
  if (!role || !submittedBy) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind !== "member") return false;
  if (role.role === "admin") return true;
  return Boolean(actorRef) && actorRef === submittedBy;
}

export function formatReviewSubmissionError(
  code: string | undefined,
  fallbackMessage = "",
): string {
  switch (code) {
    case "review_submission_duplicate":
      return "Phiên bản này đã được gửi duyệt và đang chờ xử lý.";
    case "review_submission_version_invalid":
      return "Chỉ gửi duyệt được phiên bản chưa được duyệt hoặc đã thu hồi.";
    case "review_submission_changes_required":
      return "Phiên bản đã bị yêu cầu sửa; hãy chuẩn bị phiên bản mới trước khi gửi duyệt.";
    case "review_submission_not_pending":
      return "Yêu cầu duyệt đã được xử lý hoặc rút bởi người khác.";
    case "review_submission_stale":
      return "Phiên bản đã thay đổi so với yêu cầu duyệt. Vui lòng kiểm tra lại.";
    case "review_submission_forbidden":
      return "Chỉ người gửi hoặc quản trị đơn vị được rút yêu cầu duyệt.";
    case "review_submission_not_found":
      return "Không tìm thấy yêu cầu duyệt.";
    case "review_preview_consumed":
      return "Bản xem trước này đã được sử dụng. Vui lòng xem trước lại.";
    case "review_preview_expired":
      return "Bản xem trước đã hết hạn. Vui lòng xem trước lại.";
    case "review_preview_mismatch":
      return "Bản xem trước không khớp nội dung đã xem.";
    case "review_preview_stale":
      return "Tài liệu hoặc yêu cầu duyệt đã thay đổi. Vui lòng xem trước lại.";
    case "review_preview_not_found":
      return "Không tìm thấy bản xem trước cho thao tác này.";
    case "idempotency_conflict":
      return "Khóa Idempotency-Key đã được sử dụng cho một yêu cầu khác.";
    default:
      return (
        fallbackMessage || "Không thể xử lý yêu cầu duyệt. Vui lòng thử lại."
      );
  }
}
