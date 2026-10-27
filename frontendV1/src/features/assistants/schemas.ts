import { z } from "zod";
import { ragPolicyFormSchema } from "@/features/rag/schemas";

/**
 * Zod validation schemas strictly mirroring `backendV1/qnu/domains/assistants/schemas.py`.
 */

export const assistantNameSchema = z
  .string()
  .trim()
  .min(1, "Tên trợ lý không được để trống.")
  .max(160, "Tên trợ lý tối đa 160 ký tự.");

export const assistantDescriptionSchema = z
  .string()
  .max(2000, "Mô tả tối đa 2000 ký tự.");

export const assistantPersonaSchema = z
  .string()
  .max(4000, "Chỉ dẫn hệ thống/persona tối đa 4000 ký tự.");

export const collectionIdSchema = z
  .string()
  .trim()
  .min(1, "Vui lòng chọn bộ sưu tập kho tri thức.")
  .max(64, "Mã bộ sưu tập không hợp lệ.");

export const chatProviderIdSchema = z
  .string()
  .trim()
  .min(1)
  .max(64)
  .nullable()
  .optional();

export const topKSchema = z.coerce
  .number()
  .int("Top K phải là số nguyên.")
  .min(1, "Top K tối thiểu là 1.")
  .max(20, "Top K tối đa là 20.");

export const historyTurnsSchema = z.coerce
  .number()
  .int("Số lượt hội thoại phải là số nguyên.")
  .min(0, "Số lượt hội thoại tối thiểu là 0.")
  .max(10, "Số lượt hội thoại tối đa là 10.");

export const maxOutputTokensSchema = z.coerce
  .number()
  .int("Giới hạn token xuất phải là số nguyên.")
  .gt(0, "Giới hạn token xuất phải lớn hơn 0.");

export const isActiveSchema = z.boolean();

export const expectedRevisionSchema = z.coerce
  .number()
  .int("Revision phải là số nguyên.")
  .min(1, "Revision phải lớn hơn hoặc bằng 1.");

/**
 * Assistant create form schema
 */
export const assistantCreateSchema = z.object({
  name: assistantNameSchema,
  description: assistantDescriptionSchema.default(""),
  persona: assistantPersonaSchema.default(""),
  collection_id: collectionIdSchema,
  chat_provider_id: chatProviderIdSchema.default(null),
  top_k: topKSchema.default(5),
  history_turns: historyTurnsSchema.default(3),
  max_output_tokens: maxOutputTokensSchema.default(2048),
  is_active: isActiveSchema.default(true),
});

/**
 * Assistant update form schema (requires expected_revision)
 */
export const assistantUpdateSchema = assistantCreateSchema.extend({
  expected_revision: expectedRevisionSchema,
});

/**
 * Form validator schema accepting exact defaultValues types
 */
export const assistantFormSchema = z.object({
  name: assistantNameSchema,
  description: assistantDescriptionSchema,
  persona: assistantPersonaSchema,
  collection_id: collectionIdSchema,
  chat_provider_id: z.string().trim().min(1).max(64).nullable(),
  top_k: z
    .number()
    .int("Top K phải là số nguyên.")
    .min(1, "Top K tối thiểu là 1.")
    .max(20, "Top K tối đa là 20."),
  history_turns: z
    .number()
    .int("Số lượt hội thoại phải là số nguyên.")
    .min(0, "Số lượt hội thoại tối thiểu là 0.")
    .max(10, "Số lượt hội thoại tối đa là 10."),
  max_output_tokens: z
    .number()
    .int("Giới hạn token xuất phải là số nguyên.")
    .gt(0, "Giới hạn token xuất phải lớn hơn 0."),
  is_active: isActiveSchema,
  rag_policy: ragPolicyFormSchema,
  expected_revision: z
    .number()
    .int("Revision phải là số nguyên.")
    .min(1, "Revision phải lớn hơn hoặc bằng 1."),
});

/**
 * Query search params schema for assistants list
 */
export const assistantListSearchSchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).catch(20),
  offset: z.coerce.number().int().min(0).catch(0),
});

export type AssistantListSearch = z.infer<typeof assistantListSearchSchema>;

export const DEFAULT_ASSISTANT_SEARCH: AssistantListSearch = {
  limit: 20,
  offset: 0,
};
