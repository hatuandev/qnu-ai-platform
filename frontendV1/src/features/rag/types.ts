/**
 * RAG contracts mirrored from backendV1 Context673.
 *
 * Sources of truth:
 * - `backendV1/qnu/domains/rag/policy.py` (RagPolicy)
 * - `backendV1/qnu/domains/knowledge/metadata.py` (MetadataFilter, MetadataValues,
 *   RetrievalAnnotation)
 * - `backendV1/qnu/domains/knowledge/index/schemas.py` (SearchRequest/SearchResponse)
 * - `backendV1/qnu/domains/rag/answer/schemas.py` (AnswerTrace, reason codes)
 * - `backendV1/qnu/domains/rag/answer/verification.py` (trace.verification report)
 *
 * Defaults must stay compatible with the backend: dense retrieval, no context
 * expansion, verification off. Nothing here may silently upgrade an existing
 * assistant to hybrid or turn the judge on.
 */

export type RetrievalMode = "dense" | "hybrid" | "hybrid_rerank";

export type VerificationMode = "off" | "observe" | "enforce";

export type VerificationStatus =
  | "not_run"
  | "supported"
  | "unsupported"
  | "uncertain";

export type MetadataScalar = string | number | boolean;

/** `MetadataValues` — annotations attached to a paragraph, row/cell or document. */
export type MetadataValues = {
  attributes?: Record<string, MetadataScalar> | null;
  data_year?: number | null;
  issued_year?: number | null;
  /** ISO `yyyy-mm-dd`. */
  effective_from?: string | null;
  /** ISO `yyyy-mm-dd`. */
  effective_until?: string | null;
  program?: string | null;
  intake?: string | null;
};

/** `MetadataFilter` — explicit scope sent with a search or a turn. */
export type MetadataFilter = {
  attributes?: Record<string, MetadataScalar> | null;
  data_year?: number | null;
  issued_year?: number | null;
  /** ISO `yyyy-mm-dd`; requires both effective bounds on the annotation. */
  effective_on?: string | null;
  program?: string | null;
  intake?: string | null;
};

export type MetadataEvidence = {
  citation: string;
  quote: string;
};

/** `RetrievalAnnotation` — metadata plus the source evidence that proves it. */
export type RetrievalAnnotation = {
  /** `document`, `paragraph:section:paragraph` or `table:citation:row:r[:column:c]`. */
  target: string;
  values: MetadataValues;
  evidence: MetadataEvidence[];
};

export type RagPolicy = {
  scope_resolution?: "explicit" | "catalog";
  retrieval_mode: RetrievalMode;
  candidate_k: number;
  rrf_k: number;
  rerank_provider_id: string | null;
  metadata_filter: MetadataFilter;
  context_window: number;
  context_max_bytes: number;
  verification_mode: VerificationMode;
  verification_provider_id: string | null;
  verification_max_output_tokens: number | null;
};

/** Backend defaults: dense + no context expansion + verification off. */
export const DEFAULT_RAG_POLICY: RagPolicy = {
  retrieval_mode: "dense",
  candidate_k: 30,
  rrf_k: 60,
  rerank_provider_id: null,
  metadata_filter: {},
  context_window: 0,
  context_max_bytes: 16000,
  verification_mode: "off",
  verification_provider_id: null,
  verification_max_output_tokens: null,
};

export const NEW_ASSISTANT_RAG_POLICY: RagPolicy = {
  ...DEFAULT_RAG_POLICY,
  scope_resolution: "catalog",
  context_window: 1,
};

export const RETRIEVAL_MODE_LABEL: Record<RetrievalMode, string> = {
  dense: "Dense (ngữ nghĩa)",
  hybrid: "Hybrid (dense + từ khóa)",
  hybrid_rerank: "Hybrid + Rerank",
};

export const VERIFICATION_MODE_LABEL: Record<VerificationMode, string> = {
  off: "Tắt kiểm chứng",
  observe: "Chỉ quan sát (không chặn)",
  enforce: "Chặn câu trả lời không được nguồn hỗ trợ",
};

export const VERIFICATION_STATUS_LABEL: Record<VerificationStatus, string> = {
  not_run: "Chưa chạy",
  supported: "Có nguồn hỗ trợ",
  unsupported: "Không được nguồn hỗ trợ",
  uncertain: "Chưa đủ chắc chắn",
};

/** `trace.verification` — the judge report; never mixed with generation usage. */
export type VerificationFinding = {
  statement_index: number;
  status: Exclude<VerificationStatus, "not_run">;
  reason: string;
  quotes?: { evidence_id: string; quote: string }[];
};

export type VerificationTrace = {
  mode?: VerificationMode;
  status?: VerificationStatus;
  version?: string;
  provider_id?: string | null;
  model_name?: string | null;
  configuration_hash?: string | null;
  usage_id?: string | null;
  /** Judge usage only. Missing means unknown, never 0. */
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  ms?: number;
  findings?: VerificationFinding[];
};

/** `trace.context` — context-window expansion accounting. */
export type ContextTrace = {
  status?: "disabled" | "no_hits" | "expanded" | string;
  bytes_used?: number;
  skipped_budget?: number;
  added?: unknown[];
};

/** `trace.retrieval` — ranking diagnostics; scores are on different scales. */
export type RetrievalTrace = {
  mode?: RetrievalMode;
  dense_count?: number;
  top_k?: number;
  manifest_sha256?: string | null;
  metadata_filter?: MetadataFilter;
  metadata_eligible_chunks?: number | null;
  query_embedding_ms?: number;
  dense_ms?: number;
  lexical_ms?: number;
  rerank_ms?: number;
  ranking?: Record<string, { chunk_id: string; score: number }[]>;
  score_kinds?: Record<string, string>;
};

/** True when the policy is still the backend-compatible default. */
export function isDefaultRagPolicy(
  policy: RagPolicy | null | undefined,
): boolean {
  if (!policy) return true;
  return (
    policy.retrieval_mode === "dense" &&
    (policy.scope_resolution ?? "explicit") === "explicit" &&
    policy.context_window === 0 &&
    policy.verification_mode === "off" &&
    policy.rerank_provider_id === null &&
    policy.verification_provider_id === null &&
    Object.keys(policy.metadata_filter ?? {}).length === 0
  );
}

/**
 * Mirrors `RagPolicy.compatible` and `AssistantConfig.candidate_budget`.
 * Returns a Vietnamese message for the first violated rule, or null.
 */
export function validateRagPolicy(
  policy: RagPolicy,
  topK: number,
): string | null {
  if (policy.retrieval_mode !== "dense" && policy.candidate_k < topK) {
    return "Ngân sách ứng viên (candidate_k) phải lớn hơn hoặc bằng Top K khi dùng hybrid hoặc rerank.";
  }
  if (policy.rerank_provider_id && policy.retrieval_mode !== "hybrid_rerank") {
    return "Chỉ chọn provider rerank khi chế độ truy xuất là Hybrid + Rerank.";
  }
  if (policy.verification_provider_id && policy.verification_mode === "off") {
    return "Cần bật kiểm chứng trước khi chọn provider kiểm chứng.";
  }
  return null;
}

/** Drops empty metadata-filter entries so `{}` stays `{}`. */
export function compactMetadataFilter(filter: MetadataFilter): MetadataFilter {
  const next: MetadataFilter = {};
  if (typeof filter.data_year === "number") next.data_year = filter.data_year;
  if (typeof filter.issued_year === "number")
    next.issued_year = filter.issued_year;
  if (filter.effective_on) next.effective_on = filter.effective_on;
  if (filter.program) next.program = filter.program;
  if (filter.intake) next.intake = filter.intake;
  if (filter.attributes && Object.keys(filter.attributes).length)
    next.attributes = filter.attributes;
  return next;
}

export function hasMetadataFilter(
  filter: MetadataFilter | null | undefined,
): boolean {
  return Object.keys(compactMetadataFilter(filter ?? {})).length > 0;
}

export function describeMetadataFilter(
  filter: MetadataFilter | null | undefined,
): string {
  const value = compactMetadataFilter(filter ?? {});
  const parts: string[] = [];
  if (value.data_year) parts.push(`Năm dữ liệu ${value.data_year}`);
  if (value.issued_year) parts.push(`Năm ban hành ${value.issued_year}`);
  if (value.effective_on) parts.push(`Hiệu lực ngày ${value.effective_on}`);
  if (value.program) parts.push(`Ngành ${value.program}`);
  if (value.intake) parts.push(`Đợt ${value.intake}`);
  for (const [key, entry] of Object.entries(value.attributes ?? {}))
    parts.push(`${key} · ${entry}`);
  return parts.length > 0 ? parts.join(" · ") : "Không giới hạn metadata";
}

/** Human summary of an annotation's declared values. Unknown values are absent. */
export function describeMetadataValues(
  values: MetadataValues | null | undefined,
): string {
  const parts: string[] = [];
  if (values?.data_year) parts.push(`Năm dữ liệu ${values.data_year}`);
  if (values?.issued_year) parts.push(`Năm ban hành ${values.issued_year}`);
  if (values?.effective_from)
    parts.push(`Hiệu lực từ ${values.effective_from}`);
  if (values?.effective_until) parts.push(`đến ${values.effective_until}`);
  if (values?.program) parts.push(`Ngành ${values.program}`);
  if (values?.intake) parts.push(`Đợt ${values.intake}`);
  for (const [label, value] of Object.entries(values?.attributes ?? {})) {
    parts.push(`${label} ${value}`);
  }
  return parts.length > 0 ? parts.join(" · ") : "Chưa khai báo giá trị";
}

/**
 * Readable label for a metadata target. The exact target string stays visible in
 * the UI: it is the only thing the backend can validate against.
 */
export function describeAnnotationTarget(target: string): string {
  if (target === "document") return "Toàn tài liệu";
  if (target.startsWith("section:")) return "Mục theo tiêu đề nguồn";
  const paragraph = /^paragraph:(\d+):(\d+)$/.exec(target);
  if (paragraph) {
    return `Đoạn ${Number(paragraph[2]) + 1} của mục ${Number(paragraph[1]) + 1}`;
  }
  const table = /^table:(.+):row:(\d+)(?::column:(\d+))?$/.exec(target);
  if (table) {
    const row = Number(table[2]) + 1;
    return table[3] === undefined
      ? `Hàng ${row} của bảng ${table[1]}`
      : `Ô hàng ${row}, cột ${Number(table[3]) + 1} của bảng ${table[1]}`;
  }
  return target;
}

/** `AnswerResponse.reason` codes, including the Context673 verification ones. */
export type AnswerReason =
  | "no_eligible_content"
  | "no_match"
  | "model_abstained"
  | "answer_not_supported"
  | "answer_verification_uncertain";

export function describeAnswerReason(
  reason: AnswerReason | null | undefined,
): string {
  switch (reason) {
    case "no_eligible_content":
      return "Không tìm thấy nội dung hợp lệ trong kho tri thức của trợ lý để trả lời câu hỏi này.";
    case "no_match":
      return "Nội dung tài liệu trong bộ sưu tập không khớp với câu hỏi của bạn.";
    case "model_abstained":
      return "Mô hình AI từ chối trả lời vì các bằng chứng tìm được không đủ căn cứ xác thực.";
    case "answer_not_supported":
      return "Câu trả lời do mô hình soạn không được nguồn trích dẫn hỗ trợ, nên hệ thống không phát hành. Đây là kết quả kiểm chứng, không phải lỗi kết nối.";
    case "answer_verification_uncertain":
      return "Bước kiểm chứng chưa xác định được câu trả lời có được nguồn hỗ trợ hay không, nên hệ thống giữ lại để người đọc tự đối chiếu. Đây là kết quả kiểm chứng, không phải lỗi kết nối.";
    default:
      return "Hệ thống từ chối kết luận do thiếu bằng chứng xác thực.";
  }
}
