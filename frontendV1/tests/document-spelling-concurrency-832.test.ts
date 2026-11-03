import { expect, test, vi } from "vitest";
import { ApiProblemError } from "@/app/api/v1";
import {
  checkWholeDocument,
  type DetectCall,
  type DocumentSpellingReport,
} from "@/features/knowledge/ocr-spelling-batch";
import type {
  DetectionResponse,
  ReviewDocument,
} from "@/features/knowledge/ocr-types";

const doc: ReviewDocument = {
  run_id: "ocr",
  version: 3,
  version_id: "v3",
  canonical_sha256: "hash",
  original_sha256: "original",
  markdown_sha256: "md",
  saved_at: null,
  units: [1, 2, 3, 4, 5].map((page) => ({
    evidence_id: `e-${page}`,
    page,
    kind: "paragraph",
    text: "Nội dung",
    original_text: "Nội dung",
    row: null,
    column: null,
    bbox: {},
  })),
};
function harness() {
  const gates = new Map<
    string,
    {
      done: (change?: Partial<DetectionResponse>) => void;
      fail: (e: unknown) => void;
    }
  >();
  let active = 0;
  let peak = 0;
  let stopped = false;
  let snapshot: DocumentSpellingReport | undefined;
  const detect = vi.fn<DetectCall>(
    (request) =>
      new Promise((resolve, reject) => {
        active++;
        peak = Math.max(peak, active);
        const finish = () => {
          active--;
        };
        gates.set(request.body.evidence_ids[0], {
          done: (change = {}) => {
            finish();
            resolve({
              id: request.idempotencyKey,
              status: "completed",
              version: 3,
              canonical_sha256: "hash",
              checked_evidence_ids: request.body.evidence_ids,
              suggestions: [],
              usage_id: null,
              error_code: null,
              created_at: "2026-11-03",
              ...change,
            });
          },
          fail: (e) => {
            finish();
            reject(e);
          },
        });
      }),
  );
  const run = () =>
    checkWholeDocument({
      doc,
      key: "key",
      providerId: "provider",
      sourceVersion: 3,
      detect,
      shouldStop: () => stopped,
      onUpdate: (r) => {
        snapshot = r;
      },
    });
  return {
    detect,
    gates,
    run,
    stop: () => {
      stopped = true;
    },
    peak: () => peak,
    snapshot: () => snapshot,
  };
}
test("two asynchronous slots replenish independently, never exceed two, and retain source order", async () => {
  const h = harness();
  const run = h.run();
  expect(h.detect).toHaveBeenCalledTimes(2);
  expect(
    h.snapshot()?.batches.filter((b) => b.status === "running"),
  ).toHaveLength(2);
  h.gates.get("e-2")?.done();
  await vi.waitFor(() => expect(h.gates.has("e-3")).toBe(true));
  expect(h.snapshot()?.batches[0].status).toBe("running");
  h.gates.get("e-3")?.done();
  await vi.waitFor(() => expect(h.gates.has("e-4")).toBe(true));
  h.gates.get("e-1")?.done();
  await vi.waitFor(() => expect(h.gates.has("e-5")).toBe(true));
  h.gates.get("e-5")?.done();
  h.gates.get("e-4")?.done();
  const r = await run;
  expect(h.peak()).toBe(2);
  expect(r.batches.map((b) => b.page)).toEqual([1, 2, 3, 4, 5]);
  expect(r.batches.every((b) => b.status === "completed")).toBe(true);
  expect(h.detect.mock.calls.map(([c]) => c.idempotencyKey)).toEqual(
    [1, 2, 3, 4, 5].map((n) => `key:batch:${n}`),
  );
});
test("invalid suggestions fail only their own batch", async () => {
  const h = harness();
  const run = h.run();
  h.gates.get("e-1")?.fail(
    new ApiProblemError({
      status: 502,
      code: "ocr_spelling_invalid",
      message: "invalid suggestions",
    }),
  );
  for (const page of [2, 3, 4, 5]) {
    await vi.waitFor(() => expect(h.gates.has(`e-${page}`)).toBe(true));
    h.gates.get(`e-${page}`)?.done();
  }
  const result = await run;
  expect(result.batches.map((batch) => batch.status)).toEqual([
    "failed",
    "completed",
    "completed",
    "completed",
    "completed",
  ]);
  expect(h.detect).toHaveBeenCalledTimes(5);
});

test.each(["stop", "uncertain", "quota", "stale"])(
  "%s stops unsent work but drains both active requests without retry",
  async (reason) => {
    const h = harness();
    const run = h.run();
    expect(h.detect).toHaveBeenCalledTimes(2);
    if (reason === "stop") h.stop();
    if (reason === "quota")
      h.gates.get("e-1")?.fail(
        new ApiProblemError({
          status: 429,
          code: "quota_exceeded",
          message: "quota",
        }),
      );
    else
      h.gates
        .get("e-1")
        ?.done(
          reason === "uncertain"
            ? { status: "uncertain", error_code: "chat_provider_uncertain" }
            : reason === "stale"
              ? { version: 4 }
              : {},
        );
    await vi.waitFor(() =>
      expect(h.snapshot()?.batches[0].status).not.toBe("running"),
    );
    expect(h.snapshot()?.finished).toBe(false);
    expect(h.detect).toHaveBeenCalledTimes(2);
    h.gates.get("e-2")?.done();
    const r = await run;
    expect(r.batches[1].status).toBe("completed");
    expect(r.batches.slice(2).every((b) => b.status === "not_run")).toBe(true);
    expect(r.finished).toBe(true);
    expect(h.detect).toHaveBeenCalledTimes(2);
  },
);
