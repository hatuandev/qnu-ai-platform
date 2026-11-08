import type { InboxItem, InboxKind } from "./inbox-types.ts";

export const INBOX_KINDS = [
  "review_pending",
  "changes_requested",
  "awaiting_publish",
  "preparation_failed",
  "sync_incomplete",
] as const satisfies readonly InboxKind[];

export const INBOX_KIND_LABELS: Record<InboxKind, string> = {
  review_pending: "Chờ duyệt",
  changes_requested: "Cần sửa",
  awaiting_publish: "Chờ xuất bản",
  sync_incomplete: "Đồng bộ",
  preparation_failed: "Chuẩn bị lỗi",
};

export function inboxKindVariant(
  kind: InboxKind,
): "info" | "warning" | "default" | "destructive" {
  switch (kind) {
    case "review_pending":
      return "info";
    case "changes_requested":
      return "warning";
    case "awaiting_publish":
      return "default";
    case "preparation_failed":
      return "warning";
    case "sync_incomplete":
      return "destructive";
    default:
      return "default";
  }
}

const ROLE_LABELS: Record<string, string> = {
  admin: "Quản trị đơn vị",
  editor: "Biên tập",
  reviewer: "Người duyệt",
};

/**
 * Never invent an owner: unknown labels stay visible as their raw role and an
 * empty list reads as the neutral server wording.
 */
export function formatAllowedRoles(roles: readonly string[]): string {
  if (roles.length === 0) return "Chờ người duyệt";
  return roles.map((role) => ROLE_LABELS[role] ?? role).join(", ");
}

/**
 * Typed deep link built from server-provided row identifiers. The server also
 * returns `deep_path`, but keeping the typed form avoids a full page reload.
 */
export function inboxTarget(workspaceId: string, item: InboxItem) {
  if (
    item.kind === "preparation_failed" &&
    item.source_id &&
    item.collection_id
  ) {
    return {
      to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId" as const,
      params: {
        workspaceId,
        collectionId: item.collection_id,
        sourceId: item.source_id,
      },
    };
  }
  if (item.document_id && item.version_id && item.collection_id) {
    return {
      to: "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId" as const,
      params: {
        workspaceId,
        collectionId: item.collection_id,
        documentId: item.document_id,
        versionId: item.version_id,
      },
    };
  }
  return {
    to: "/workspaces/$workspaceId/knowledge/$knowledgeId" as const,
    params: {
      workspaceId,
      knowledgeId: item.collection_id,
    },
    search: { page: 1, pageSize: 20, stage: "serving" as const },
  };
}
