/**
 * Permission checks for v1 screens.
 *
 * Mirrors `AuthActor.has_permission` in `backendV1/qnu/domains/identity/actor.py`
 * so the UI hides an action exactly when the server would reject it. This is a
 * UI convenience only: every decision is re-made by the backend, and nothing here
 * can grant a permission the server did not return.
 */

import type { V1Actor } from "./types";

function normalizedSet(values: readonly string[] | undefined): Set<string> {
  return new Set(
    (values ?? [])
      .map((value) => value.trim().toLowerCase())
      .filter((value) => value.length > 0),
  );
}

export function hasV1Permission(
  actor: V1Actor | null | undefined,
  permission: string | undefined,
): boolean {
  if (!permission) return true;
  if (!actor || actor.authenticated === false) return false;

  const wanted = permission.trim().toLowerCase();
  const granted = normalizedSet(actor.permissions);
  if (granted.has(wanted)) return true;

  const roles = normalizedSet(actor.roles);
  const isAdmin = roles.has("ai.admin") || granted.has("ai.access.admin");
  return isAdmin && wanted.startsWith("ai.");
}

export function hasAnyV1Permission(
  actor: V1Actor | null | undefined,
  permissions: readonly string[],
): boolean {
  return permissions.some((permission) => hasV1Permission(actor, permission));
}

/**
 * Platform administration of workspaces. A workspace `admin` role does **not**
 * imply this: the backend checks `ai.workspaces.manage` for create/update and
 * `ai.models.manage` for provider administration.
 */
export function isPlatformWorkspaceAdmin(
  actor: V1Actor | null | undefined,
): boolean {
  return hasV1Permission(actor, "ai.workspaces.manage");
}

export function isModelAdmin(actor: V1Actor | null | undefined): boolean {
  return hasV1Permission(actor, "ai.models.manage");
}

export type WorkspaceRole = "admin" | "editor" | "reviewer" | "member";

/** Role of the caller inside one workspace, as returned by the members API. */
export type CallerWorkspaceRole =
  | { kind: "platform-admin" }
  | { kind: "member"; role: WorkspaceRole }
  | { kind: "none" }
  /** Membership pages loaded so far do not contain the caller yet. */
  | { kind: "unknown" };

export type MembershipLike = {
  actor_ref: string;
  role: string;
  status: string;
};

/**
 * Resolve the caller's role from server-returned membership rows.
 *
 * `actor_ref` is an opaque, case-sensitive identifier: it is compared verbatim
 * and never substituted with an email or display name.
 */
export function resolveCallerWorkspaceRole(args: {
  actor: V1Actor | null | undefined;
  members: readonly MembershipLike[];
  /** Total rows the server reports; when larger than `members`, the answer is partial. */
  total: number;
  platformAdmin: boolean;
}): CallerWorkspaceRole {
  if (args.platformAdmin) return { kind: "platform-admin" };
  const actorRef = args.actor?.actor_id?.trim();
  if (!actorRef) return { kind: "none" };

  const own = args.members.find((member) => member.actor_ref === actorRef);
  if (own) {
    if (own.status !== "active") return { kind: "none" };
    return { kind: "member", role: own.role as WorkspaceRole };
  }
  // A page that does not contain the caller proves nothing while rows remain.
  return args.members.length < args.total
    ? { kind: "unknown" }
    : { kind: "none" };
}

export function canManageMembers(role: CallerWorkspaceRole): boolean {
  return (
    role.kind === "platform-admin" ||
    (role.kind === "member" && role.role === "admin")
  );
}

export function canChooseWorkspaceDefaults(role: CallerWorkspaceRole): boolean {
  return canManageMembers(role);
}
