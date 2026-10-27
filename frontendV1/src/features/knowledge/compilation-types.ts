/**
 * Type contracts for Knowledge Compiler domain in frontendV1.
 * Matches backendV1 schemas from:
 * - qnu.domains.knowledge.compilation.schemas
 * - qnu.domains.knowledge.compilation.drafting
 * - qnu.domains.knowledge.compilation.review.schemas
 * - qnu.domains.knowledge.compilation.review.report
 * - qnu.domains.knowledge.compilation.workflow.schemas
 */

export type CompilationOrigin = "compiler" | "user_edit";

export type CompilationStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "uncertain"
  | "cancelled";

export type CompilationRunResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  generation: number;
  topic: string;
  status: CompilationStatus;
  provider_id: string;
  requested_by: string;
  requested_at: string;
  dispatched_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  attempt_count: number;
  error_code: string | null;
  input_sha256: string;
  usage_tokens: number | null;
  parent_run_id: string | null;
  origin: CompilationOrigin;
};

export type CompilationCreatedResponse = {
  run: CompilationRunResponse;
  created: boolean;
  dispatched: boolean;
};

export type CompilationRequestInput = {
  topic: string;
  ocr_run_ids: string[];
  provider_id?: string | null;
  max_output_tokens?: number | null;
  structured_output?: boolean;
  text_versions?: Record<string, number>;
  auto_review?: boolean;
  review_provider_id?: string | null;
  review_max_output_tokens?: number;
  review_structured_output?: boolean;
};

export type DraftParagraph = {
  text: string;
  citations: string[];
};

export type DraftSection = {
  heading: string;
  paragraphs: DraftParagraph[];
};

export type DraftContent = {
  title: string;
  sections: DraftSection[];
  unknowns: string[];
};

export type TableCell = {
  header: boolean;
  row_span: number;
  col_span: number;
  text: string;
};

export type LiteralTableEntry = {
  citation: string;
  page_number: number;
  table: {
    rows: TableCell[][];
  };
};

export type CitationDetail = {
  workspace_id: string;
  collection_id: string;
  source_id: string;
  revision_id: string;
  filename: string;
  content_type: string;
  evidence_id: string;
  canonical_sha256: string;
  manifest_sha256: string;
  page_number?: number;
  path?: string;
  artifact?: string;
  text_version?: {
    id: string;
    version: number;
    canonical_sha256: string;
    markdown_sha256: string;
  };
  original_artifact?: string;
  original_canonical_sha256?: string;
  [key: string]: unknown;
};

export type SourceSummary = {
  ocr_run_id: string;
  canonical_sha256: string;
  manifest_sha256: string;
  identity: {
    workspace_id: string;
    collection_id: string;
    source_id: string;
    revision_id: string;
    filename: string;
    content_type: string;
    [key: string]: unknown;
  };
  original_canonical_sha256?: string;
  text_version?: {
    id: string;
    version: number;
    canonical_sha256: string;
    markdown_sha256: string;
  };
};

export type DraftDocumentResponse = {
  schema_version: string;
  compilation_run_id: string;
  publication_status: string;
  requires_review: boolean;
  topic: string;
  title: string;
  sections: DraftSection[];
  unknowns: string[];
  citations: Record<string, CitationDetail>;
  source_tables: LiteralTableEntry[];
  sources: SourceSummary[];
  origin?: string;
  parent_run_id?: string | null;
  validation?: {
    schema: string;
    citation_membership: string;
    semantic_faithfulness: string;
  };
};

export type AutoReviewStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "uncertain"
  | "none";

export type AutoReviewResponse = {
  compilation_run_id: string;
  status: AutoReviewStatus;
  review_id: string | null;
  error_code: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at: string | null;
  notScheduled?: boolean;
};

export type ReviewStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "uncertain";

export type CompilationReviewResponse = {
  id: string;
  compilation_run_id: string;
  workspace_id: string;
  collection_id: string;
  status: ReviewStatus;
  verdict: "needs_attention" | "no_issues_detected" | null;
  provider_id: string;
  input_sha256: string;
  draft_sha256: string;
  bundle_sha256: string;
  created_by: string;
  created_at: string;
  finished_at: string | null;
  error_code: string | null;
  usage_id: string | null;
  usage_tokens: number | null;
  trace: Record<string, unknown>;
};

export type ReviewRequestInput = {
  provider_id?: string | null;
  max_output_tokens?: number;
  structured_output?: boolean;
};

export type UnitExcerpt = {
  id: string;
  text: string;
  page?: number;
  kind?: string;
  [key: string]: unknown;
};

export type SourceAssessmentStatus =
  | "covered"
  | "omitted"
  | "out_of_scope"
  | "uncertain";

export type DraftAssessmentStatus =
  | "supported"
  | "contradicted"
  | "unsupported"
  | "uncertain";

export type SourceAssessmentEntry = {
  source_id: string;
  status: SourceAssessmentStatus;
  draft_ids: string[];
  explanation: string;
  suggested_action: string;
  source: UnitExcerpt;
  draft_excerpts: UnitExcerpt[];
};

export type DraftAssessmentEntry = {
  draft_id: string;
  status: DraftAssessmentStatus;
  source_ids: string[];
  explanation: string;
  suggested_action: string;
  draft: UnitExcerpt;
  source_excerpts: UnitExcerpt[];
};

export type ReviewFinding = {
  direction: "source_to_draft" | "draft_to_source";
  status: string;
  explanation: string;
  suggested_action: string;
  sources: UnitExcerpt[];
  draft_excerpts: UnitExcerpt[];
};

export type ReviewSummary = {
  source_units_checked: number;
  draft_units_checked: number;
  source_status_counts: Record<string, number>;
  draft_status_counts: Record<string, number>;
  finding_count: number;
};

export type ReviewReportResponse = {
  schema_version: string;
  review_id: string;
  bundle_sha256: string;
  topic: string;
  verdict: "needs_attention" | "no_issues_detected";
  summary: ReviewSummary;
  findings: ReviewFinding[];
  source_assessments: SourceAssessmentEntry[];
  draft_assessments: DraftAssessmentEntry[];
  limits: string[];
};

export type EditContextResponse = {
  compilation_run_id: string;
  bundle_sha256: string;
  edit_count: number;
  content: DraftContent;
  citations: Record<string, CitationDetail>;
  source_tables: LiteralTableEntry[];
  sources: SourceSummary[];
};

export type EditPreviewRequest = {
  expected_bundle_sha256: string;
  reason: string;
  review_id?: string | null;
  content: DraftContent;
};

export type EditPreviewResponse = {
  preview_id: string;
  preview_sha256: string;
  expires_at: string;
  before: DraftContent;
  after: DraftContent;
  reason: string;
  source_tables: LiteralTableEntry[];
  review_id: string | null;
  report_sha256: string | null;
};

export type AcceptEditRequest = {
  preview_id: string;
  preview_sha256: string;
};
