/**
 * HTTP request functions for Inbox domain.
 */

import { v1Client } from "../v1-client";
import { inboxPaths } from "./endpoints";
import type { InboxListParams, InboxPage } from "./types";

export async function readInbox(
  workspaceId: string,
  params?: InboxListParams,
  options?: { signal?: AbortSignal },
): Promise<InboxPage> {
  const searchParams: Record<string, string | number> = {};

  if (params?.collectionId) {
    searchParams.collection_id = params.collectionId;
  }
  if (params?.kind) {
    searchParams.kind = params.kind;
  }
  if (params?.page) {
    searchParams.page = params.page;
  }
  if (params?.pageSize) {
    searchParams.page_size = params.pageSize;
  }

  return v1Client.get<InboxPage>(inboxPaths.list(workspaceId), {
    searchParams,
    signal: options?.signal,
  });
}
