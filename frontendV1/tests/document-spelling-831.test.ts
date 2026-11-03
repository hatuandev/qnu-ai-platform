import { expect, test, vi } from "vitest";
import { ApiProblemError } from "@/app/api/v1";
import {
  checkWholeDocument,
  type DetectCall,
  planSpellingBatches,
} from "@/features/knowledge/ocr-spelling-batch";
import type { ReviewDocument, TextUnit } from "@/features/knowledge/ocr-types";

function doc(count = 105): ReviewDocument {
  return {
    run_id: "ocr",
    version: 2,
    version_id: "v2",
    canonical_sha256: "source-hash",
    original_sha256: "original",
    markdown_sha256: "md",
    saved_at: null,
    units: Array.from(
      { length: count },
      (_, i) =>
        ({
          evidence_id: `e-${i}`,
          page: Math.floor(i / 30) + 1,
          kind: i % 3 === 0 ? "table_cell" : "text",
          text: `Nội dung ${i}`,
          original_text: `Nội dung ${i}`,
          bbox: {},
          row: null,
          column: null,
        }) as TextUnit,
    ),
  };
}
const success: DetectCall = async ({ body, idempotencyKey }) => ({
  id: idempotencyKey,
  status: "completed",
  version: body.expected_version,
  canonical_sha256: body.expected_sha256,
  checked_evidence_ids: body.evidence_ids,
  suggestions: [],
  error_code: null,
  usage_id: "usage",
  created_at: "2026-11-02",
});
const options = (d = doc()) => ({
  doc: d,
  key: "root-key",
  providerId: "chat-model",
  sourceVersion: 2,
  detect: vi.fn(success),
  shouldStop: () => false,
  onUpdate: vi.fn(),
  concurrency: 1 as const,
});

test("whole document covers more than 100 units without truncation, per page and bounded group", () => {
  const d = doc(235);
  const batches = planSpellingBatches(d, "key");
  expect(batches.flatMap((b) => b.evidenceIds)).toEqual(
    d.units.map((u) => u.evidence_id),
  );
  expect(new Set(batches.map((b) => b.key)).size).toBe(batches.length);
  expect(batches.every((b) => b.evidenceIds.length <= 20)).toBe(true);
  expect(
    batches.every((b) =>
      b.evidenceIds.every(
        (id) => d.units.find((u) => u.evidence_id === id)?.page === b.page,
      ),
    ),
  ).toBe(true);
});
test("images and blank units are excluded; long evidence stays intact", () => {
  const d = doc(3);
  d.units[0].text = "x".repeat(9000);
  d.units[1].kind = "image";
  d.units[2].text = " ";
  expect(planSpellingBatches(d, "key").map((b) => b.evidenceIds)).toEqual([
    ["e-0"],
  ]);
});
test("all requests pin version/hash/provider with independent stable idempotency keys", async () => {
  const o = options();
  const r = await checkWholeDocument(o);
  expect(r.batches.every((b) => b.status === "completed")).toBe(true);
  expect(o.detect).toHaveBeenCalledTimes(r.batches.length);
  for (const [call] of o.detect.mock.calls)
    expect(call.body).toMatchObject({
      expected_version: 2,
      expected_sha256: "source-hash",
      source_version: 2,
      provider_id: "chat-model",
    });
  expect(o.detect.mock.calls.map(([c]) => c.idempotencyKey)).toEqual(
    r.batches.map((b) => b.key),
  );
});
test("a truncated group is replaced by smaller requests without resending successful groups", async () => {
  const o = options();
  o.detect.mockImplementationOnce(async (c) => ({
    ...(await success(c)),
    status: "failed",
    error_code: "chat_output_truncated",
  }));
  const r = await checkWholeDocument(o);
  expect(r.batches.every((b) => b.status === "completed")).toBe(true);
  expect(o.detect).toHaveBeenCalledTimes(r.batches.length + 1);
  const [first] = o.detect.mock.calls[0];
  expect(r.batches.slice(0, 2).flatMap((b) => b.evidenceIds)).toEqual(
    first.body.evidence_ids,
  );
  expect(first.body.max_output_tokens).toBeUndefined();
});
test.each(["uncertain", "running"])(
  "%s result stops unsent groups, preserving its real check",
  async (status) => {
    const o = options();
    o.detect.mockImplementationOnce(async (c) => ({
      ...(await success(c)),
      status,
      error_code: "chat_provider_uncertain",
    }));
    const r = await checkWholeDocument(o);
    expect(r.batches[0].status).toBe("uncertain");
    expect(r.batches[0].check?.status).toBe(status);
    expect(r.batches.slice(1).every((b) => b.status === "not_run")).toBe(true);
    expect(o.detect).toHaveBeenCalledTimes(1);
  },
);
test.each(["quota_exceeded", "model_not_configured"])(
  "global %s stops the cohort",
  async (code) => {
    const o = options();
    o.detect.mockRejectedValueOnce(
      new ApiProblemError({ status: 409, code, message: "diagnostic" }),
    );
    const r = await checkWholeDocument(o);
    expect(r.batches[0].errorCode).toBe(code);
    expect(o.detect).toHaveBeenCalledTimes(1);
  },
);
test("network loss is uncertain, never a completed report or automatic resend", async () => {
  const o = options();
  o.detect.mockRejectedValueOnce(new Error("network"));
  const r = await checkWholeDocument(o);
  expect(r.batches[0].status).toBe("uncertain");
  expect(o.detect).toHaveBeenCalledTimes(1);
});
test("version mismatch stops remaining work without making stale suggestions actionable", async () => {
  const o = options();
  o.detect.mockImplementationOnce(async (c) => ({
    ...(await success(c)),
    version: 3,
  }));
  const r = await checkWholeDocument(o);
  expect(r.batches[0]).toMatchObject({
    status: "failed",
    errorCode: "ocr_text_source_changed",
  });
  expect(o.detect).toHaveBeenCalledTimes(1);
});
test("stop waits for the active response and leaves remaining groups explicitly not run", async () => {
  const o = options();
  let stop = false;
  o.shouldStop = () => stop;
  o.detect.mockImplementationOnce(async (c) => {
    stop = true;
    return success(c);
  });
  const r = await checkWholeDocument(o);
  expect(r.batches[0].status).toBe("completed");
  expect(r.batches[1].status).toBe("not_run");
  expect(o.detect).toHaveBeenCalledTimes(1);
});
