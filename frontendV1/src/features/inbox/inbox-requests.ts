import type { V1Client } from "../../app/api/v1/client.ts";
import { inboxPaths } from "../../app/api/v1/endpoints.ts";
import type { InboxFilters, InboxPage } from "./inbox-types.ts";

export function listInbox(
  client: V1Client,
  workspaceId: string,
  filters: InboxFilters,
  options?: { signal?: AbortSignal },
): Promise<InboxPage> {
  return client.get<InboxPage>(inboxPaths.inbox(workspaceId), {
    searchParams: {
      kind: filters.kind,
      collection_id: filters.collectionId,
      page: filters.page,
      page_size: filters.pageSize,
    },
    signal: options?.signal,
  });
}
