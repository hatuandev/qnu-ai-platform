// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { clearAccessToken, setAccessToken } from "@/app/api/v1";
import {
  clearAllOcrDrafts,
  useOcrDraft,
} from "@/features/knowledge/ocr-draft-store";

const scope = {
  workspaceId: "w",
  collectionId: "c",
  sourceId: "s",
  revisionId: "r",
  runId: "ocr",
};
const initialBase = { version: 0, sha256: "0".repeat(64) };
const newBase = { version: 1, sha256: "1".repeat(64) };
afterEach(() => {
  cleanup();
  clearAllOcrDrafts();
  clearAccessToken();
});

test("editing another unit must not silently rebase the entire old OCR draft", () => {
  const hook = renderHook(({ base }) => useOcrDraft(scope, base), {
    initialProps: { base: initialBase },
  });
  act(() =>
    hook.result.current.update(() => new Map([["ev-1", "local edit"]])),
  );
  hook.rerender({ base: newBase });
  expect(hook.result.current.baseMovedOn(newBase)).toBe(true);
  act(() =>
    hook.result.current.update(
      (old) => new Map([...old, ["ev-2", "second edit"]]),
    ),
  );
  expect(hook.result.current.draft?.baseVersion).toBe(0);
  expect(hook.result.current.baseMovedOn(newBase)).toBe(true);
});

test("explicitly accepting the new OCR base is permitted", () => {
  const hook = renderHook(() => useOcrDraft(scope, initialBase));
  act(() =>
    hook.result.current.update(() => new Map([["ev-1", "local edit"]])),
  );
  act(() => hook.result.current.rebase(newBase));
  expect(hook.result.current.draft?.baseVersion).toBe(1);
  expect(hook.result.current.baseMovedOn(newBase)).toBe(false);
});

test("reverting one unit after a refresh does not rebase the remaining edits", () => {
  const hook = renderHook(({ base }) => useOcrDraft(scope, base), {
    initialProps: { base: initialBase },
  });
  act(() =>
    hook.result.current.update(
      () =>
        new Map([
          ["ev-1", "first"],
          ["ev-2", "second"],
        ]),
    ),
  );
  hook.rerender({ base: newBase });
  act(() =>
    hook.result.current.update((old) => {
      const next = new Map(old);
      next.delete("ev-2");
      return next;
    }),
  );
  expect(hook.result.current.draft?.baseSha256).toBe(initialBase.sha256);
  expect(hook.result.current.changes.get("ev-1")).toBe("first");
  expect(hook.result.current.baseMovedOn(newBase)).toBe(true);
});

test("late callbacks from the old session cannot edit, clear or rebase a new session draft", () => {
  setAccessToken("synthetic-session-one");
  const hook = renderHook(() => useOcrDraft(scope, initialBase));
  const oldHandle = hook.result.current;
  act(() => setAccessToken("synthetic-session-two"));
  act(() =>
    hook.result.current.update(() => new Map([["ev-1", "new session draft"]])),
  );
  act(() => {
    oldHandle.update(() => new Map([["ev-1", "stale edit"]]));
    oldHandle.rebase(newBase);
    oldHandle.clear();
  });
  expect(hook.result.current.changes.get("ev-1")).toBe("new session draft");
  expect(hook.result.current.draft?.baseVersion).toBe(0);
});
