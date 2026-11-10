import type { AuthActor } from "@/api/auth/types";

/**
 * Checks whether the current actor is a platform-wide admin
 * who can manage workspaces and platform settings.
 */
export function isPlatformAdmin(actor: AuthActor | null | undefined): boolean {
  if (!actor?.authenticated) return false;
  const roles = new Set((actor.roles || []).map((r) => r.trim().toLowerCase()));
  const granted = new Set(
    (actor.permissions || []).map((p) => p.trim().toLowerCase()),
  );
  return (
    roles.has("ai.admin") ||
    granted.has("ai.access.admin") ||
    granted.has("ai.workspaces.manage")
  );
}

/**
 * Checks whether the current actor has ModelOps administration rights
 * required for GET/PUT /modelops/defaults and provider management.
 */
export function isModelAdmin(actor: AuthActor | null | undefined): boolean {
  if (!actor?.authenticated) return false;
  const roles = new Set((actor.roles || []).map((r) => r.trim().toLowerCase()));
  const granted = new Set(
    (actor.permissions || []).map((p) => p.trim().toLowerCase()),
  );
  return (
    roles.has("ai.admin") ||
    granted.has("ai.access.admin") ||
    granted.has("ai.models.manage")
  );
}
