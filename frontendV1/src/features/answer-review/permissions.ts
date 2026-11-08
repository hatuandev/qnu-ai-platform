import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";

/**
 * Mirrors `LABEL_ROLES` in `backendV1/qnu/domains/answer_review/service.py`.
 * Any workspace member may run a test; only admin/editor/reviewer may attach
 * a human label to an answer.
 */
export function canLabelAnswerReviews(role: CallerWorkspaceRole): boolean {
  if (role.kind === "platform-admin") {
    return true;
  }
  if (role.kind === "member") {
    return (
      role.role === "admin" ||
      role.role === "editor" ||
      role.role === "reviewer"
    );
  }
  return false;
}
