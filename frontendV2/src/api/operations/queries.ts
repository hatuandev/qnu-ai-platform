import { useQuery } from "@tanstack/react-query";
import {
  getOperationsSummary,
  listOperationsJobs,
  listWorkspaceBackups,
} from "./requests";

export const operationsKeys = {
  all: ["v1", "operations"] as const,
  jobs: (workspaceId: string, params?: Record<string, unknown>) =>
    [...operationsKeys.all, "jobs", workspaceId, params ?? {}] as const,
  summary: (workspaceId: string) =>
    [...operationsKeys.all, "summary", workspaceId] as const,
  backups: (workspaceId: string, params?: Record<string, unknown>) =>
    [...operationsKeys.all, "backups", workspaceId, params ?? {}] as const,
};

export function useOperationsJobsQuery(
  workspaceId?: string | null,
  params?: {
    kind?: string;
    status?: string;
    collection_id?: string;
    limit?: number;
    offset?: number;
  },
) {
  return useQuery({
    queryKey: workspaceId
      ? operationsKeys.jobs(workspaceId, params)
      : [...operationsKeys.all, "jobs", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) {
        return Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 });
      }
      return listOperationsJobs(workspaceId, params, { signal });
    },
    enabled: Boolean(workspaceId),
    refetchInterval: (query) => {
      // Poll every 3s if any job is currently queued or running
      const hasActive = query.state.data?.items?.some((j) =>
        ["queued", "running", "syncing"].includes(j.status),
      );
      return hasActive ? 3000 : false;
    },
  });
}

export function useOperationsSummaryQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? operationsKeys.summary(workspaceId)
      : [...operationsKeys.all, "summary", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) return Promise.resolve({});
      return getOperationsSummary(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useWorkspaceBackupsQuery(
  workspaceId?: string | null,
  params?: { limit?: number; offset?: number },
) {
  return useQuery({
    queryKey: workspaceId
      ? operationsKeys.backups(workspaceId, params)
      : [...operationsKeys.all, "backups", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) {
        return Promise.resolve({ items: [], total: 0, limit: 20, offset: 0 });
      }
      return listWorkspaceBackups(workspaceId, params, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}
