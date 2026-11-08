import type { CompilationOrigin, CompilationStatus } from "./compilation-types";
import type { IndexReadiness } from "./index-types";
import type { ProcessingRunResponse } from "./ocr-types";
import type { DocumentResponse, VersionResponse } from "./publication-types";
import type { KBRevision, PageResponse } from "./types";

/**
 * Read-model summaries mirrored from
 * `backendV1/qnu/domains/knowledge/sources/schemas.py` and
 * `backendV1/qnu/domains/knowledge/publication/schemas.py`.
 */

export type SummaryCapabilities = {
  can_prepare: boolean;
  can_register: boolean;
  can_approve: boolean;
  can_publish: boolean;
};

export type SourceTextVersionRef = {
  id: string;
  version: number;
  canonical_sha256: string;
  markdown_sha256: string;
  created_by: string;
  created_at: string;
};

export type SourceProcessingRunSummary = ProcessingRunResponse & {
  latest_text_version: SourceTextVersionRef | null;
};

export type SourceVersionRef = {
  version_id: string;
  version_no: number;
  state_version: number;
  status: string;
  bundle_sha256: string;
  document_id: string;
  document_title: string;
};

export type SourceDerivation = {
  compilation_run_id: string;
  compilation_generation: number;
  compilation_status: CompilationStatus;
  origin: CompilationOrigin;
  ocr_run_id: string;
  ocr_generation: number;
  text_version: SourceTextVersionRef | null;
  version: SourceVersionRef | null;
  readiness: IndexReadiness | null;
  is_serving: boolean;
};

export type SourceSummaryResponse = {
  observed_at: string;
  source_id: string;
  title: string;
  latest_revision_no: number;
  serving_revision_no: number;
  revision: KBRevision;
  processing_runs: SourceProcessingRunSummary[];
  runs_truncated: boolean;
  active_run_id: string | null;
  derivations: SourceDerivation[];
  derivations_truncated: boolean;
  capabilities: SummaryCapabilities;
};

export type VersionOrigin = {
  source_id: string;
  source_title: string;
  revision_id: string;
  revision_no: number;
  file_name: string;
  sha256: string;
  ocr_run_id: string;
  ocr_generation: number;
  text_version_id: string | null;
  text_version_no: number | null;
};

export type VersionSummary = VersionResponse & {
  origins: VersionOrigin[];
};

export type DocumentSummaryResponse = {
  observed_at: string;
  document: DocumentResponse;
  prepared_version: VersionResponse | null;
  published_version: VersionResponse | null;
  served_version: VersionResponse | null;
  published_decision_id: string | null;
  readiness: IndexReadiness;
  serving_matches_published: boolean;
  versions: PageResponse<VersionSummary>;
  capabilities: SummaryCapabilities;
};
