import type { SourceSummaryResponse } from "@/api/knowledge/types";
import type { DetectionResponse } from "@/api/ocr/requests";

export function spellingScope(
  summary: SourceSummaryResponse | undefined,
  preferredRunId?: string | null,
) {
  const runId =
    preferredRunId ??
    summary?.active_run_id ??
    summary?.derivations[0]?.ocr_run_id;
  const run = summary?.processing_runs.find((item) => item.id === runId);
  if (run?.status !== "completed") return null;
  return {
    runId: run.id,
    revisionId: run.revision_id,
    textVersion: run.latest_text_version?.version ?? 0,
  };
}

export function preferredSpellingCheck(
  checks: DetectionResponse[] | undefined,
) {
  return (
    checks?.find((check) => check.total_evidence_count != null) ?? checks?.[0]
  );
}

export function spellingCoverage(check: DetectionResponse) {
  const checked = new Set(check.checked_evidence_ids).size;
  const total = check.total_evidence_count ?? null;
  return {
    checked,
    total,
    complete:
      check.status === "completed" && total !== null && checked === total,
  };
}
