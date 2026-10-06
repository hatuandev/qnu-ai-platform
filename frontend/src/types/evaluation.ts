/** Types for Continuous Evaluation (Ragas TM-08 Standard) & Knowledge Gaps */

export interface EvaluationMetrics {
  faithfulness: number;
  answer_relevance: number;
  context_precision: number;
  target_faithfulness: number;
  target_relevance: number;
  target_precision: number;
  total_evaluations?: number;
  last_evaluated_at?: string;
}

export interface EvaluationRunItem {
  id: string;
  dataset_id: string;
  assistant_code: string;
  status: string;
  total_cases: number;
  passed_cases: number;
  pass_rate: number;
  faithfulness_avg: number;
  answer_relevance_avg: number;
  context_precision_avg: number;
  meets_tm08_standard: boolean;
  evaluation_method?: string;
  metadata_info?: Record<string, unknown>;
  created_at: string;
  completed_at?: string;
}

export interface EvaluationResultItem {
  id: string;
  test_case_id: string;
  query: string;
  generated_answer: string;
  contexts: string[];
  faithfulness_score: number;
  answer_relevance_score: number;
  context_precision_score: number;
  is_hallucinated: boolean;
  is_refusal: boolean;
  passed_all_criteria: boolean;
  execution_path: string;
  reasoning?: string | null;
  ground_truth?: string | null;
}

export interface EvaluationRunDetail extends EvaluationRunItem {
  items: EvaluationResultItem[];
}

export interface EvaluationRunRequest {
  assistant_code: string;
  dataset_id: string;
  sample_size?: number;
  evaluation_method?: "heuristic" | "llm_judge";
}

export interface GapInboxItem {
  id: string;
  question: string;
  assistant_code: string;
  assistant_name: string;
  collection_id?: string;
  reason: string;
  frequency: number;
  timestamp: string;
  status: "pending" | "resolved" | "dismissed";
  resolution_notes?: string | null;
  resolved_by?: string | null;
}

export interface KnowledgeGapResolveRequest {
  status: "resolved" | "dismissed";
  resolution_notes?: string;
  resolved_by?: string;
}
