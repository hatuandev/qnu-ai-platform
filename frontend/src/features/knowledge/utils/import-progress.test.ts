import assert from "node:assert/strict";
import { test } from "node:test";
import { getBatchProgress, getItemProgress } from "./import-progress";

test("one finished document is 100 while its neighbor keeps its own progress", () => {
  assert.equal(getItemProgress({ status: "succeeded", progress: 90 }), 100);
  assert.equal(getItemProgress({ status: "processing", progress: 50 }), 50);
  assert.equal(
    getBatchProgress([
      { status: "succeeded" },
      { status: "processing", progress: 50 },
    ]),
    75,
  );
});
test("failure or review is not success; queued retries restart at zero", () => {
  assert.equal(getItemProgress({ status: "failed", progress: 75 }), 75);
  assert.equal(
    getItemProgress({ status: "review_required", progress: 75 }),
    75,
  );
  assert.equal(getItemProgress({ status: "queued", progress: 75 }), 0);
  assert.equal(getBatchProgress([]), 0);
});
