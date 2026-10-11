import assert from "node:assert/strict";
import test from "node:test";
import {
  resolveRetryAction,
  resolveSourceActionBanner,
} from "./retry-decision";

test("resolveSourceActionBanner: 1. failed + awaiting_publish -> 'failed'", () => {
  const banner = resolveSourceActionBanner({
    status: "failed",
    failed_count: 1,
    awaiting_publish_count: 2,
    publishable_count: 2,
    needs_build_count: 3,
  });
  assert.equal(banner, "failed");
});

test("resolveSourceActionBanner: 2. review_required không failed -> 'review'", () => {
  const banner = resolveSourceActionBanner({
    status: "review_required",
    failed_count: 0,
    awaiting_publish_count: 2,
    publishable_count: 2,
    needs_build_count: 1,
  });
  assert.equal(banner, "review");
});

test("resolveSourceActionBanner: 3. needs_build_count > 0 -> 'updates'", () => {
  const banner = resolveSourceActionBanner({
    status: "ready",
    failed_count: 0,
    awaiting_publish_count: 0,
    publishable_count: 0,
    needs_build_count: 4,
  });
  assert.equal(banner, "updates");
});

test("resolveSourceActionBanner: 4. updates_available -> 'updates'", () => {
  const banner = resolveSourceActionBanner({
    status: "updates_available",
    failed_count: 0,
    awaiting_publish_count: 0,
    publishable_count: 0,
    needs_build_count: 0,
  });
  assert.equal(banner, "updates");
});

test("resolveSourceActionBanner: 5. ready -> 'none'", () => {
  const banner = resolveSourceActionBanner({
    status: "ready",
    failed_count: 0,
    awaiting_publish_count: 0,
    publishable_count: 0,
    needs_build_count: 0,
  });
  assert.equal(banner, "none");
});

test("resolveSourceActionBanner: 6. empty -> 'none'", () => {
  const banner = resolveSourceActionBanner({
    status: "empty",
    failed_count: 0,
    awaiting_publish_count: 0,
    publishable_count: 0,
    needs_build_count: 0,
  });
  assert.equal(banner, "none");
});

test("resolveSourceActionBanner: 7. pending -> 'none'", () => {
  const banner = resolveSourceActionBanner({
    status: "pending",
    failed_count: 0,
    awaiting_publish_count: 0,
    publishable_count: 0,
    needs_build_count: 0,
  });
  assert.equal(banner, "none");
});

test("resolveSourceActionBanner: Độ ưu tiên thứ bậc failed > review > updates > none", () => {
  // Khi vừa có failed, vừa có awaiting_publish và needs_build: failed thắng
  assert.equal(
    resolveSourceActionBanner({
      status: "failed",
      failed_count: 1,
      awaiting_publish_count: 5,
      needs_build_count: 10,
    }),
    "failed",
  );

  // Khi không failed, có awaiting_publish và needs_build: review thắng
  assert.equal(
    resolveSourceActionBanner({
      status: "review_required",
      failed_count: 0,
      awaiting_publish_count: 5,
      needs_build_count: 10,
    }),
    "review",
  );

  // Khi không failed, không staging, nhưng có needs_build: updates thắng
  assert.equal(
    resolveSourceActionBanner({
      status: "ready",
      failed_count: 0,
      awaiting_publish_count: 0,
      needs_build_count: 2,
    }),
    "updates",
  );

  // Khi null / undefined: none
  assert.equal(resolveSourceActionBanner(null), "none");
  assert.equal(resolveSourceActionBanner(undefined), "none");
});

test("resolveRetryAction: Failed + staging -> retry action là 'publish'", () => {
  const actionWithPublishable = resolveRetryAction({
    publishable_count: 2,
    awaiting_publish_count: 0,
    needs_build_count: 1,
  });
  assert.equal(actionWithPublishable, "publish");

  const actionWithAwaiting = resolveRetryAction({
    publishable_count: 0,
    awaiting_publish_count: 1,
    needs_build_count: 0,
  });
  assert.equal(actionWithAwaiting, "publish");
});

test("resolveRetryAction: Failed không staging -> retry action là 'sync'", () => {
  const action = resolveRetryAction({
    publishable_count: 0,
    awaiting_publish_count: 0,
    needs_build_count: 2,
  });
  assert.equal(action, "sync");
  assert.equal(resolveRetryAction(null), "sync");
  assert.equal(resolveRetryAction({}), "sync");
});
