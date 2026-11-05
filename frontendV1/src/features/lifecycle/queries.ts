import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import { getLifecycleAction, listArchivedResources } from "./requests";
import type { LifecycleAction } from "./types";

export function useLifecycleAction(workspaceId: string, id?: string) {
  const { sessionId } = useV1Auth();
  const queryClient = useQueryClient();
  const completed = useRef("");
  const queryKey = ["v1", sessionId, "lifecycle-action", workspaceId, id];
  const query = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const received = await getLifecycleAction(
        v1Client,
        workspaceId,
        id ?? "",
        signal,
      );
      const cached = queryClient.getQueryData<LifecycleAction>(queryKey);
      // An accepted receipt cannot become an unconfirmed preview again.
      // Read the cache after I/O: acceptance may finish while this GET is in flight.
      if (
        received.status === "preview" &&
        cached &&
        cached.status !== "preview"
      )
        return cached;
      return received;
    },
    enabled: Boolean(id && workspaceId),
    retry: false,
    refetchInterval: (q) => (q.state.data?.status === "pending" ? 2500 : false),
  });
  useEffect(() => {
    if (
      query.data?.status !== "completed" ||
      completed.current === query.data.id
    )
      return;
    completed.current = query.data.id;
    void queryClient.invalidateQueries({
      predicate: (q) =>
        q.queryKey[0] === "v1" &&
        q.queryKey[1] === sessionId &&
        q.queryKey[2] !== "lifecycle-action",
    });
  }, [query.data, queryClient, sessionId]);
  return query;
}
export function useArchivedResources(
  workspaceId: string,
  page: number,
  enabled: boolean,
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "lifecycle-resources", workspaceId, page],
    queryFn: ({ signal }) =>
      listArchivedResources(v1Client, workspaceId, page, signal),
    enabled,
    retry: false,
  });
}
