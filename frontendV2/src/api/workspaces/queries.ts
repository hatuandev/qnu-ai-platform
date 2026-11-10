/**
 * TanStack Query hooks for QNU AI Workspace domain.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addMember,
  createWorkspace,
  getAllowedProviders,
  getWorkspace,
  getWorkspaceQuota,
  listMembers,
  listWorkspaceEvents,
  listWorkspaces,
  listWorkspaceUsage,
  resolveWorkspaceRoute,
  revokeMember,
  setAllowedProviders,
  setWorkspaceDefaults,
  updateMember,
  updateWorkspace,
} from "./requests";
import type {
  AllowlistUpdateInput,
  MemberCreateInput,
  MemberUpdateInput,
  PageParams,
  WorkspaceCreateInput,
  WorkspaceUpdateInput,
} from "./types";

const ROOT = ["v1", "workspaces"] as const;

export const workspaceKeys = {
  all: ROOT,
  lists: () => [...ROOT, "list"] as const,
  list: (params: PageParams) =>
    [...ROOT, "list", params.page, params.pageSize] as const,
  details: () => [...ROOT, "detail"] as const,
  detail: (workspaceId: string) => [...ROOT, "detail", workspaceId] as const,
  resolveRoute: (code: string) => [...ROOT, "resolveRoute", code] as const,
  members: (workspaceId: string, params: PageParams) =>
    [...ROOT, "members", workspaceId, params.page, params.pageSize] as const,
  events: (workspaceId: string, params: PageParams) =>
    [...ROOT, "events", workspaceId, params.page, params.pageSize] as const,
  quota: (workspaceId: string) => [...ROOT, "quota", workspaceId] as const,
  usage: (workspaceId: string, params: PageParams) =>
    [...ROOT, "usage", workspaceId, params.page, params.pageSize] as const,
  allowedProviders: (workspaceId: string) =>
    [...ROOT, "allowedProviders", workspaceId] as const,
};

export function useWorkspacesQuery(params?: Partial<PageParams>) {
  const pageParams: PageParams = {
    page: params?.page ?? 1,
    pageSize: params?.pageSize ?? 50,
  };

  return useQuery({
    queryKey: workspaceKeys.list(pageParams),
    queryFn: ({ signal }) => listWorkspaces(pageParams, { signal }),
  });
}

export function useResolveWorkspaceRouteQuery(code?: string | null) {
  return useQuery({
    queryKey: code
      ? workspaceKeys.resolveRoute(code)
      : [...ROOT, "resolveRoute", "empty"],
    queryFn: ({ signal }) => {
      if (!code) throw new Error("code is required");
      return resolveWorkspaceRoute(code, { signal });
    },
    enabled: Boolean(code),
    retry: 1,
  });
}

export function useWorkspaceDetailQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.detail(workspaceId)
      : [...ROOT, "detail", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return getWorkspace(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useCreateWorkspaceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: WorkspaceCreateInput) => createWorkspace(input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workspaceKeys.lists() });
    },
  });
}

export function useUpdateWorkspaceMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      workspaceId,
      patch,
    }: {
      workspaceId: string;
      patch: WorkspaceUpdateInput;
    }) => updateWorkspace(workspaceId, patch),
    onSuccess: (_, { workspaceId }) => {
      queryClient.invalidateQueries({ queryKey: workspaceKeys.lists() });
      queryClient.invalidateQueries({
        queryKey: workspaceKeys.detail(workspaceId),
      });
    },
  });
}

export function useWorkspaceMembersQuery(
  workspaceId?: string | null,
  params?: Partial<PageParams>,
) {
  const pageParams: PageParams = {
    page: params?.page ?? 1,
    pageSize: params?.pageSize ?? 50,
  };

  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.members(workspaceId, pageParams)
      : [...ROOT, "members", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listMembers(workspaceId, pageParams, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useAddMemberMutation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: MemberCreateInput) => addMember(workspaceId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...ROOT, "members", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: workspaceKeys.detail(workspaceId),
      });
    },
  });
}

export function useUpdateMemberMutation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      memberId,
      patch,
    }: {
      memberId: string;
      patch: MemberUpdateInput;
    }) => updateMember(workspaceId, memberId, patch),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...ROOT, "members", workspaceId],
      });
    },
  });
}

export function useRevokeMemberMutation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (memberId: string) => revokeMember(workspaceId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [...ROOT, "members", workspaceId],
      });
      queryClient.invalidateQueries({
        queryKey: workspaceKeys.detail(workspaceId),
      });
    },
  });
}

export function useWorkspaceEventsQuery(
  workspaceId?: string | null,
  params?: Partial<PageParams>,
) {
  const pageParams: PageParams = {
    page: params?.page ?? 1,
    pageSize: params?.pageSize ?? 50,
  };

  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.events(workspaceId, pageParams)
      : [...ROOT, "events", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listWorkspaceEvents(workspaceId, pageParams, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useWorkspaceQuotaQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.quota(workspaceId)
      : [...ROOT, "quota", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return getWorkspaceQuota(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useWorkspaceUsageQuery(
  workspaceId?: string | null,
  params?: Partial<PageParams>,
) {
  const pageParams: PageParams = {
    page: params?.page ?? 1,
    pageSize: params?.pageSize ?? 20,
  };

  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.usage(workspaceId, pageParams)
      : [...ROOT, "usage", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return listWorkspaceUsage(workspaceId, pageParams, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useAllowedProvidersQuery(workspaceId?: string | null) {
  return useQuery({
    queryKey: workspaceId
      ? workspaceKeys.allowedProviders(workspaceId)
      : [...ROOT, "allowedProviders", "empty"],
    queryFn: ({ signal }) => {
      if (!workspaceId) throw new Error("workspaceId is required");
      return getAllowedProviders(workspaceId, { signal });
    },
    enabled: Boolean(workspaceId),
  });
}

export function useSetAllowedProvidersMutation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: AllowlistUpdateInput) =>
      setAllowedProviders(workspaceId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowedProviders(workspaceId),
      });
    },
  });
}

export function useSetWorkspaceDefaultsMutation(workspaceId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (defaults: Record<string, string>) =>
      setWorkspaceDefaults(workspaceId, defaults),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowedProviders(workspaceId),
      });
    },
  });
}
