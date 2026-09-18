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
  metadata_info?: Record<string, unknown>;
  created_at: string;
  completed_at?: string;
}

export interface EvaluationRunRequest {
  assistant_code: string;
  dataset_id: string;
  sample_size?: number;
}

export interface GapInboxItem {
  id: string;
  question: string;
  assistant_code: string;
  assistant_name: string;
  reason: string;
  frequency: number;
  timestamp: string;
  status: "pending" | "resolved";
}
