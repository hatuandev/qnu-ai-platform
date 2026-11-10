/**
 * TanStack Query hooks for Inbox domain.
 */

import { useQuery } from "@tanstack/react-query";
import { readInbox } from "./requests";
import type { InboxListParams } from "./types";

export const inboxKeys = {
  all: ["v1", "inbox"] as const,

  list: (workspaceId: string, params?: InboxListParams) =>
    [
      ...inboxKeys.all,
      "list",
      workspaceId,
      params?.collectionId ?? "all",
      params?.kind ?? "all",
      params?.page ?? 1,
      params?.pageSize ?? 20,
    ] as const,
};

export function useInboxQuery(
  workspaceId?: string | null,
  params?: InboxListParams,
  options?: { refetchInterval?: number | false },
) {
  return useQuery({
    queryKey: workspaceId
      ? inboxKeys.list(workspaceId, params)
      : [...inboxKeys.all, "list", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return readInbox(workspaceId, params, { signal });
    },
    enabled: Boolean(workspaceId),
    refetchInterval: options?.refetchInterval ?? 10000,
  });
}
