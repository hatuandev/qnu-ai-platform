/**
 * Decide how a rerun treats the compilation run recorded in the checkpoint.
 *
 * Rules that must not be relaxed:
 * - A live run is never replaced; the rerun only waits for it.
 * - A part that ended `uncertain` is never replayed: the provider may have been
 *   charged and may still be generating, so the call is not idempotent.
 * - Replacing a terminal run creates a new run from the completed OCR source and
 *   keeps the old one in history; it needs an explicit operator opt-in.
 */

/** A run planned by an older planner cannot be resumed under the current contract. */
export const PLANNER_VERSION = "qnu.compiler.plan/v5";
export const REVIEW_PLANNER_VERSION = "qnu.compiler.review.plan/v2";

export type Decision =
  | { action: "wait" }
  | { action: "raise_output"; output: number }
  | { action: "new_run"; reason: "stale_planner" | "unresumable_parts" };

export type RunFacts = {
  status: string;
  error_code?: string | null;
  provider_id?: string | null;
  planner_version?: string | null;
  parts?: { status: string }[];
};

const ACTIVE = new Set(["queued", "running", "dispatched"]);
const STOPPED_PART = new Set(["failed", "uncertain", "claim_lost", "missing"]);

/**
 * The output ceiling may be raised once per publication, and only when the run
 * itself was cut short by that ceiling: a replanned run must not consume it.
 */
export function canRecoverAdmissionCompilation(
  run: {
    status: string;
    error_code?: string | null;
    provider_id?: string | null;
  },
  publication: {
    compilationRecoveryOf?: string;
    review?: string;
    version?: string;
  },
  providerId: string | undefined,
  outputLimit: number | null | undefined,
): outputLimit is number {
  return (
    run.status === "failed" &&
    run.error_code === "chat_output_truncated" &&
    !!providerId &&
    run.provider_id === providerId &&
    !publication.compilationRecoveryOf &&
    !publication.review &&
    !publication.version &&
    typeof outputLimit === "number" &&
    Number.isSafeInteger(outputLimit) &&
    outputLimit >= 8192
  );
}

export function decideCompilationRecovery(
  facts: RunFacts,
  publication: {
    compilationRecoveryOf?: string;
    review?: string;
    version?: string;
  },
  providerId: string | undefined,
  outputLimit: number | null | undefined,
): Decision {
  if (
    facts.status === "completed" &&
    facts.planner_version &&
    facts.planner_version !== PLANNER_VERSION &&
    !publication.version
  ) {
    return { action: "new_run", reason: "stale_planner" };
  }
  if (ACTIVE.has(facts.status) || facts.status === "completed")
    return { action: "wait" };
  if (
    canRecoverAdmissionCompilation(facts, publication, providerId, outputLimit)
  ) {
    return { action: "raise_output", output: outputLimit };
  }
  if (facts.planner_version !== PLANNER_VERSION) {
    return { action: "new_run", reason: "stale_planner" };
  }
  if (
    facts.status === "uncertain" ||
    (facts.parts ?? []).some((part) => STOPPED_PART.has(part.status))
  ) {
    return { action: "new_run", reason: "unresumable_parts" };
  }
  // Any other terminal state has no safe move here; the caller surfaces it rather
  // than guessing or silently replacing the run.
  return { action: "wait" };
}

/** True only when the operator asked for the replacement on this invocation. */
export function recoveryAllowed(value: string | undefined): boolean {
  return value === "1";
}

export function replaceCompletedReview(
  review: { status: string; trace?: Record<string, unknown> },
  allowed: boolean,
  published: boolean,
): boolean {
  return (
    allowed &&
    !published &&
    review.status === "completed" &&
    (review.trace?.context_resolution_version !== 2 ||
      review.trace?.literal_check_version !== 1 ||
      review.trace?.review_concurrency !== 2 ||
      review.trace?.reference_contract_version !== 2)
  );
}

/**
 * A stopped review planned under another model configuration cannot be resumed:
 * the parts were planned for one exact request contract and the provider now
 * answers differently. The stored review stays untouched in history; the caller
 * may start one new review under a new idempotency key, and only when the
 * operator opted in. Nothing else is replaced automatically.
 */
export function reviewNeedsReplacement(
  message: string,
  allowed: boolean,
): boolean {
  return (
    allowed && message.includes("code=compilation_review_provider_changed")
  );
}

export function invalidReviewCanBeReplanned(
  review: {
    status: string;
    error_code?: string | null;
    trace?: Record<string, unknown>;
  },
  parts: { status: string }[],
): boolean {
  return (
    ["failed", "uncertain"].includes(review.status) &&
    review.error_code === "compilation_review_invalid" &&
    review.trace?.reference_contract_version !== 2 &&
    parts.length > 0 &&
    parts.every((part) =>
      ["pending", "completed", "failed"].includes(part.status),
    )
  );
}

export function canRecoverTruncatedReview(
  review:
    | {
        status: string;
        error_code?: string | null;
        provider_id?: string | null;
        trace?: {
          max_output_tokens?: number;
          segmentation?: { planner_version?: string | null } | null;
        };
      }
    | undefined,
  providerId: string | undefined,
  modelLimit: number | null | undefined,
): { recover: boolean; suffix: string } {
  if (
    review?.status !== "failed" ||
    review.error_code !== "chat_output_truncated" ||
    !providerId ||
    review.provider_id !== providerId
  ) {
    return { recover: false, suffix: "" };
  }
  const previousLimit = review.trace?.max_output_tokens;
  if (
    typeof previousLimit === "number" &&
    typeof modelLimit === "number" &&
    previousLimit < modelLimit
  ) {
    return { recover: true, suffix: `-budget-${modelLimit}` };
  }
  if (review.trace?.segmentation?.planner_version !== REVIEW_PLANNER_VERSION) {
    return { recover: true, suffix: "-plan-v2" };
  }
  return { recover: false, suffix: "" };
}
