// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { DetectCall } from "@/features/knowledge/ocr-spelling-batch";
import type { ReviewDocument } from "@/features/knowledge/ocr-types";
import { useDocumentSpelling } from "@/features/knowledge/use-document-spelling";

afterEach(cleanup);
const doc: ReviewDocument = {
  run_id: "ocr",
  version: 0,
  version_id: "v0",
  canonical_sha256: "hash",
  original_sha256: "original",
  markdown_sha256: "md",
  saved_at: null,
  units: [1, 2, 3].map((page) => ({
    page,
    evidence_id: `e-${page}`,
    text: "Nội dung",
    original_text: "Nội dung",
    kind: "paragraph",
    row: null,
    column: null,
    bbox: {},
  })),
};
const success: DetectCall = async ({ body, idempotencyKey }) => ({
  id: idempotencyKey,
  status: "completed",
  version: body.expected_version,
  canonical_sha256: body.expected_sha256,
  checked_evidence_ids: body.evidence_ids,
  suggestions: [],
  error_code: null,
  usage_id: null,
  created_at: "2026-11-02",
});
function deferredDetection() {
  let resolve!: () => void;
  const wait = new Promise<void>((done) => {
    resolve = done;
  });
  const detect = vi.fn<DetectCall>(async (request) => {
    await wait;
    return success(request);
  });
  return { detect, resolve };
}

test("blocks duplicate start while a request is in flight and honors stop after current group", async () => {
  const d = deferredDetection();
  const { result } = renderHook(() =>
    useDocumentSpelling("scope", () => true, d.detect),
  );
  let run: ReturnType<typeof result.current.start>;
  act(() => {
    run = result.current.start(doc, "key", null, null);
  });
  await act(async () => {
    await result.current.start(doc, "duplicate", null, null);
  });
  expect(d.detect).toHaveBeenCalledTimes(2);
  act(() => result.current.stop());
  expect(result.current.running).toBe(true);
  await act(async () => {
    d.resolve();
    await run;
  });
  expect(d.detect).toHaveBeenCalledTimes(2);
  expect(result.current.running).toBe(false);
  expect(result.current.report?.batches.map((b) => b.status)).toEqual([
    "completed",
    "completed",
    "not_run",
  ]);
});

test.each(["scope", "session", "unmount"])(
  "%s change stops unsent groups and suppresses stale results",
  async (change) => {
    const d = deferredDetection();
    let current = true;
    const { result, rerender, unmount } = renderHook(
      ({ scope }) => useDocumentSpelling(scope, () => current, d.detect),
      { initialProps: { scope: "first" } },
    );
    let run: ReturnType<typeof result.current.start>;
    let returned: Awaited<typeof run>;
    act(() => {
      run = result.current.start(doc, "key", null, null);
    });
    if (change === "scope") rerender({ scope: "second" });
    if (change === "session") current = false;
    if (change === "unmount") unmount();
    await act(async () => {
      d.resolve();
      returned = await run;
    });
    expect(returned).toBeUndefined();
    expect(d.detect).toHaveBeenCalledTimes(2);
    if (change === "scope") expect(result.current.report).toBeNull();
  },
);

test("an invalid session cannot start inference", async () => {
  const detect = vi.fn(success);
  const { result } = renderHook(() =>
    useDocumentSpelling("scope", () => false, detect),
  );
  await act(async () => {
    await result.current.start(doc, "key", null, null);
  });
  expect(detect).not.toHaveBeenCalled();
  expect(result.current.running).toBe(false);
});
