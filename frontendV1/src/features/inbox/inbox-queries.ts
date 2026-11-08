import { useQuery } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { listInbox } from "./inbox-requests";
import type { InboxFilters, InboxPage } from "./inbox-types";

export const inboxKeys = {
  all: (workspaceId: string, sessionId?: number) =>
    ["v1", sessionId, "workspaces", workspaceId, "inbox"] as const,
  page: (workspaceId: string, filters: InboxFilters, sessionId?: number) =>
    [
      ...inboxKeys.all(workspaceId, sessionId),
      {
        kind: filters.kind ?? null,
        collectionId: filters.collectionId ?? null,
        page: filters.page,
        pageSize: filters.pageSize,
      },
    ] as const,
};

export function useInboxQuery(workspaceId: string, filters: InboxFilters) {
  const { sessionId } = useV1Auth();
  return useQuery<InboxPage>({
    queryKey: inboxKeys.page(workspaceId, filters, sessionId),
    queryFn: ({ signal }) =>
      listInbox(v1Client, workspaceId, filters, { signal }),
    enabled: Boolean(workspaceId),
    placeholderData: (previous) => previous,
    staleTime: 15_000,
  });
}
