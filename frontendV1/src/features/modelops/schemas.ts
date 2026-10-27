/**
 * Client-side mirrors of `ProviderCreateRequest` / `ProviderUpdateRequest`.
 *
 * Limits are copied from `qnu/domains/modelops/schemas.py`; anything the
 * backend does not enforce is only a hint here, never a hard block.
 */

import { z } from "zod";

export const providerNameSchema = z
  .string()
  .trim()
  .min(2, "Tên provider cần ít nhất 2 ký tự.")
  .max(255, "Tên provider tối đa 255 ký tự.");

export const providerBaseUrlSchema = z
  .string()
  .trim()
  .min(8, "Base URL cần ít nhất 8 ký tự.")
  .max(1024, "Base URL tối đa 1024 ký tự.");

export const providerModelNameSchema = z
  .string()
  .trim()
  .min(1, "Model name không được để trống.")
  .max(200, "Model name tối đa 200 ký tự.");

const capabilitySchema = z.enum(["chat", "embedding", "rerank", "ocr"]);

/**
 * Form schema for the provider dialog.
 *
 * The eight capacity fields stay plain strings here: their rules live in
 * `capacity-patch.ts` (positive integers, `input/output <= context`,
 * `ocr_page_input` consistency) so that the same rules drive both the message
 * shown to the operator and the payload that is finally sent.
 */
export const providerFormSchema = z.object({
  name: providerNameSchema,
  baseUrl: providerBaseUrlSchema,
  modelName: providerModelNameSchema,
  capabilities: z
    .array(capabilitySchema)
    .min(1, "Chọn ít nhất một capability."),
  priority: z
    .string()
    .trim()
    .regex(/^\d+$/, "Priority là số nguyên từ 1 đến 10.")
    .refine((value) => Number(value) >= 1 && Number(value) <= 10, {
      message: "Priority nằm trong khoảng 1–10.",
    }),
  timeoutSeconds: z
    .string()
    .trim()
    .regex(/^\d+$/, "Timeout là số nguyên giây.")
    .refine((value) => Number(value) >= 1 && Number(value) <= 600, {
      message: "Timeout nằm trong khoảng 1–600 giây.",
    }),
  contextWindowTokens: z.string(),
  maxInputTokens: z.string(),
  maxOutputTokens: z.string(),
  embeddingDimension: z.string(),
  ocrMaxImageWidth: z.string(),
  ocrMaxImageHeight: z.string(),
  ocrInputTokensUpperBound: z.string(),
  ocrPromptSha256: z.string(),
});

/** `provider_type` is create-only: the update schema does not accept it. */
export const providerUpdateSchema = providerFormSchema;

export const keyCreateSchema = z.object({
  name: z
    .string()
    .trim()
    .min(2, "Tên key cần ít nhất 2 ký tự.")
    .max(120, "Tên key tối đa 120 ký tự."),
  secret: z
    .string()
    .min(8, "Secret cần ít nhất 8 ký tự.")
    .max(4096, "Secret tối đa 4096 ký tự."),
  priority: z
    .string()
    .trim()
    .regex(/^\d+$/, "Priority là số nguyên từ 1 đến 10.")
    .refine((value) => Number(value) >= 1 && Number(value) <= 10, {
      message: "Priority nằm trong khoảng 1–10.",
    }),
});

export const keyRotateSchema = keyCreateSchema.extend({
  reason: z.string().trim().max(512, "Lý do tối đa 512 ký tự."),
});

export const keyRevokeSchema = z.object({
  reason: z.string().trim().max(512, "Lý do tối đa 512 ký tự."),
});
