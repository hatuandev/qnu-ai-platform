import type { KnowledgeSourceRevisionResponse } from "@/types/knowledge";

interface RevisionActions {
  updateSourceRevisionContent: (
    collection: string,
    source: string,
    revision: string,
    markdown: string,
    review?: { change_reason: string; expected_canonical_hash?: string },
  ) => Promise<KnowledgeSourceRevisionResponse>;
  reviewSourceRevision: (
    collection: string,
    source: string,
    revision: string,
    decision: "approved",
    comment: string,
  ) => Promise<KnowledgeSourceRevisionResponse>;
}

export async function saveStudioRevision(
  api: RevisionActions,
  collection: string,
  source: string,
  revision: {
    id: string;
    status?: string;
    requires_structured_review?: boolean;
  },
  markdown: string | undefined,
  approve: boolean,
  review?: { reason: string; expectedHash?: string | null },
): Promise<string> {
  let target = revision;
  if (markdown !== undefined)
    target = await api.updateSourceRevisionContent(
      collection,
      source,
      target.id,
      markdown,
      review
        ? {
            change_reason: review.reason,
            expected_canonical_hash: review.expectedHash ?? undefined,
          }
        : undefined,
    );
  if (approve) {
    if (
      target.status !== "review_required" &&
      !target.requires_structured_review
    )
      throw new Error("Chỉ duyệt bản đang chờ kiểm duyệt.");
    target = await api.reviewSourceRevision(
      collection,
      source,
      target.id,
      "approved",
      review?.reason || "Phê duyệt qua Studio",
    );
  }
  return target.id;
}
