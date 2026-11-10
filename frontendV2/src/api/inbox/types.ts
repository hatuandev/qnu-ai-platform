/**
 * TypeScript types for Inbox domain.
 * Mirrors `backendV1/qnu/domains/knowledge/inbox/schemas.py`.
 */

export type InboxKind =
  | "review_pending"
  | "changes_requested"
  | "awaiting_publish"
  | "sync_incomplete"
  | "preparation_failed";

export type InboxItem = {
  id: string;
  kind: InboxKind;
  title: string;
  problem: string;
  detail: string;
  occurred_at: string;
  collection_id: string;
  collection_name: string;
  document_id: string | null;
  version_id: string | null;
  submission_id: string | null;
  source_id: string | null;
  allowed_roles: string[];
  deep_path: string;
};

export type InboxPageMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type InboxPage = {
  items: InboxItem[];
  meta: InboxPageMeta;
  counts: Record<string, number>;
};

export type InboxListParams = {
  collectionId?: string;
  kind?: InboxKind;
  page?: number;
  pageSize?: number;
};
