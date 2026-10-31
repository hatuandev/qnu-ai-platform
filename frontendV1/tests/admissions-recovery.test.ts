import { describe, expect, it } from "vitest";
import {
  canRecoverAdmissionCompilation,
  canRecoverTruncatedReview,
  decideCompilationRecovery,
  invalidReviewCanBeReplanned,
  PLANNER_VERSION,
  REVIEW_PLANNER_VERSION,
  recoveryAllowed,
  replaceCompletedReview,
  reviewNeedsReplacement,
} from "../e2e/stages/admissions-recovery";

const failed = {
  status: "failed",
  error_code: "chat_output_truncated",
  provider_id: "provider",
};

it("requires a definite invalid reply under the old reference contract to replan", () => {
  const review = {
    status: "uncertain",
    error_code: "compilation_review_invalid",
  };
  expect(
    invalidReviewCanBeReplanned(review, [
      { status: "failed" },
      { status: "completed" },
    ]),
  ).toBe(true);
  for (const status of ["running", "received", "uncertain"]) {
    expect(invalidReviewCanBeReplanned(review, [{ status }])).toBe(false);
  }
  expect(invalidReviewCanBeReplanned(review, [])).toBe(false);
  expect(
    invalidReviewCanBeReplanned(
      { ...review, trace: { reference_contract_version: 2 } },
      [{ status: "failed" }],
    ),
  ).toBe(false);
  expect(
    invalidReviewCanBeReplanned(
      { ...review, error_code: "chat_provider_uncertain" },
      [{ status: "failed" }],
    ),
  ).toBe(false);
});

it("replaces only an explicitly opted-in completed unpublished legacy review", () => {
  const old = { status: "completed" };
  expect(replaceCompletedReview(old, true, false)).toBe(true);
  expect(replaceCompletedReview(old, false, false)).toBe(false);
  expect(replaceCompletedReview(old, true, true)).toBe(false);
  expect(replaceCompletedReview({ status: "running" }, true, false)).toBe(
    false,
  );
  expect(replaceCompletedReview({ status: "uncertain" }, true, false)).toBe(
    false,
  );
  expect(
    replaceCompletedReview(
      {
        status: "completed",
        trace: {
          context_resolution_version: 2,
          literal_check_version: 1,
          review_concurrency: 2,
          reference_contract_version: 2,
        },
      },
      true,
      false,
    ),
  ).toBe(false);
});

describe("admissions compilation recovery", () => {
  it("allows a known truncation once using configured output capacity", () => {
    expect(canRecoverAdmissionCompilation(failed, {}, "provider", 16384)).toBe(
      true,
    );
  });
  it("keeps uncertain, other failures and other providers untouched", () => {
    expect(
      canRecoverAdmissionCompilation(
        { ...failed, status: "uncertain" },
        {},
        "provider",
        16384,
      ),
    ).toBe(false);
    expect(
      canRecoverAdmissionCompilation(
        { ...failed, error_code: "quota_exceeded" },
        {},
        "provider",
        16384,
      ),
    ).toBe(false);
    expect(canRecoverAdmissionCompilation(failed, {}, "another", 16384)).toBe(
      false,
    );
  });
  it("does not loop a recovery or replace reviewed/published work", () => {
    for (const publication of [
      { compilationRecoveryOf: "old" },
      { review: "review" },
      { version: "version" },
    ]) {
      expect(
        canRecoverAdmissionCompilation(failed, publication, "provider", 16384),
      ).toBe(false);
    }
  });
  it("requires a usable, explicit provider budget", () => {
    for (const limit of [undefined, null, 4096, 8192.5, Number.NaN, Infinity]) {
      expect(
        canRecoverAdmissionCompilation(failed, {}, "provider", limit),
      ).toBe(false);
    }
  });
});

describe("rerun decision for an existing compilation run", () => {
  it("replans completed old drafts only before publication; recover opt-in is still required", () => {
    const old = {
      status: "completed",
      planner_version: "qnu.compiler.plan/v4",
    };
    expect(decideCompilationRecovery(old, {}, "provider", 16384)).toEqual({
      action: "new_run",
      reason: "stale_planner",
    });
    expect(
      decideCompilationRecovery(
        old,
        { version: "published" },
        "provider",
        16384,
      ),
    ).toEqual({ action: "wait" });
    expect(recoveryAllowed(undefined)).toBe(false);
  });
  it("waits for a live run and reuses a completed one", () => {
    for (const status of ["queued", "running", "dispatched", "completed"]) {
      expect(
        decideCompilationRecovery({ status }, {}, "provider", 16384),
      ).toEqual({ action: "wait" });
    }
  });
  it("raises the ceiling only for the truncation it can attribute", () => {
    expect(decideCompilationRecovery(failed, {}, "provider", 16384)).toEqual({
      action: "raise_output",
      output: 16384,
    });
  });
  it("replaces an uncertain run with a new one instead of replaying a part", () => {
    expect(
      decideCompilationRecovery(
        { status: "uncertain", planner_version: PLANNER_VERSION },
        {},
        "provider",
        undefined,
      ),
    ).toEqual({ action: "new_run", reason: "unresumable_parts" });
  });
  it("replaces a run planned under another planner version", () => {
    expect(
      decideCompilationRecovery(
        { status: "failed", planner_version: "qnu.compiler.plan/v3" },
        {},
        "provider",
        undefined,
      ),
    ).toEqual({ action: "new_run", reason: "stale_planner" });
  });
  it("treats a single stopped part as unresumable", () => {
    expect(
      decideCompilationRecovery(
        {
          status: "failed",
          planner_version: PLANNER_VERSION,
          parts: [{ status: "completed" }, { status: "uncertain" }],
        },
        {},
        "provider",
        undefined,
      ),
    ).toEqual({ action: "new_run", reason: "unresumable_parts" });
  });
  it("needs an explicit opt-in before a run is replaced", () => {
    expect(recoveryAllowed("1")).toBe(true);
    for (const value of [undefined, "true", "0", ""])
      expect(recoveryAllowed(value)).toBe(false);
  });
});

describe("review replacement", () => {
  const changed =
    "POST /reviews: HTTP 409, code=compilation_review_provider_changed";
  it("replaces a review only for a changed model contract with opt-in", () => {
    expect(reviewNeedsReplacement(changed, true)).toBe(true);
    expect(reviewNeedsReplacement(changed, false)).toBe(false);
  });
  it("never replaces a review for any other failure", () => {
    for (const message of [
      "POST /reviews: HTTP 409, code=compilation_review_segment_too_large",
      "POST /reviews: HTTP 409, code=compilation_review_interrupted",
      "POST /reviews: HTTP 422, code=compilation_review_segment_too_large",
      "POST /reviews: HTTP 503, code=storage_unavailable",
    ]) {
      expect(reviewNeedsReplacement(message, true)).toBe(false);
    }
  });
  it("recovers a legacy unsegmented truncated review at 4096 under review.plan/v2 without touching uncertain reviews", () => {
    expect(
      canRecoverTruncatedReview(
        {
          status: "failed",
          error_code: "chat_output_truncated",
          provider_id: "prv_chat",
          trace: { max_output_tokens: 4096 },
        },
        "prv_chat",
        4096,
      ),
    ).toEqual({ recover: true, suffix: "-plan-v2" });
    expect(
      canRecoverTruncatedReview(
        {
          status: "failed",
          error_code: "chat_output_truncated",
          provider_id: "prv_chat",
          trace: {
            max_output_tokens: 4096,
            segmentation: { planner_version: REVIEW_PLANNER_VERSION },
          },
        },
        "prv_chat",
        4096,
      ),
    ).toEqual({ recover: false, suffix: "" });
    expect(
      canRecoverTruncatedReview(
        {
          status: "uncertain",
          error_code: "chat_provider_uncertain",
          provider_id: "prv_chat",
          trace: { max_output_tokens: 4096 },
        },
        "prv_chat",
        4096,
      ),
    ).toEqual({ recover: false, suffix: "" });
  });
});
