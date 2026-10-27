import { expect, test } from "vitest";
import { createV1Client } from "@/app/api/v1/client";
import { csvCell, evaluationCsv } from "@/features/evaluation/report-export";
import {
  getEvaluationManifest,
  runEvaluation,
} from "@/features/evaluation/requests";
import type {
  EvaluationRequest,
  EvaluationResult,
} from "@/features/evaluation/types";
import {
  acceptCleanup,
  createBackup,
  downloadBackup,
  getCleanup,
  getRetention,
  listBackups,
  previewBackupDeletion,
  previewCleanup,
  verifyBackup,
} from "@/features/operations/maintenance-requests";
import { acceptRecovery } from "@/features/operations/requests";
import { operationsSearchSchema } from "@/features/operations/search";

function recorder() {
  const calls: {
    url: string;
    method: string;
    headers: Headers;
    body: unknown;
  }[] = [];
  const client = createV1Client({
    fetchImpl: async (url, options) => {
      calls.push({
        url,
        method: options?.method ?? "GET",
        headers: new Headers(options?.headers),
        body: options?.body ? JSON.parse(String(options.body)) : undefined,
      });
      return new Response(JSON.stringify({}), {
        headers: { "Content-Type": "application/json" },
      });
    },
  });
  return { client, calls };
}
test("backup retries preserve the explicit retention and idempotency key", async () => {
  const { client, calls } = recorder();
  await createBackup(client, "w", null, "same-intent");
  await createBackup(client, "w", null, "same-intent");
  expect(calls[0].body).toEqual({ retention_days: null });
  expect(calls[1].body).toEqual(calls[0].body);
  expect(calls.map((c) => c.headers.get("Idempotency-Key"))).toEqual([
    "same-intent",
    "same-intent",
  ]);
});
test("backups use server pagination and protected verification/download routes", async () => {
  const { client, calls } = recorder();
  await listBackups(client, "w", 3, undefined, 50);
  await getRetention(client, "w");
  await verifyBackup(client, "w", "backup");
  await downloadBackup(client, "w", "backup");
  const url = new URL(calls[0].url, "http://synthetic.invalid");
  expect(url.searchParams.get("offset")).toBe("100");
  expect(url.searchParams.get("limit")).toBe("50");
  expect(calls[1].url).toMatch(/operations\/retention$/);
  expect(calls[2].url).toMatch(/backups\/backup\/verify$/);
  expect(calls[3].url).toMatch(/backups\/backup\/download$/);
});
test("backup deletion uses operation preview and exact operation acceptance", async () => {
  const { client, calls } = recorder();
  await previewBackupDeletion(client, "w", "backup", "Expired");
  await acceptRecovery(client, "w", {
    id: "approval",
    preview_sha256: "a".repeat(64),
  });
  expect(calls[0].url).toMatch(/backups\/backup\/delete-preview$/);
  expect(calls[0].body).toEqual({ reason: "Expired" });
  expect(calls[1].url).toMatch(/operations\/actions$/);
  expect(calls[1].headers.get("Idempotency-Key")).toBe("operations:approval");
});
test("storage cleanup is separate from index cleanup and replay preserves approved hash", async () => {
  const { client, calls } = recorder();
  await previewCleanup(client, "w", "Unused files", 72);
  const proof = { id: "gc-one", preview_sha256: "b".repeat(64) };
  await acceptCleanup(client, "w", proof);
  await acceptCleanup(client, "w", proof);
  await getCleanup(client, "w", proof.id);
  expect(calls[0].body).toEqual({ reason: "Unused files", min_age_hours: 72 });
  expect(calls[0].url).toMatch(/operations\/storage-cleanups\/previews$/);
  expect(calls[1].body).toEqual({
    preview_id: proof.id,
    preview_sha256: proof.preview_sha256,
  });
  expect(calls[2].body).toEqual(calls[1].body);
  expect(calls[1].headers.get("Idempotency-Key")).toBe(
    "storage-cleanup:gc-one",
  );
  expect(calls[2].headers.get("Idempotency-Key")).toBe(
    "storage-cleanup:gc-one",
  );
  expect(calls[3].url).toMatch(/storage-cleanups\/actions\/gc-one$/);
});
test("maintenance URLs validate bounded identifiers and survive reload parsing", () => {
  expect(
    operationsSearchSchema.parse({
      view: "storage",
      cleanupActionId: "gc-one",
    }),
  ).toMatchObject({ view: "storage", cleanupActionId: "gc-one", page: 1 });
  expect(operationsSearchSchema.safeParse({ view: "invalid" }).success).toBe(
    false,
  );
  expect(
    operationsSearchSchema.safeParse({ backupId: "x".repeat(65) }).success,
  ).toBe(false);
});
const request: EvaluationRequest = {
  index_run_id: "run",
  manifest_sha256: "c".repeat(64),
  label_version: "v1",
  label_author: "Synthetic annotator",
  label_status: "draft_needs_human_check",
  top_k: 5,
  candidate_k: 30,
  include_rerank: true,
  rerank_provider_id: "provider",
  queries: [
    {
      id: "q",
      query: "=SUM(A1)",
      group: "test",
      gold_chunk_ids: ["chunk"],
      document_ids: null,
    },
  ],
};
test("evaluation carries one pinned snapshot and labels without inventing a history endpoint", async () => {
  const { client, calls } = recorder();
  await getEvaluationManifest(client, "w", "c", "run");
  await runEvaluation(client, "w", "c", request);
  expect(calls[0].url).toMatch(/indexing-runs\/run\/manifest$/);
  expect(calls[1].url).toMatch(/collections\/c\/retrieval-evaluations$/);
  expect(calls[1].method).toBe("POST");
  expect(calls[1].body).toEqual(request);
});
test.each(["=SUM(A1)", "+1", "-1", "@link", " \t=1", "\u0000=1"])(
  "CSV neutralizes formula cell %j",
  (value) => {
    expect(csvCell(value).startsWith("\"'")).toBe(true);
  },
);
test("CSV preserves quotes, lines, empty metrics and explicit answer NOT RUN", () => {
  const result = {
    id: "eval",
    index_run_id: "run",
    manifest_sha256: request.manifest_sha256,
    label_status: request.label_status,
    label_version: "v1",
    label_author: "Synthetic annotator",
    answer_evaluation: "NOT RUN",
    records: [
      {
        query_id: "q",
        group: "test",
        strategy: "dense",
        status: "error",
        ranked_ids: [],
        error_code: "provider_down",
        metrics: null,
      },
    ],
  } as EvaluationResult;
  const csv = evaluationCsv(result, request);
  expect(csv.startsWith("\uFEFF")).toBe(true);
  expect(csv).toContain('"\'=SUM(A1)"');
  expect(csv).toContain('"provider_down","","","",""');
  expect(csv).toContain('"NOT RUN"');
  expect(csvCell('a,"b"\nc')).toBe('"a,""b""\nc"');
});
