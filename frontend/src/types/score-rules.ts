export interface ScoreCell {
  block_id: string;
  fact_id: string;
  attribute: string;
  value: string;
}

export interface ScoreRuleDefinition {
  id: string;
  binding_id: string;
  index_revision_id: string;
  source_revision_id: string;
  canonical_hash: string;
  year: number;
  source_method: string;
  source_attribute: string;
  source_aliases: string[];
  target_method: string;
  target_attribute: string;
  base_combination: string;
  combination_context_attribute: string;
  mappings: {
    combination: string;
    base_combination: string;
    proof: ScoreCell;
  }[];
  points: { source: ScoreCell; target: ScoreCell }[];
  operation: "piecewise_linear";
  decimal_places: number;
  rounding: "ROUND_HALF_UP" | "ROUND_HALF_EVEN" | "ROUND_DOWN";
  rule_proofs: { block_id: string; quote: string }[];
}

export type ScoreRuleStatus = "draft" | "approved" | "active" | "revoked";
export type ScoreRuleAction = "approve" | "activate" | "deactivate" | "revoke";

export interface ScoreRuleRecord {
  definition: ScoreRuleDefinition;
  status: ScoreRuleStatus;
  created_by: string;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface ScoreRuleRegistry {
  version: number;
  items: ScoreRuleRecord[];
  audit: {
    rule_id: string;
    action: string;
    actor_id: string;
    at: string;
    reason: string;
    request_id: string;
  }[];
}

export interface ScorePreviewResult {
  status: "calculated" | "missing" | "clarify";
  is_preview: boolean;
  reason: string;
  message: string;
  result: string | null;
  formula: string | null;
  rounding: string | null;
  x1: string | null;
  x2: string | null;
  y1: string | null;
  y2: string | null;
  citations: {
    source_id: string;
    title: string;
    quote: string;
    page_number: number | null;
  }[];
}
