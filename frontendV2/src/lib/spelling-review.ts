import type { SourceSummaryResponse } from "@/api/knowledge/types";
import type { DetectionResponse } from "@/api/ocr/requests";

const USABLE_RUN_STATUSES = new Set(["completed", "completed_with_warnings"]);

export function spellingScope(
  summary: SourceSummaryResponse | undefined,
  preferredRunId?: string | null,
) {
  const runs = summary?.processing_runs ?? [];
  const runId =
    preferredRunId ??
    summary?.active_run_id ??
    summary?.derivations[0]?.ocr_run_id;
  const run = runId
    ? runs.find((item) => item.id === runId)
    : runs.find((item) => USABLE_RUN_STATUSES.has(item.status));
  if (!run || !USABLE_RUN_STATUSES.has(run.status)) return null;
  return {
    runId: run.id,
    revisionId: run.revision_id,
    textVersion: run.latest_text_version?.version ?? 0,
  };
}

export function currentSpellingCheck(
  checks: DetectionResponse[] | undefined,
  version: number | undefined,
) {
  if (!checks || version === undefined) return undefined;
  const relevant = checks.filter(
    (check) => check.version === version || check.reviewed_version === version,
  );
  return (
    relevant.find((check) => check.reviewed_at) ??
    relevant.find((check) => check.status === "completed") ??
    relevant.find((check) => check.status === "running") ??
    relevant[0]
  );
}

export function formatSpellingMoment(value: string) {
  const moment = new Date(value);
  if (Number.isNaN(moment.getTime())) return "";
  return moment.toLocaleString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  });
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

export function spellingPercent(checked: number, total: number | null) {
  if (!total || total <= 0) return null;
  return Math.min(100, Math.floor((checked / total) * 100));
}
