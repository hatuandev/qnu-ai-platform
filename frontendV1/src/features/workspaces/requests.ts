/**
 * HTTP contract for workspace screens.
 *
 * Every function here maps 1:1 to a route in `backendV1/qnu/domains/workspaces`
 * and `qnu/domains/modelops` (allowlist/quota/usage). They are plain async
 * functions so the contract can be exercised without a DOM; the React hooks in
 * `queries.ts` only add caching and invalidation.
 */

import type { V1Client } from "../../app/api/v1/client.ts";
import { workspacePaths } from "../../app/api/v1/endpoints.ts";
import type {
  AllowlistResponse,
  AllowlistUpdateInput,
  Capability,
  MemberCreateInput,
  MemberUpdateInput,
  Page,
  PageParams,
  Quota,
  UsageRecord,
  Workspace,
  WorkspaceCreateInput,
  WorkspaceDefaultsInput,
  WorkspaceEvent,
  WorkspaceMember,
  WorkspaceUpdateInput,
} from "./types.ts";

/** Backend caps `page_size` at 200; the role lookup walks pages of this size. */
export const MEMBER_PAGE_SIZE = 200;
const MAX_MEMBER_PAGES = 10;

export function listWorkspaces(
  client: V1Client,
  params: PageParams,
  options?: { signal?: AbortSignal },
): Promise<Page<Workspace>> {
  return client.get<Page<Workspace>>(workspacePaths.list, {
    searchParams: { page: params.page, page_size: params.pageSize },
    signal: options?.signal,
  });
}

export function getWorkspace(
  client: V1Client,
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<Workspace> {
  return client.get<Workspace>(workspacePaths.detail(workspaceId), options);
}

export function createWorkspace(
  client: V1Client,
  input: WorkspaceCreateInput,
): Promise<Workspace> {
  return client.post<Workspace>(workspacePaths.list, input);
}

export function updateWorkspace(
  client: V1Client,
  workspaceId: string,
  patch: WorkspaceUpdateInput,
): Promise<Workspace> {
  return client.patch<Workspace>(workspacePaths.detail(workspaceId), patch);
}

export function listMembers(
  client: V1Client,
  workspaceId: string,
  params: PageParams,
  options?: { signal?: AbortSignal },
): Promise<Page<WorkspaceMember>> {
  return client.get<Page<WorkspaceMember>>(
    workspacePaths.members(workspaceId),
    {
      searchParams: { page: params.page, page_size: params.pageSize },
      signal: options?.signal,
    },
  );
}

export function addMember(
  client: V1Client,
  workspaceId: string,
  input: MemberCreateInput,
): Promise<WorkspaceMember> {
  return client.post<WorkspaceMember>(
    workspacePaths.members(workspaceId),
    input,
  );
}

export function updateMember(
  client: V1Client,
  workspaceId: string,
  memberId: string,
  patch: MemberUpdateInput,
): Promise<WorkspaceMember> {
  return client.patch<WorkspaceMember>(
    workspacePaths.member(workspaceId, memberId),
    patch,
  );
}

/** DELETE revokes and keeps history; the row is returned with status `revoked`. */
export function revokeMember(
  client: V1Client,
  workspaceId: string,
  memberId: string,
): Promise<WorkspaceMember> {
  return client.delete<WorkspaceMember>(
    workspacePaths.member(workspaceId, memberId),
  );
}

export function listWorkspaceEvents(
  client: V1Client,
  workspaceId: string,
  params: PageParams,
  options?: { signal?: AbortSignal },
): Promise<Page<WorkspaceEvent>> {
  return client.get<Page<WorkspaceEvent>>(workspacePaths.events(workspaceId), {
    searchParams: { page: params.page, page_size: params.pageSize },
    signal: options?.signal,
  });
}

export function getAllowlist(
  client: V1Client,
  workspaceId: string,
  options?: { signal?: AbortSignal },
): Promise<AllowlistResponse> {
  return client.get<AllowlistResponse>(
    workspacePaths.allowedProviders(workspaceId),
    options,
  );
}

/** Replaces the whole grant list **and** the defaults attached to it. */
export function putAllowlist(
  client: V1Client,
  workspaceId: string,
  input: AllowlistUpdateInput,
): Promise<AllowlistResponse> {
  return client.put<AllowlistResponse>(
    workspacePaths.allowedProviders(workspaceId),
    input,
  );
}

/** Replaces the whole per-capability default map. */
export function putWorkspaceDefaults(
  client: V1Client,
  workspaceId: string,
  input: WorkspaceDefaultsInput,
): Promise<Partial<Record<Capability, string>>> {
  return client.put<Partial<Record<Capability, string>>>(
    workspacePaths.modelDefaults(workspaceId),
    input,
  );
}

export function getQuota(
  client: V1Client,
  workspaceId: string,
  period?: string,
  options?: { signal?: AbortSignal },
): Promise<Quota> {
  return client.get<Quota>(workspacePaths.quota(workspaceId), {
    searchParams: { period },
    signal: options?.signal,
  });
}

export function listUsage(
  client: V1Client,
  workspaceId: string,
  params: PageParams,
  options?: { signal?: AbortSignal },
): Promise<Page<UsageRecord>> {
  return client.get<Page<UsageRecord>>(workspacePaths.usage(workspaceId), {
    searchParams: { page: params.page, page_size: params.pageSize },
    signal: options?.signal,
  });
}

/**
 * Read every membership page needed to locate the caller.
 *
 * A single page that does not contain the caller proves nothing, so the loop
 * stops only when the membership is found or all rows have been read.
 */
export async function loadMembersForRole(
  client: V1Client,
  workspaceId: string,
  actorRef: string,
  options?: { signal?: AbortSignal },
): Promise<{ members: WorkspaceMember[]; total: number }> {
  const members: WorkspaceMember[] = [];
  let total = 0;

  for (let page = 1; page <= MAX_MEMBER_PAGES; page += 1) {
    const response = await listMembers(
      client,
      workspaceId,
      {
        page,
        pageSize: MEMBER_PAGE_SIZE,
      },
      options,
    );
    total = response.meta.total;
    members.push(...response.items);
    if (members.some((member) => member.actor_ref === actorRef)) break;
    if (members.length >= total || response.items.length === 0) break;
  }

  return { members, total };
}
