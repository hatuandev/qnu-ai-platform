import { z } from "zod";
import { knowledgePaths, type V1Client } from "@/app/api/v1";
import type { AnswerResponse } from "@/features/conversations/types";
import {
  type MetadataFilterDraft,
  validateMetadataFilterDraft,
} from "@/features/rag/metadata-filter-fields";
import {
  ragPolicyFormSchema,
  toRagPolicy,
  toRagPolicyForm,
} from "@/features/rag/schemas";
import {
  DEFAULT_RAG_POLICY,
  type RagPolicy,
  validateRagPolicy,
} from "@/features/rag/types";

export type AnswerSettings = RagPolicy & {
  top_k: number;
  provider_id: string | null;
  max_output_tokens: number;
};
export type AnswerRequest = Omit<AnswerSettings, "max_output_tokens"> & {
  max_output_tokens: number | null;
  question: string;
  document_ids: string[] | null;
};
export const DEFAULT_ANSWER_SETTINGS: AnswerSettings = {
  ...DEFAULT_RAG_POLICY,
  top_k: 5,
  provider_id: null,
  max_output_tokens: Number.NaN,
};
const requestSchema = z.object({
  question: z.string().trim().min(1, "Nhập câu hỏi.").max(8000),
  top_k: z.number().int().min(1).max(20),
  provider_id: z.string().min(1).max(64).nullable(),
  max_output_tokens: z.number().int().positive().nullable(),
  document_ids: z
    .array(z.string().min(1).max(64))
    .max(100)
    .refine((v) => new Set(v).size === v.length, "Tài liệu bị trùng."),
});
export function buildAnswerRequest(
  question: string,
  settings: AnswerSettings,
  documents: string[],
  filter: MetadataFilterDraft,
): AnswerRequest {
  const errors = validateMetadataFilterDraft(filter);
  if (Object.keys(errors).length)
    throw new Error(Object.values(errors).join(" "));
  const basic = requestSchema.safeParse({
    question,
    ...settings,
    max_output_tokens: Number.isNaN(settings.max_output_tokens)
      ? null
      : settings.max_output_tokens,
    document_ids: documents,
  });
  if (!basic.success)
    throw new Error(
      basic.error.issues[0]?.message ?? "Kiểm tra câu hỏi và ngân sách.",
    );
  const parsed = ragPolicyFormSchema.safeParse({
    ...toRagPolicyForm(settings),
    filter_data_year: filter.data_year.trim() ? Number(filter.data_year) : null,
    filter_issued_year: filter.issued_year.trim()
      ? Number(filter.issued_year)
      : null,
    filter_effective_on: filter.effective_on.trim(),
    filter_program: filter.program.trim(),
    filter_intake: filter.intake.trim(),
  });
  if (!parsed.success)
    throw new Error(
      parsed.error.issues[0]?.message ??
        "Phạm vi hoặc cấu hình RAG không hợp lệ.",
    );
  const policy = toRagPolicy(parsed.data);
  const invalid = validateRagPolicy(policy, basic.data.top_k);
  if (invalid) throw new Error(invalid);
  return {
    ...policy,
    ...basic.data,
    document_ids: documents.length ? documents : null,
  };
}
export function requestAnswer(
  client: V1Client,
  workspaceId: string,
  collectionId: string,
  body: AnswerRequest,
) {
  // Synchronous/stateless API: no automatic retry and no invented idempotency contract.
  return client.post<AnswerResponse>(
    knowledgePaths.answers(workspaceId, collectionId),
    body,
  );
}
