export interface SampleQuestionItem {
  id: string;
  text: string;
}

export interface AssistantEditForm {
  name: string;
  description: string;
  category: string;
  system_prompt: string;
  workflow_id: string;
  collection_id: string;
  sample_questions: SampleQuestionItem[];
  primary_model: string;
  fallback_model: string;
  temperature: number;
  max_tokens: number;
  thinking_budget: number;
  block_prompt_injection: boolean;
  mask_pii: boolean;
  require_grounded_answer: boolean;
  protect_system_prompt: boolean;
  human_approval_required: boolean;
  require_citations: boolean;
  no_answer_message: string;
}

export const CATEGORY_OPTIONS = [
  { value: "admissions", label: "Tuyển sinh & Hướng nghiệp" },
  { value: "academic", label: "Quy chế & Học vụ" },
  { value: "resources", label: "Thư viện & Học liệu Số" },
  { value: "administration", label: "Soạn thảo Văn bản NĐ 30" },
  { value: "examination", label: "Khảo thí & Đề thi Bloom" },
  { value: "general", label: "Hỗ trợ Đa năng" },
];
