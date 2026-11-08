import assert from "node:assert/strict";
import { test } from "vitest";
import {
  hasActiveSourceTask,
  isSourceSummaryKey,
  summaryKeys,
} from "../src/features/knowledge/summary-queries.ts";
import type { SourceSummaryResponse } from "../src/features/knowledge/summary-types.ts";

const SESSION = 7;
const WORKSPACE = "workspace-a";
const COLLECTION = "collection-a";
const SOURCE = "source-a";

function buildSummary(input: {
  activeRunId?: string | null;
  processingStatuses?: string[];
  compilationStatuses?: string[];
}): SourceSummaryResponse {
  return {
    active_run_id: input.activeRunId ?? null,
    processing_runs: (input.processingStatuses ?? []).map((status) => ({
      status,
    })),
    derivations: (input.compilationStatuses ?? []).map(
      (compilation_status) => ({ compilation_status }),
    ),
  } as unknown as SourceSummaryResponse;
}

test("source summary keys separate revisions and page limits", () => {
  const base = summaryKeys.sourceBase(SESSION, WORKSPACE, COLLECTION, SOURCE);
  const first = summaryKeys.source(SESSION, WORKSPACE, COLLECTION, SOURCE, {
    revisionId: "revision-1",
    runsLimit: 10,
    derivationsLimit: 20,
  });
  const second = summaryKeys.source(SESSION, WORKSPACE, COLLECTION, SOURCE, {
    revisionId: "revision-2",
    runsLimit: 10,
    derivationsLimit: 20,
  });
  assert.deepEqual(first.slice(0, base.length), [...base]);
  assert.notDeepEqual(first, second);
});

test("document summary keys never collide with source summaries", () => {
  const source = summaryKeys.sourceBase(SESSION, WORKSPACE, COLLECTION, SOURCE);
  const document = summaryKeys.documentBase(
    SESSION,
    WORKSPACE,
    COLLECTION,
    "document-a",
  );
  assert.notDeepEqual(source, document);
  assert.deepEqual(
    summaryKeys
      .document(SESSION, WORKSPACE, COLLECTION, "document-a", {
        page: 2,
        pageSize: 20,
      })
      .slice(0, document.length),
    [...document],
  );
});

test("lineage invalidation matches every source in one collection only", () => {
  const params = { revisionId: "revision-1" };
  const sourceA = summaryKeys.source(
    SESSION,
    WORKSPACE,
    COLLECTION,
    "source-a",
    params,
  );
  const sourceB = summaryKeys.source(
    SESSION,
    WORKSPACE,
    COLLECTION,
    "source-b",
    params,
  );
  const document = summaryKeys.document(
    SESSION,
    WORKSPACE,
    COLLECTION,
    "document-a",
    { page: 1, pageSize: 20 },
  );
  assert.equal(
    isSourceSummaryKey(sourceA, SESSION, WORKSPACE, COLLECTION),
    true,
  );
  assert.equal(
    isSourceSummaryKey(sourceB, SESSION, WORKSPACE, COLLECTION),
    true,
  );
  assert.equal(
    isSourceSummaryKey(document, SESSION, WORKSPACE, COLLECTION),
    false,
  );
  assert.equal(
    isSourceSummaryKey(sourceA, SESSION, "workspace-b", COLLECTION),
    false,
  );
  assert.equal(
    isSourceSummaryKey(sourceA, SESSION, WORKSPACE, "collection-b"),
    false,
  );
});

test("a source summary is idle when every task reached a terminal state", () => {
  assert.equal(hasActiveSourceTask(undefined), false);
  assert.equal(
    hasActiveSourceTask(
      buildSummary({
        processingStatuses: ["completed", "failed", "cancelled", "uncertain"],
        compilationStatuses: ["completed", "failed", "cancelled"],
      }),
    ),
    false,
  );
});

test("a source summary keeps polling while any real task can still change it", () => {
  assert.equal(
    hasActiveSourceTask(buildSummary({ activeRunId: "run-1" })),
    true,
  );
  assert.equal(
    hasActiveSourceTask(buildSummary({ processingStatuses: ["running"] })),
    true,
  );
  assert.equal(
    hasActiveSourceTask(buildSummary({ compilationStatuses: ["queued"] })),
    true,
  );
});
