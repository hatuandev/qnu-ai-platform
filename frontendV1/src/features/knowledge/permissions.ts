import type { CallerWorkspaceRole } from "../../app/auth/v1/permissions.ts";

/**
 * Knowledge collections and source mutations require workspace admin or editor role.
 * (Or platform workspace admin).
 */
export function canManageKnowledge(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin" || role.role === "editor";
  }
  return false;
}

/**
 * Creating a compilation run and editing/previewing drafts require workspace admin or editor.
 */
export function canCreateOrEditCompilation(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin" || role.role === "editor";
  }
  return false;
}

/**
 * Manual review can be initiated by workspace admin, editor, or reviewer.
 */
export function canReviewCompilation(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return (
      role.role === "admin" ||
      role.role === "editor" ||
      role.role === "reviewer"
    );
  }
  return false;
}

/**
 * Reading compilation runs and review reports is permitted for all workspace members.
 */
export function canReadCompilation(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return (
      role.role === "admin" ||
      role.role === "editor" ||
      role.role === "reviewer" ||
      role.role === "member"
    );
  }
  return false;
}

/**
 * Registering a compiled document or adding a version requires admin or editor.
 */
export function canRegisterCompiledDocument(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin" || role.role === "editor";
  }
  return false;
}

/**
 * Approving a compiled version requires admin or reviewer.
 */
export function canApproveCompiledVersion(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin" || role.role === "reviewer";
  }
  return false;
}

/**
 * Publishing an approved compiled version requires admin.
 */
export function canPublishCompiledVersion(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin";
  }
  return false;
}

/**
 * Withdrawing an approved or published compiled version requires admin.
 */
export function canWithdrawCompiledVersion(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return role.role === "admin";
  }
  return false;
}

/**
 * Reading compiled documents, versions, and decision history is permitted for all workspace members.
 */
export function canReadCompiledDocuments(
  role: CallerWorkspaceRole | null | undefined,
): boolean {
  if (!role) return false;
  if (role.kind === "platform-admin") return true;
  if (role.kind === "member") {
    return (
      role.role === "admin" ||
      role.role === "editor" ||
      role.role === "reviewer" ||
      role.role === "member"
    );
  }
  return false;
}
