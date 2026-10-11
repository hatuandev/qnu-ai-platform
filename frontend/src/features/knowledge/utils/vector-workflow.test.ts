import assert from "node:assert/strict";
import { test } from "node:test";
import type { KnowledgeBinding, VectorLoadState } from "@/types/knowledge";
import { canPublishSources, getSourceVectorState } from "./vector-workflow";

const source = {
  id: "source",
  active_source_revision_id: "md",
  source_status: "ready",
} as KnowledgeBinding;
const ready: VectorLoadState = {
  jobs: [],
  indexes: [
    {
      id: "index",
      binding_id: "source",
      source_revision_v2_id: "md",
      vector_generation_id: "gen",
      chunk_count: 3,
      status: "ready",
    },
  ],
};

test("Markdown ready is not vector ready", () => {
  assert.equal(getSourceVectorState(source, "gen").isReady, false);
  assert.equal(canPublishSources([source], "gen"), false);
  assert.equal(canPublishSources([], "gen", ready), false);
});
test("only the same Markdown revision and embedding generation can publish", () => {
  assert.equal(canPublishSources([source], "gen", ready), true);
  assert.equal(canPublishSources([source], "other", ready), false);
  assert.equal(
    canPublishSources(
      [{ ...source, active_source_revision_id: "new" }],
      "gen",
      ready,
    ),
    false,
  );
  assert.equal(
    canPublishSources(
      [{ ...source, source_status: "review_required" }],
      "gen",
      ready,
    ),
    false,
  );
  assert.equal(
    canPublishSources([source, { ...source, id: "not-indexed" }], "gen", ready),
    false,
  );
});
test("worker status and failure are truthful; ready is not published", () => {
  const job = {
    id: "job",
    status: "queued",
    progress: 0,
    error: "offline",
    payload: {
      binding_id: "source",
      generation_id: "gen",
      source_revision_id: "md",
    },
  };
  assert.equal(
    getSourceVectorState(source, "gen", { ...ready, jobs: [job] }).label,
    "Chờ worker",
  );
  assert.equal(
    canPublishSources([source], "gen", { ...ready, jobs: [job] }),
    false,
  );
  assert.equal(
    getSourceVectorState(source, "gen", {
      jobs: [{ ...job, status: "failed" }],
      indexes: [],
    }).error,
    "offline",
  );
  assert.equal(
    getSourceVectorState(source, "gen", ready).label,
    "Đã nạp · Chờ xuất bản",
  );
  assert.equal(
    getSourceVectorState(
      { ...source, active_index_revision_id: "index" },
      "gen",
      ready,
    ).label,
    "Đang phục vụ chatbot",
  );
});
