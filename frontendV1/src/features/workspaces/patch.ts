/** PATCH /workspaces/{id} only accepts name/description/status, and `null` means "no change". */

import type { WorkspaceUpdateInput } from "./types.ts";

export type WorkspacePatchBaseline = {
  name: string;
  description: string | null;
};

export function buildWorkspacePatch(
  initial: WorkspacePatchBaseline,
  values: WorkspacePatchBaseline,
): WorkspaceUpdateInput {
  const patch: WorkspaceUpdateInput = {};

  const nextName = values.name.trim();
  if (nextName !== initial.name.trim()) patch.name = nextName;

  // An empty string is the only way to clear a description: `null` is ignored.
  const nextDescription = values.description?.trim() ?? "";
  const previousDescription = initial.description?.trim() ?? "";
  if (nextDescription !== previousDescription)
    patch.description = nextDescription;

  return patch;
}

export function isEmptyPatch(patch: WorkspaceUpdateInput): boolean {
  return Object.keys(patch).length === 0;
}
