import assert from "node:assert/strict";
import { test } from "node:test";
import type { KnowledgeBinding, VectorLoadState } from "@/types/knowledge";
import {
  canPublishSelectedSources,
  canPublishSources,
  getSelectedPublishItems,
  getSelectedReviewBlockers,
  getSourceVectorState,
} from "./vector-workflow";

const source = {
  id: "source",
  status: "active",
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

test("selected publication ignores unindexed/unreviewed unselected sources", () => {
  const unselected = {
    ...source,
    id: "other",
    source_status: "review_required",
    requires_structured_review: true,
  };
  const targets = [{ binding_id: source.id, source_revision_id: "md" }];
  assert.equal(
    canPublishSelectedSources(
      [source, unselected],
      targets,
      "gen",
      undefined,
      ready,
    ),
    true,
  );
  assert.deepEqual(getSelectedPublishItems([source], targets, "gen", ready), [
    { ...targets[0], index_revision_id: "index" },
  ]);
  assert.equal(
    canPublishSelectedSources(
      [source],
      [{ ...targets[0], source_revision_id: "changed" }],
      "gen",
      "gen",
      ready,
    ),
    false,
  );
  assert.equal(
    canPublishSelectedSources(
      [{ ...source, requires_structured_review: true }],
      targets,
      "gen",
      "gen",
      ready,
    ),
    false,
  );
});

test("selected publication preserves serving sources but generation switch must cover them", () => {
  const other = {
    ...source,
    id: "other",
    active_index_revision_id: "old-index",
  };
  const targets = [{ binding_id: source.id, source_revision_id: "md" }];
  assert.equal(
    canPublishSelectedSources([source, other], targets, "gen", "gen", ready),
    true,
  );
  assert.equal(
    canPublishSelectedSources(
      [source, other],
      targets,
      "gen",
      "old-gen",
      ready,
    ),
    false,
  );
  assert.equal(
    canPublishSelectedSources([source], [], "gen", "gen", ready),
    false,
  );
});

test("review blockers are limited to the selected vector targets", () => {
  const blockers = Array.from({ length: 8 }, (_, index) => ({
    ...source,
    id: `source-${index + 1}`,
    active_source_revision_id: `revision-${index + 1}`,
    requires_structured_review: true,
  })) as KnowledgeBinding[];

  assert.deepEqual(
    getSelectedReviewBlockers(blockers, ["source-1"]).map((item) => item.id),
    ["source-1"],
  );
});

test("busy embedding stays pending and cannot publish", () => {
  const waiting: VectorLoadState = {
    indexes: [],
    jobs: [
      {
        id: "job",
        status: "running",
        phase: "waiting_embedding",
        progress: 35,
        payload: {
          binding_id: "source",
          generation_id: "gen",
          source_revision_id: "md",
        },
      },
    ],
  };
  assert.equal(
    getSourceVectorState(source, "gen", waiting).label,
    "Chờ embedding",
  );
  assert.equal(getSourceVectorState(source, "gen", waiting).isPending, true);
  assert.equal(canPublishSources([source], "gen", waiting), false);
});

test("paused source is not serving and does not block publishing active sources", () => {
  const paused = {
    ...source,
    id: "paused",
    status: "paused",
  } as KnowledgeBinding;
  assert.equal(
    getSourceVectorState(paused, "gen", ready).label,
    "Đã ngừng dùng",
  );
  assert.equal(getSourceVectorState(paused, "gen", ready).isReady, false);
  assert.equal(canPublishSources([paused], "gen", ready), false);
  assert.equal(canPublishSources([source, paused], "gen", ready), true);
});

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
    canPublishSources(
      [{ ...source, requires_structured_review: true }],
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
