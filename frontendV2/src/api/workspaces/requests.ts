/**
 * HTTP request functions for QNU AI Workspace domain.
 * Maps 1:1 to routes in `backendV1/qnu/domains/workspaces`.
 */

import { v1Client } from "../v1-client";
import { workspacePaths } from "./endpoints";
import type {
  MemberCreateInput,
  MemberUpdateInput,
  Page,
  PageParams,
  QuotaResponse,
  UsageResponse,
  Workspace,
  WorkspaceCreateInput,
  WorkspaceEvent,
  WorkspaceMember,
  WorkspaceResolveRouteResponse,
  WorkspaceUpdateInput,
} from "./types";

export async function listWorkspaces(
  params?: Partial<PageParams>,
  options?: { signal?: AbortSignal },
): Promise<Page<Workspace>> {
  return v1Client.get<Page<Workspace>>(workspacePaths.list, {
    searchParams: {
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 50,
    },
    signal: options?.signal,
  });
}

export async function resolveWorkspaceRoute(
  code: string,
  options?: { signal?: AbortSignal },
): Promise<WorkspaceResolveRouteResponse> {
  return v1Client.get<WorkspaceResolveRouteResponse>(
    workspacePaths.resolveRoute(code),
    options,
  );
}

export async function getWorkspace(
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<Workspace> {
  return v1Client.get<Workspace>(workspacePaths.detail(workspaceId), options);
}

export async function createWorkspace(
  input: WorkspaceCreateInput,
): Promise<Workspace> {
  return v1Client.post<Workspace>(workspacePaths.list, input);
}

export async function updateWorkspace(
  workspaceId: string,
  patch: WorkspaceUpdateInput,
): Promise<Workspace> {
  return v1Client.patch<Workspace>(workspacePaths.detail(workspaceId), patch);
}

export async function listMembers(
  workspaceId: string,
  params?: Partial<PageParams>,
  options?: { signal?: AbortSignal },
): Promise<Page<WorkspaceMember>> {
  return v1Client.get<Page<WorkspaceMember>>(
    workspacePaths.members(workspaceId),
    {
      searchParams: {
        page: params?.page ?? 1,
        page_size: params?.pageSize ?? 50,
      },
      signal: options?.signal,
    },
  );
}

export async function addMember(
  workspaceId: string,
  input: MemberCreateInput,
): Promise<WorkspaceMember> {
  return v1Client.post<WorkspaceMember>(
    workspacePaths.members(workspaceId),
    input,
  );
}

export async function updateMember(
  workspaceId: string,
  memberId: string,
  patch: MemberUpdateInput,
): Promise<WorkspaceMember> {
  return v1Client.patch<WorkspaceMember>(
    workspacePaths.member(workspaceId, memberId),
    patch,
  );
}

export async function revokeMember(
  workspaceId: string,
  memberId: string,
): Promise<WorkspaceMember> {
  return v1Client.delete<WorkspaceMember>(
    workspacePaths.member(workspaceId, memberId),
  );
}

export async function listWorkspaceEvents(
  workspaceId: string,
  params?: Partial<PageParams>,
  options?: { signal?: AbortSignal },
): Promise<Page<WorkspaceEvent>> {
  return v1Client.get<Page<WorkspaceEvent>>(
    workspacePaths.events(workspaceId),
    {
      searchParams: {
        page: params?.page ?? 1,
        page_size: params?.pageSize ?? 50,
      },
      signal: options?.signal,
    },
  );
}

export async function getWorkspaceQuota(
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<QuotaResponse> {
  return v1Client.get<QuotaResponse>(
    workspacePaths.quota(workspaceId),
    options,
  );
}

export async function listWorkspaceUsage(
  workspaceId: string,
  params?: Partial<PageParams>,
  options?: { signal?: AbortSignal },
): Promise<Page<UsageResponse>> {
  return v1Client.get<Page<UsageResponse>>(workspacePaths.usage(workspaceId), {
    searchParams: {
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 20,
    },
    signal: options?.signal,
  });
}
