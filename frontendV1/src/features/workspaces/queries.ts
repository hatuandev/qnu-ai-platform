import {
  type QueryClient,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { useMemo } from "react";
import { v1Client } from "@/app/api/v1";
import { useV1Auth } from "@/app/auth/v1";
import {
  type CallerWorkspaceRole,
  isPlatformWorkspaceAdmin,
  resolveCallerWorkspaceRole,
} from "@/app/auth/v1/permissions";
import {
  addMember,
  createWorkspace,
  getAllowlist,
  getQuota,
  getWorkspace,
  listMembers,
  listUsage,
  listWorkspaceEvents,
  listWorkspaces,
  loadMembersForRole,
  putAllowlist,
  putQuota,
  putWorkspaceDefaults,
  revokeMember,
  updateMember,
  updateWorkspace,
} from "@/features/workspaces/requests";
import type {
  AllowlistUpdateInput,
  Capability,
  MemberCreateInput,
  MemberUpdateInput,
  PageParams,
  QuotaUpdateInput,
  WorkspaceCreateInput,
  WorkspaceDefaultsInput,
  WorkspaceUpdateInput,
} from "@/features/workspaces/types";

const ROOT = ["v1", "workspaces"] as const;

export const workspaceKeys = {
  all: (sessionId?: number) =>
    sessionId !== undefined ? (["v1", sessionId, "workspaces"] as const) : ROOT,
  lists: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "workspaces", "list"] as const)
      : ([...ROOT, "list"] as const),
  list: (params: PageParams, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          "list",
          params.page,
          params.pageSize,
        ] as const)
      : ([...ROOT, "list", params.page, params.pageSize] as const),
  details: (sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "workspaces", "detail"] as const)
      : ([...ROOT, "detail"] as const),
  detail: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "workspaces", "detail", workspaceId] as const)
      : ([...ROOT, "detail", workspaceId] as const),
  members: (workspaceId: string, params: PageParams, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          "members",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const)
      : ([
          ...ROOT,
          "members",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const),
  callerRole: (workspaceId: string, actorRef: string, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          "caller-role",
          workspaceId,
          actorRef,
        ] as const)
      : ([...ROOT, "caller-role", workspaceId, actorRef] as const),
  events: (workspaceId: string, params: PageParams, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          "events",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const)
      : ([
          ...ROOT,
          "events",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const),
  allowlist: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "workspaces", "allowlist", workspaceId] as const)
      : ([...ROOT, "allowlist", workspaceId] as const),
  quota: (workspaceId: string, sessionId?: number) =>
    sessionId !== undefined
      ? (["v1", sessionId, "workspaces", "quota", workspaceId] as const)
      : ([...ROOT, "quota", workspaceId] as const),
  usage: (workspaceId: string, params: PageParams, sessionId?: number) =>
    sessionId !== undefined
      ? ([
          "v1",
          sessionId,
          "workspaces",
          "usage",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const)
      : ([
          ...ROOT,
          "usage",
          workspaceId,
          params.page,
          params.pageSize,
        ] as const),
};

function invalidateWorkspaceScopes(
  queryClient: QueryClient,
  workspaceId: string,
  sessionId?: number,
) {
  void queryClient.invalidateQueries({
    queryKey: workspaceKeys.lists(sessionId),
  });
  void queryClient.invalidateQueries({
    queryKey: workspaceKeys.detail(workspaceId, sessionId),
  });
  if (sessionId !== undefined) {
    void queryClient.invalidateQueries({
      queryKey: ["v1", sessionId, "workspaces", "members", workspaceId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
    });
    void queryClient.invalidateQueries({
      queryKey: ["v1", sessionId, "workspaces", "caller-role", workspaceId],
    });
  }
  void queryClient.invalidateQueries({
    queryKey: [...ROOT, "members", workspaceId],
  });
  void queryClient.invalidateQueries({
    queryKey: [...ROOT, "events", workspaceId],
  });
  void queryClient.invalidateQueries({
    queryKey: [...ROOT, "caller-role", workspaceId],
  });
}

export function useWorkspacesQuery(params: PageParams) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.list(params, sessionId),
    queryFn: ({ signal }) => listWorkspaces(v1Client, params, { signal }),
    placeholderData: (previous) => previous,
  });
}

export function useWorkspaceQuery(workspaceId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.detail(workspaceId, sessionId),
    queryFn: ({ signal }) => getWorkspace(v1Client, workspaceId, { signal }),
    enabled: Boolean(workspaceId),
  });
}

export function useMembersQuery(workspaceId: string, params: PageParams) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.members(workspaceId, params, sessionId),
    queryFn: ({ signal }) =>
      listMembers(v1Client, workspaceId, params, { signal }),
    enabled: Boolean(workspaceId),
  });
}

export function useWorkspaceEventsQuery(
  workspaceId: string,
  params: PageParams,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.events(workspaceId, params, sessionId),
    queryFn: ({ signal }) =>
      listWorkspaceEvents(v1Client, workspaceId, params, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}

export function useAllowlistQuery(workspaceId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.allowlist(workspaceId, sessionId),
    queryFn: ({ signal }) => getAllowlist(v1Client, workspaceId, { signal }),
    enabled: Boolean(workspaceId),
  });
}

export function useQuotaQuery(workspaceId: string) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.quota(workspaceId, sessionId),
    queryFn: ({ signal }) =>
      getQuota(v1Client, workspaceId, undefined, { signal }),
    enabled: Boolean(workspaceId),
  });
}

export function useUsageQuery(
  workspaceId: string,
  params: PageParams,
  options?: { enabled?: boolean },
) {
  const { sessionId } = useV1Auth();
  return useQuery({
    queryKey: workspaceKeys.usage(workspaceId, params, sessionId),
    queryFn: ({ signal }) =>
      listUsage(v1Client, workspaceId, params, { signal }),
    enabled: Boolean(workspaceId) && (options?.enabled ?? true),
  });
}

/**
 * The caller's role inside one workspace, taken from server membership rows.
 *
 * Platform administrators never need the extra read. Everyone else walks the
 * membership pages until their own `actor_ref` appears, so a first page without
 * the caller is never mistaken for "no permission".
 */
export function useCallerWorkspaceRole(workspaceId: string): {
  role: CallerWorkspaceRole;
  isPending: boolean;
  error: Error | null;
} {
  const { actor, sessionId } = useV1Auth();
  const actorRef = actor?.actor_id ?? "";
  const platformAdmin = isPlatformWorkspaceAdmin(actor);

  const query = useQuery({
    queryKey: workspaceKeys.callerRole(workspaceId, actorRef, sessionId),
    queryFn: ({ signal }) =>
      loadMembersForRole(v1Client, workspaceId, actorRef, { signal }),
    enabled: Boolean(workspaceId) && Boolean(actorRef) && !platformAdmin,
    staleTime: 30_000,
  });

  return useMemo(() => {
    if (platformAdmin) {
      return {
        role: { kind: "platform-admin" } as CallerWorkspaceRole,
        isPending: false,
        error: null,
      };
    }
    if (query.isError) {
      return {
        role: { kind: "unknown" } as CallerWorkspaceRole,
        isPending: false,
        error: query.error instanceof Error ? query.error : null,
      };
    }
    if (!query.data) {
      return {
        role: { kind: "unknown" } as CallerWorkspaceRole,
        isPending: query.isLoading,
        error: null,
      };
    }
    return {
      role: resolveCallerWorkspaceRole({
        actor,
        members: query.data.members,
        total: query.data.total,
        platformAdmin: false,
      }),
      isPending: false,
      error: null,
    };
  }, [
    actor,
    platformAdmin,
    query.data,
    query.error,
    query.isError,
    query.isLoading,
  ]);
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: WorkspaceCreateInput) =>
      createWorkspace(v1Client, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.lists(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.lists(),
      });
    },
  });
}

export function useUpdateWorkspace(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (patch: WorkspaceUpdateInput) =>
      updateWorkspace(v1Client, workspaceId, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.lists(sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.lists(),
      });
      invalidateWorkspaceScopes(queryClient, workspaceId, sessionId);
    },
  });
}

export function useAddMember(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: MemberCreateInput) =>
      addMember(v1Client, workspaceId, input),
    onSuccess: () => {
      invalidateWorkspaceScopes(queryClient, workspaceId, sessionId);
    },
  });
}

export function useUpdateMember(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (args: { memberId: string; patch: MemberUpdateInput }) =>
      updateMember(v1Client, workspaceId, args.memberId, args.patch),
    onSuccess: () => {
      invalidateWorkspaceScopes(queryClient, workspaceId, sessionId);
    },
  });
}

export function useRevokeMember(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (memberId: string) =>
      revokeMember(v1Client, workspaceId, memberId),
    onSuccess: () => {
      invalidateWorkspaceScopes(queryClient, workspaceId, sessionId);
    },
  });
}

export function usePutAllowlist(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: AllowlistUpdateInput) =>
      putAllowlist(v1Client, workspaceId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowlist(workspaceId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowlist(workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
      });
      void queryClient.invalidateQueries({
        queryKey: [...ROOT, "events", workspaceId],
      });
      // The catalog drives default pickers elsewhere in the app.
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "modelops"],
      });
      void queryClient.invalidateQueries({ queryKey: ["v1", "modelops"] });
    },
  });
}

export function usePutWorkspaceDefaults(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (defaults: Partial<Record<Capability, string>>) =>
      putWorkspaceDefaults(v1Client, workspaceId, {
        defaults,
      } satisfies WorkspaceDefaultsInput),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowlist(workspaceId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.allowlist(workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
      });
      void queryClient.invalidateQueries({
        queryKey: [...ROOT, "events", workspaceId],
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "modelops"],
      });
      void queryClient.invalidateQueries({ queryKey: ["v1", "modelops"] });
    },
  });
}

export function usePutQuota(workspaceId: string) {
  const queryClient = useQueryClient();
  const { sessionId } = useV1Auth();
  return useMutation({
    mutationFn: (input: QuotaUpdateInput) =>
      putQuota(v1Client, workspaceId, input),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.quota(workspaceId, sessionId),
      });
      void queryClient.invalidateQueries({
        queryKey: workspaceKeys.quota(workspaceId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["v1", sessionId, "workspaces", "events", workspaceId],
      });
      void queryClient.invalidateQueries({
        queryKey: [...ROOT, "events", workspaceId],
      });
    },
  });
}
