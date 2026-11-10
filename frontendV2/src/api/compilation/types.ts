/**
 * TypeScript types for Compilation domain.
 * Mirrors `backendV1/qnu/domains/knowledge/compilation/schemas.py` and `workflow/schemas.py`.
 */

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
  text: string;
  header: boolean;
  row_span: number;
  col_span: number;
};

export type SourceTableEntry = {
  citation: string;
  table: {
    rows: TableCell[][];
  };
};

export type CompilationDraftResponse = DraftContent & {
  schema_version: string;
  compilation_run_id: string;
  publication_status: string;
  requires_review: boolean;
  topic: string;
  citations: Record<string, unknown>;
  source_tables: SourceTableEntry[];
  sources: Array<{
    id?: string;
    source_id?: string;
    title?: string;
    file_name?: string;
    [key: string]: unknown;
  }>;
  validation?: Record<string, unknown>;
};

export type EditContextResponse = {
  compilation_run_id: string;
  bundle_sha256: string;
  edit_count: number;
  content: DraftContent;
  citations: Record<string, unknown>;
  source_tables: SourceTableEntry[];
  sources: Array<{
    id?: string;
    source_id?: string;
    title?: string;
    file_name?: string;
    [key: string]: unknown;
  }>;
};

export type EditPreviewRequest = {
  expected_bundle_sha256: string;
  reason: string;
  content: DraftContent;
  review_id?: string | null;
};

export type EditPreviewResponse = {
  preview_id: string;
  preview_sha256: string;
  expires_at: string;
  before: DraftContent;
  after: DraftContent;
  reason: string;
  source_tables: SourceTableEntry[];
  review_id?: string | null;
};

export type EditCommitRequest = {
  preview_id: string;
  preview_sha256: string;
};

export type CompilationResponse = {
  id: string;
  workspace_id: string;
  collection_id: string;
  generation: number;
  topic: string;
  status: string;
  provider_id: string | null;
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
  origin: string;
  source_first: boolean;
  ai_supplement: boolean;
  selective_supplement: boolean;
};

export type CompilationCreatedResponse = {
  run: CompilationResponse;
  created: boolean;
  dispatched: boolean;
};

// Durable root-part counts, not elapsed-time estimates or physical pages.
export type CompilationProgressResponse = {
  run_id: string;
  status: string;
  total: number;
  completed: number;
};
