import type { PageMeta } from "@/features/workspaces/types";

/**
 * Mirrors `backendV1/qnu/domains/knowledge/inbox/schemas.py`. A row exists only
 * while its underlying resource is still unresolved; there is no dismissal.
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
  /** Roles the server says may act; an empty list is never filled with a name. */
  allowed_roles: string[];
  deep_path: string;
};

export type InboxPage = {
  items: InboxItem[];
  meta: PageMeta;
  counts: Partial<Record<InboxKind, number>>;
};

export type InboxFilters = {
  kind?: InboxKind;
  collectionId?: string;
  page: number;
  pageSize: number;
};
