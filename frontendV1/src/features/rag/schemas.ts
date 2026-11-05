import { z } from "zod";
import type { MetadataFilter, RagPolicy } from "./types";
import { DEFAULT_RAG_POLICY } from "./types";

/**
 * Flat form representation of `RagPolicy`.
 *
 * The API payload is nested; the form stays flat so every control is a simple
 * TanStack Form field with its own error message, and no one has to type JSON.
 */
export type RagPolicyFormValues = {
  scope_resolution: "explicit" | "catalog";
  retrieval_mode: RagPolicy["retrieval_mode"];
  candidate_k: number;
  rrf_k: number;
  rerank_provider_id: string | null;
  context_window: number;
  context_max_bytes: number;
  verification_mode: RagPolicy["verification_mode"];
  verification_provider_id: string | null;
  verification_max_output_tokens: number | null;
  filter_data_year: number | null;
  filter_issued_year: number | null;
  filter_effective_on: string;
  filter_program: string;
  filter_intake: string;
  filter_attributes?: MetadataFilter["attributes"];
};

const yearSchema = z
  .number()
  .int("Năm phải là số nguyên.")
  .min(1000, "Năm phải từ 1000 đến 9999.")
  .max(9999, "Năm phải từ 1000 đến 9999.")
  .nullable();

const isoDateSchema = z
  .string()
  .trim()
  .regex(/^$|^\d{4}-\d{2}-\d{2}$/, "Ngày hiệu lực phải có dạng YYYY-MM-DD.")
  .refine(
    (value) => value === "" || !Number.isNaN(Date.parse(`${value}T00:00:00Z`)),
    "Ngày hiệu lực không hợp lệ.",
  );

export const ragPolicyFormSchema = z
  .object({
    scope_resolution: z.enum(["explicit", "catalog"]).default("explicit"),
    retrieval_mode: z.enum(["dense", "hybrid", "hybrid_rerank"]),
    candidate_k: z
      .number()
      .int("Ngân sách ứng viên phải là số nguyên.")
      .min(1, "Ngân sách ứng viên tối thiểu là 1.")
      .max(100, "Ngân sách ứng viên tối đa là 100."),
    rrf_k: z
      .number()
      .int("RRF k phải là số nguyên.")
      .min(1, "RRF k tối thiểu là 1.")
      .max(1000, "RRF k tối đa là 1000."),
    rerank_provider_id: z.string().trim().min(1).max(64).nullable(),
    context_window: z
      .number()
      .int("Cửa sổ ngữ cảnh phải là số nguyên.")
      .min(0, "Cửa sổ ngữ cảnh tối thiểu là 0.")
      .max(5, "Cửa sổ ngữ cảnh tối đa là 5."),
    context_max_bytes: z
      .number()
      .int("Ngân sách ngữ cảnh phải là số nguyên.")
      .min(256, "Ngân sách ngữ cảnh tối thiểu 256 byte.")
      .max(128000, "Ngân sách ngữ cảnh tối đa 128000 byte."),
    verification_mode: z.enum(["off", "observe", "enforce"]),
    verification_provider_id: z.string().trim().min(1).max(64).nullable(),
    verification_max_output_tokens: z
      .number()
      .int("Ngân sách token kiểm chứng phải là số nguyên.")
      .positive("Ngân sách token kiểm chứng phải lớn hơn 0.")
      .nullable(),
    filter_attributes: z
      .record(
        z.string().min(1).max(80),
        z.union([z.string().min(1).max(500), z.number(), z.boolean()]),
      )
      .nullish(),
    filter_data_year: yearSchema,
    filter_issued_year: yearSchema,
    filter_effective_on: isoDateSchema,
    filter_program: z.string().trim().max(160, "Ngành tối đa 160 ký tự."),
    filter_intake: z.string().trim().max(160, "Đợt tối đa 160 ký tự."),
  })
  .superRefine((value, ctx) => {
    if (value.rerank_provider_id && value.retrieval_mode !== "hybrid_rerank") {
      ctx.addIssue({
        code: "custom",
        path: ["rerank_provider_id"],
        message:
          "Chỉ chọn provider rerank khi chế độ truy xuất là Hybrid + Rerank.",
      });
    }
    if (value.verification_provider_id && value.verification_mode === "off") {
      ctx.addIssue({
        code: "custom",
        path: ["verification_provider_id"],
        message: "Cần bật kiểm chứng trước khi chọn provider kiểm chứng.",
      });
    }
  });

export const DEFAULT_RAG_POLICY_FORM: RagPolicyFormValues =
  toRagPolicyForm(DEFAULT_RAG_POLICY);

/** Form values → API `rag_policy`. Empty filter fields are omitted. */
export function toRagPolicy(values: RagPolicyFormValues): RagPolicy {
  const filter: MetadataFilter = {};
  if (values.filter_attributes && Object.keys(values.filter_attributes).length)
    filter.attributes = values.filter_attributes;
  if (typeof values.filter_data_year === "number") {
    filter.data_year = values.filter_data_year;
  }
  if (typeof values.filter_issued_year === "number") {
    filter.issued_year = values.filter_issued_year;
  }
  if (values.filter_effective_on)
    filter.effective_on = values.filter_effective_on;
  if (values.filter_program) filter.program = values.filter_program;
  if (values.filter_intake) filter.intake = values.filter_intake;

  return {
    ...(values.scope_resolution === "catalog"
      ? { scope_resolution: "catalog" as const }
      : {}),
    retrieval_mode: values.retrieval_mode,
    candidate_k: values.candidate_k,
    rrf_k: values.rrf_k,
    // A rerank provider is meaningless outside hybrid_rerank; never send a
    // stale id that the backend would reject.
    rerank_provider_id:
      values.retrieval_mode === "hybrid_rerank"
        ? values.rerank_provider_id
        : null,
    metadata_filter: filter,
    context_window: values.context_window,
    context_max_bytes: values.context_max_bytes,
    verification_mode: values.verification_mode,
    verification_provider_id:
      values.verification_mode === "off"
        ? null
        : values.verification_provider_id,
    verification_max_output_tokens: values.verification_max_output_tokens,
  };
}

/** API `rag_policy` (possibly absent on older assistants) → form values. */
export function toRagPolicyForm(
  policy: RagPolicy | null | undefined,
): RagPolicyFormValues {
  const source = policy ?? DEFAULT_RAG_POLICY;
  const filter = source.metadata_filter ?? {};
  return {
    scope_resolution: source.scope_resolution ?? "explicit",
    retrieval_mode: source.retrieval_mode ?? "dense",
    candidate_k: source.candidate_k ?? 30,
    rrf_k: source.rrf_k ?? 60,
    rerank_provider_id: source.rerank_provider_id ?? null,
    context_window: source.context_window ?? 0,
    context_max_bytes: source.context_max_bytes ?? 16000,
    verification_mode: source.verification_mode ?? "off",
    verification_provider_id: source.verification_provider_id ?? null,
    verification_max_output_tokens:
      source.verification_max_output_tokens ?? null,
    filter_data_year: filter.data_year ?? null,
    filter_issued_year: filter.issued_year ?? null,
    filter_effective_on: filter.effective_on ?? "",
    filter_program: filter.program ?? "",
    filter_intake: filter.intake ?? "",
    ...(filter.attributes ? { filter_attributes: filter.attributes } : {}),
  };
}
