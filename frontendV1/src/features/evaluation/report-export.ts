import type { EvaluationRequest, EvaluationResult } from "./types";

/** Quote every cell and neutralize spreadsheet formula prefixes, including leading controls. */
export function csvCell(value: unknown): string {
  let text = value === null || value === undefined ? "" : String(value);
  const significant = [...text].find(
    (character) => character.charCodeAt(0) > 32 && character.trim() !== "",
  );
  if (significant && "=+@-".includes(significant)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}
export function evaluationCsv(
  result: EvaluationResult,
  request: EvaluationRequest,
) {
  const rows: unknown[][] = [
    [
      "evaluation_id",
      "index_run_id",
      "manifest_sha256",
      "label_status",
      "label_version",
      "label_author",
      "query_id",
      "query",
      "group",
      "strategy",
      "status",
      "error_code",
      "hit_at_k",
      "annotated_recall_at_k",
      "mrr_at_k",
      "annotated_precision_at_k",
      "empty_gold",
      "ranked_ids",
      "answer_evaluation",
      "document_ids",
    ],
  ];
  for (const record of result.records)
    rows.push([
      result.id,
      result.index_run_id,
      result.manifest_sha256,
      result.label_status,
      result.label_version,
      result.label_author,
      record.query_id,
      request.queries.find((q) => q.id === record.query_id)?.query,
      record.group,
      record.strategy,
      record.status,
      record.error_code,
      record.metrics?.hit_at_k,
      record.metrics?.annotated_recall_at_k,
      record.metrics?.mrr_at_k,
      record.metrics?.annotated_precision_at_k,
      record.metrics?.empty_gold,
      record.ranked_ids.join(" | "),
      result.answer_evaluation,
      request.queries
        .find((q) => q.id === record.query_id)
        ?.document_ids?.join(" | ") ?? "",
    ]);
  return `\uFEFF${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}`;
}
