import type { CallerWorkspaceRole } from "@/app/auth/v1/permissions";

/**
 * Access control policies for AI Assistants in QNU AI Platform v1.
 *
 * Implements server invariants from `backendV1/qnu/domains/assistants/service.py`:
 * - All authenticated workspace members can read assistant list and details.
 * - Only workspace administrators (`admin` role in membership) or platform workspace
 *   administrators (`ai.workspaces.manage`) can create, update, or toggle assistants.
 * - Workspace `editor` can upload documents to knowledge base, but CANNOT manage assistants.
 * - Platform `ai.models.manage` does NOT grant assistant modification rights.
 * - In unknown/pending role state, write actions remain disabled.
 */
export function canManageAssistants(role: CallerWorkspaceRole): boolean {
  if (role.kind === "platform-admin") {
    return true;
  }
  if (role.kind === "member") {
    return role.role === "admin";
  }
  return false;
}
