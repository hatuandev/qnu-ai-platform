/**
 * Pure helpers for the workspace model allowlist.
 *
 * `PUT /workspaces/{id}/allowed-providers` **replaces** the grant list and the
 * defaults attached to it, so every edit must be expressed as a full, explicit
 * draft. These helpers keep untouched capabilities intact and make the removal
 * of a default visible before the request is sent.
 */

import type {
  AllowlistResponse,
  AllowlistUpdateInput,
  Capability,
} from "./types.ts";
import { CAPABILITIES } from "./types.ts";

export type AllowlistDraft = {
  providerIds: string[];
  defaults: Partial<Record<Capability, string>>;
};

export function draftFromAllowlist(
  response: AllowlistResponse,
): AllowlistDraft {
  const providerIds: string[] = [];
  const defaults: Partial<Record<Capability, string>> = {};

  for (const provider of response.providers) {
    providerIds.push(provider.provider_id);
    for (const capability of provider.default_capabilities) {
      defaults[capability] = provider.provider_id;
    }
  }

  return { providerIds, defaults };
}

export function toggleProvider(
  draft: AllowlistDraft,
  providerId: string,
  granted: boolean,
): AllowlistDraft {
  const providerIds = granted
    ? Array.from(new Set([...draft.providerIds, providerId]))
    : draft.providerIds.filter((id) => id !== providerId);
  return { providerIds, defaults: { ...draft.defaults } };
}

export function setCapabilityDefault(
  draft: AllowlistDraft,
  capability: Capability,
  providerId: string | null,
): AllowlistDraft {
  const defaults = { ...draft.defaults };
  if (providerId === null) delete defaults[capability];
  else defaults[capability] = providerId;
  return { providerIds: [...draft.providerIds], defaults };
}

/**
 * Defaults that point at a provider which is no longer granted.
 *
 * The backend rejects such a payload (`allowlist_default_not_allowed`), so the
 * UI must show them and ask before dropping them.
 */
export function orphanedDefaults(
  draft: AllowlistDraft,
): Array<{ capability: Capability; providerId: string }> {
  const granted = new Set(draft.providerIds);
  return CAPABILITIES.filter((capability) => {
    const providerId = draft.defaults[capability];
    return providerId !== undefined && !granted.has(providerId);
  }).map((capability) => ({
    capability,
    providerId: draft.defaults[capability] as string,
  }));
}

/** Drop only the defaults that lost their provider; everything else is kept. */
export function pruneOrphanedDefaults(draft: AllowlistDraft): AllowlistDraft {
  const defaults = { ...draft.defaults };
  for (const { capability } of orphanedDefaults(draft))
    delete defaults[capability];
  return { providerIds: [...draft.providerIds], defaults };
}

export function toAllowlistInput(draft: AllowlistDraft): AllowlistUpdateInput {
  return {
    provider_ids: [...draft.providerIds],
    defaults: { ...draft.defaults },
  };
}

export function sameAllowlist(a: AllowlistDraft, b: AllowlistDraft): boolean {
  if (a.providerIds.length !== b.providerIds.length) return false;
  const left = [...a.providerIds].sort();
  const right = [...b.providerIds].sort();
  if (left.some((id, index) => id !== right[index])) return false;
  return CAPABILITIES.every(
    (capability) => a.defaults[capability] === b.defaults[capability],
  );
}

/**
 * Merge one capability change into the current defaults.
 *
 * Used by `PUT /workspaces/{id}/model-defaults`, which also replaces the whole
 * map: the request must carry every unchanged capability as well.
 */
export function withCapabilityDefault(
  current: Partial<Record<Capability, string>>,
  capability: Capability,
  providerId: string | null,
): Partial<Record<Capability, string>> {
  const next = { ...current };
  if (providerId === null) delete next[capability];
  else next[capability] = providerId;
  return next;
}
