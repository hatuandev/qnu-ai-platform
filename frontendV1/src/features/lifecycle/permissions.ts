import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";
import type { LifecycleOperation, ResourceKind } from "./types";

export function isLifecycleAdmin(
  role: CallerWorkspaceRole | undefined,
): boolean {
  return (
    role?.kind === "platform-admin" ||
    (role?.kind === "member" && role.role === "admin")
  );
}
export function isLifecycleEditor(
  role: CallerWorkspaceRole | undefined,
): boolean {
  return (
    isLifecycleAdmin(role) ||
    (role?.kind === "member" && role.role === "editor")
  );
}
export function canReadOperations(role: CallerWorkspaceRole): boolean {
  return (
    isLifecycleEditor(role) ||
    (role.kind === "member" && role.role === "reviewer")
  );
}
export function canLifecycleAction(
  role: CallerWorkspaceRole | undefined,
  kind: ResourceKind,
  action: LifecycleOperation,
  options: {
    ownedConversation?: boolean;
    deleted?: boolean;
    turn?: boolean;
  } = {},
): boolean {
  if (kind === "conversation" || (kind === "job" && options.turn))
    return options.ownedConversation === true;
  if (
    kind === "assistant" ||
    kind === "index" ||
    action === "delete" ||
    action === "replace" ||
    (action === "restore" && options.deleted)
  )
    return isLifecycleAdmin(role);
  return isLifecycleEditor(role);
}
