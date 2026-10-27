import type { DocumentSelection } from "@/features/knowledge/document-scope-picker";
import type { SearchHit } from "@/features/knowledge/index-types";
export type IndexManifest = {
  run_id: string;
  generation: number;
  chunks: { id: string; text_sha256: string }[];
  inputs: {
    document_id: string;
    version_id: string;
    publication_decision_id: string;
  }[];
};
export type LabelStatus = "draft_needs_human_check" | "human_reviewed";
export type EvaluationQuestionDraft = {
  id: string;
  query: string;
  group: string;
  gold: SearchHit[];
  documents: DocumentSelection[];
};
export type EvaluationRequest = {
  index_run_id: string;
  manifest_sha256: string;
  label_version: string;
  label_author: string;
  label_status: LabelStatus;
  queries: {
    id: string;
    query: string;
    group: string;
    gold_chunk_ids: string[];
    document_ids: string[] | null;
  }[];
  top_k: number;
  candidate_k: number;
  include_rerank: boolean;
  rerank_provider_id: string | null;
};
export type MetricValues = {
  hit_at_k: number | null;
  annotated_recall_at_k: number | null;
  mrr_at_k: number | null;
  annotated_precision_at_k: number | null;
};
export type EvaluationRecord = {
  query_id: string;
  group: string;
  strategy: string;
  status: string;
  ranked_ids: string[];
  metrics:
    | (MetricValues & {
        empty_gold: boolean;
        retrieved_count: number;
        answer_correctness: null;
        answer_groundedness: null;
      })
    | null;
  error_code?: string;
  candidate_trace?: Record<string, unknown>;
};
export type EvaluationResult = {
  schema_version: string;
  id: string;
  index_run_id: string;
  manifest_sha256: string;
  label_version: string;
  label_author: string;
  label_status: LabelStatus;
  top_k: number;
  candidate_k: number;
  records: EvaluationRecord[];
  summary: Record<
    string,
    {
      expected: number;
      completed: number;
      errors: number;
      completed_only_metrics: MetricValues;
      acceptance: string;
    }
  >;
  answer_evaluation: "NOT RUN";
  publication_approval: false;
  timing_boundary: string;
};
