import { useQuery } from "@tanstack/react-query";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  getBackup,
  getCleanup,
  getRetention,
  listBackups,
} from "./maintenance-requests";

export function useBackups(workspaceId: string, page: number, pageSize = 20) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "backups", workspaceId, page, pageSize],
    queryFn: ({ signal }) =>
      listBackups(v1Client, workspaceId, page, signal, pageSize),
    retry: false,
    refetchInterval: 5000,
  });
}
export function useBackup(workspaceId: string, id?: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "backup", workspaceId, id],
    queryFn: ({ signal }) => getBackup(v1Client, workspaceId, id ?? "", signal),
    enabled: Boolean(id),
    retry: false,
    refetchInterval: (q) =>
      ["queued", "running", "deleting"].includes(q.state.data?.status ?? "")
        ? 2500
        : false,
  });
}
export function useRetention(workspaceId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "retention", workspaceId],
    queryFn: ({ signal }) => getRetention(v1Client, workspaceId, signal),
    retry: false,
  });
}
export function useCleanup(workspaceId: string, id?: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: ["v1", sessionId, "storage-cleanup", workspaceId, id],
    queryFn: ({ signal }) =>
      getCleanup(v1Client, workspaceId, id ?? "", signal),
    enabled: Boolean(id),
    retry: false,
    refetchInterval: (q) => (q.state.data?.status === "pending" ? 2500 : false),
  });
}
