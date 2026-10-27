import { useCallback, useMemo, useSyncExternalStore } from "react";
import { getTokenState, subscribeToken } from "@/app/api/v1/session-token";

/**
 * Post-OCR draft store.
 *
 * The draft must survive switching to the "Đối chiếu ảnh & Văn bản" tab, which
 * unmounts the review panel (Radix Tabs unmounts inactive content). Keeping the
 * map inside the panel loses the edit exactly when the user goes to compare it
 * with the scan.
 *
 * The store therefore lives outside React and pins every draft to a scope:
 * auth session + workspace + collection + source + revision + OCR run. A draft
 * can never be read for another source, and `baseVersion`/`baseSha256` record
 * the version it was written against so a newer server version is never
 * silently adopted as the new basis.
 */

export type OcrDraftScope = {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
  runId: string;
};

export type OcrDraft = {
  /** Derivative text version the draft was written against. */
  baseVersion: number;
  baseSha256: string;
  changes: ReadonlyMap<string, string>;
  updatedAt: number;
};

type Entry = {
  sessionId: number;
  draft: OcrDraft;
};

const drafts = new Map<string, Entry>();
const listeners = new Set<() => void>();
let lastSessionId = getTokenState().sessionId;

function emit(): void {
  for (const listener of listeners) listener();
}

function scopeKey(scope: OcrDraftScope, sessionId: number): string {
  return [
    sessionId,
    scope.workspaceId,
    scope.collectionId,
    scope.sourceId,
    scope.revisionId,
    scope.runId,
  ].join("|");
}

/** Drops every draft as soon as the auth session changes (logout, expiry, new token). */
function syncSession(): number {
  const sessionId = getTokenState().sessionId;
  if (sessionId !== lastSessionId) {
    lastSessionId = sessionId;
    if (drafts.size > 0) {
      drafts.clear();
      emit();
    }
  }
  return sessionId;
}

// The token store is in-memory and process-wide; a logout must not leave a
// previous user's unsaved corrections behind.
subscribeToken(() => {
  syncSession();
});

export function readOcrDraft(
  scope: OcrDraftScope | null,
  sessionId = getTokenState().sessionId,
): OcrDraft | null {
  if (!scope) return null;
  return drafts.get(scopeKey(scope, sessionId))?.draft ?? null;
}

export function hasOcrDraft(scope: OcrDraftScope | null): boolean {
  const draft = readOcrDraft(scope);
  return Boolean(draft && draft.changes.size > 0);
}

export function writeOcrDraft(
  scope: OcrDraftScope,
  base: { version: number; sha256: string },
  changes: ReadonlyMap<string, string>,
): void {
  const sessionId = getTokenState().sessionId;
  const key = scopeKey(scope, sessionId);
  if (changes.size === 0) {
    if (drafts.delete(key)) emit();
    return;
  }
  // Only explicit rebase may change the basis of edits already in this map.
  const pinned = drafts.get(key)?.draft;
  drafts.set(key, {
    sessionId,
    draft: {
      baseVersion: pinned?.baseVersion ?? base.version,
      baseSha256: pinned?.baseSha256 ?? base.sha256,
      changes: new Map(changes),
      updatedAt: Date.now(),
    },
  });
  emit();
}

export function clearOcrDraft(scope: OcrDraftScope): void {
  if (drafts.delete(scopeKey(scope, getTokenState().sessionId))) emit();
}

/**
 * Explicitly moves a draft onto a newer base version after the user has seen
 * the conflict. Never called automatically: adopting a new base silently would
 * let a stale edit overwrite someone else's save.
 */
export function rebaseOcrDraft(
  scope: OcrDraftScope,
  base: { version: number; sha256: string },
): void {
  const key = scopeKey(scope, getTokenState().sessionId);
  const entry = drafts.get(key);
  if (!entry) return;
  drafts.set(key, {
    ...entry,
    draft: {
      ...entry.draft,
      baseVersion: base.version,
      baseSha256: base.sha256,
      updatedAt: Date.now(),
    },
  });
  emit();
}

/** Test/logout seam: forgets every draft in the process. */
export function clearAllOcrDrafts(): void {
  if (drafts.size === 0) return;
  drafts.clear();
  emit();
}

export function subscribeOcrDrafts(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export type OcrDraftHandle = {
  draft: OcrDraft | null;
  changes: ReadonlyMap<string, string>;
  hasChanges: boolean;
  /** True when the server version moved on since the draft was written. */
  baseMovedOn: (current: { version: number; sha256: string }) => boolean;
  update: (
    updater: (previous: ReadonlyMap<string, string>) => Map<string, string>,
  ) => void;
  clear: () => void;
  rebase: (base: { version: number; sha256: string }) => void;
};

const EMPTY_CHANGES: ReadonlyMap<string, string> = new Map();

export function useOcrDraft(
  scope: OcrDraftScope | null,
  base: { version: number; sha256: string } | null,
): OcrDraftHandle {
  const sessionId = useSyncExternalStore(
    subscribeToken,
    () => syncSession(),
    () => lastSessionId,
  );

  const key = useMemo(
    () => (scope ? scopeKey(scope, sessionId) : null),
    [scope, sessionId],
  );

  const getSnapshot = useCallback(
    () => (key ? (drafts.get(key)?.draft ?? null) : null),
    [key],
  );

  const draft = useSyncExternalStore(
    subscribeOcrDrafts,
    getSnapshot,
    getSnapshot,
  );
  const changes = draft?.changes ?? EMPTY_CHANGES;

  const update = useCallback(
    (
      updater: (previous: ReadonlyMap<string, string>) => Map<string, string>,
    ) => {
      if (!scope || !base || getTokenState().sessionId !== sessionId) return;
      const current = readOcrDraft(scope)?.changes ?? EMPTY_CHANGES;
      writeOcrDraft(scope, base, updater(current));
    },
    [scope, base, sessionId],
  );

  const clear = useCallback(() => {
    if (scope && getTokenState().sessionId === sessionId) clearOcrDraft(scope);
  }, [scope, sessionId]);

  const rebase = useCallback(
    (next: { version: number; sha256: string }) => {
      if (scope && getTokenState().sessionId === sessionId) {
        rebaseOcrDraft(scope, next);
      }
    },
    [scope, sessionId],
  );

  const baseMovedOn = useCallback(
    (current: { version: number; sha256: string }) =>
      Boolean(
        draft &&
          draft.changes.size > 0 &&
          (draft.baseVersion !== current.version ||
            draft.baseSha256 !== current.sha256),
      ),
    [draft],
  );

  return {
    draft,
    changes,
    hasChanges: changes.size > 0,
    baseMovedOn,
    update,
    clear,
    rebase,
  };
}
