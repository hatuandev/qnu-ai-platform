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
  collection_id: string;
  is_active: boolean;
  tenant_id: string;
  sample_questions: string[];
  config: AssistantLifecycleConfig;
  created_at: string;
  updated_at: string;
}

export type AssistantDetailItem = AssistantItem;
