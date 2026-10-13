import type { KnowledgeSourceRevisionResponse } from "@/types/knowledge";

interface RevisionActions {
  updateSourceRevisionContent: (
    collection: string,
    source: string,
    revision: string,
    markdown: string,
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
): Promise<string> {
  let target = revision;
  if (markdown !== undefined)
    target = await api.updateSourceRevisionContent(
      collection,
      source,
      target.id,
      markdown,
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
      "Phê duyệt qua Studio",
    );
  }
  return target.id;
}
