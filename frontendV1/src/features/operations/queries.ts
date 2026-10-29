import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  getJob,
  getOperationAction,
  getReadiness,
  getSummary,
  listJobs,
} from "./requests";
import type { JobFilters, JobKind } from "./types";
export function useJobs(
  workspaceId: string,
  filters: JobFilters,
  enabled: boolean,
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "operations-jobs", workspaceId, filters],
    queryFn: ({ signal }) => listJobs(v1Client, workspaceId, filters, signal),
    enabled,
    retry: false,
    refetchInterval: (q) =>
      q.state.data?.items?.some((item) =>
        ["queued", "running", "dispatched"].includes(item.status),
      )
        ? 3000
        : false,
  });
}
export function useJob(
  workspaceId: string,
  kind?: JobKind,
  id?: string,
  enabled = true,
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "operations-job", workspaceId, kind, id],
    queryFn: ({ signal }) =>
      getJob(v1Client, workspaceId, kind as JobKind, id ?? "", signal),
    enabled: enabled && Boolean(kind && id),
    retry: false,
    refetchInterval: (q) =>
      ["queued", "running"].includes(q.state.data?.status ?? "") ? 2500 : false,
  });
}
export function useOperationsSummary(workspaceId: string, enabled: boolean) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "operations-summary", workspaceId],
    queryFn: ({ signal }) => getSummary(v1Client, workspaceId, signal),
    enabled,
    retry: false,
    refetchInterval: (q) =>
      q.state.data?.jobs?.some((item) =>
        ["queued", "running", "dispatched"].includes(item.status),
      )
        ? 4000
        : false,
  });
}
export function useReadiness(workspaceId: string, enabled: boolean) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "operations-readiness", workspaceId],
    queryFn: ({ signal }) => getReadiness(v1Client, workspaceId, signal),
    enabled,
    retry: false,
  });
}
export function useOperationAction(
  workspaceId: string,
  id?: string,
  enabled = true,
) {
  const { sessionId } = useV1Auth();
  const client = useQueryClient();
  const last = useRef("");
  const query = useQuery({
    queryKey: ["v1", sessionId, "operations-action", workspaceId, id],
    queryFn: ({ signal }) =>
      getOperationAction(v1Client, workspaceId, id ?? "", signal),
    enabled: enabled && Boolean(id),
    retry: false,
    refetchInterval: (q) => (q.state.data?.status === "pending" ? 2500 : false),
  });
  useEffect(() => {
    if (
      !query.data ||
      query.data.status === "preview" ||
      query.data.status === "pending" ||
      last.current === query.data.id
    )
      return;
    last.current = query.data.id;
    void client.invalidateQueries({
      queryKey: ["v1", sessionId, "operations-jobs", workspaceId],
    });
    void client.invalidateQueries({
      queryKey: ["v1", sessionId, "operations-summary", workspaceId],
    });
  }, [client, query.data, sessionId, workspaceId]);
  return query;
}
