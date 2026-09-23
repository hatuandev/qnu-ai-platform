/** Types for Assistants / Chatbots */

export interface AssistantLifecycleConfig {
  sample_questions: string[];
  persona_scope: {
    persona: string;
    allowed_topics: string[];
    out_of_scope_policy: string;
  };
  knowledge_policy: {
    chunking_strategy: "ClauseBasedChunker" | "SemanticChunker";
    require_structured_facts: boolean;
    retrieval_limit: number;
  };
  model_policy: {
    primary_model: string;
    fallback_model: string;
    temperature: number;
    max_tokens: number;
    thinking_budget?: number;
  };
  guardrails: {
    block_prompt_injection: boolean;
    mask_pii: boolean;
    require_grounded_answer: boolean;
    protect_system_prompt: boolean;
    no_answer_message: string;
  };
  tools: {
    enabled_tools: string[];
    human_approval_required: boolean;
  };
  output_policy: {
    formats: Array<"markdown" | "table" | "checklist" | "timeline">;
    require_citations: boolean;
    citation_format: string;
  };
  evaluation_policy: {
    faithfulness_threshold: number;
    answer_relevance_threshold: number;
    context_precision_threshold: number;
  };
}

export interface AssistantItem {
  id: string;
  code: string;
  name: string;
  description: string;
  avatar_url?: string | null;
  category: string;
  system_prompt: string;
  workflow_id: string;
  published_workflow_version_id?: string | null;
  workflow_ownership?: "private" | "shared";
  collection_id: string;
  is_active: boolean;
  tenant_id: string;
  sample_questions: string[];
  config: AssistantLifecycleConfig;
  created_at: string;
  updated_at: string;
}

export type AssistantDetailItem = AssistantItem;

export interface ReadinessCheckItem {
  category: "knowledge" | "model" | "tools" | "guardrails" | "evaluation";
  name: string;
  status: "passed" | "failed" | "warning";
  score: number;
  message: string;
  details?: Record<string, unknown>;
}

export interface AssistantReadinessResponse {
  assistant_code: string;
  assistant_name: string;
  is_ready_for_publish: boolean;
  overall_readiness_score: number;
  checks: ReadinessCheckItem[];
  blockers: string[];
  warnings: string[];
}

export interface AssistantCloneRequest {
  new_code: string;
  new_name: string;
  new_description?: string;
  target_collection_id?: string;
  fork_workflow?: boolean;
}

export interface AssistantForkWorkflowResponse {
  assistant_id: string;
  assistant_code: string;
  previous_workflow_id: string;
  new_workflow_id: string;
  new_workflow_name: string;
  ownership: "private" | "shared";
  message: string;
}

export interface AssistantPublishResponse {
  assistant_code: string;
  assistant_name: string;
  is_active: boolean;
  readiness_score: number;
  published_at: string;
  message: string;
}

export interface AssistantVersionItem {
  id: string;
  assistant_id: string;
  assistant_code: string;
  version_number: string;
  change_summary: string;
  snapshot_data: Record<string, unknown>;
  created_by: string;
  created_at: string;
}

export interface AssistantRollbackResponse {
  assistant_code: string;
  restored_version: string;
  current_version: string;
  message: string;
}
