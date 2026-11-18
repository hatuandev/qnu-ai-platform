import type {
  AssistantCreateRequest,
  AssistantResponse,
  RagPolicy,
} from "@/api/assistants";
import {
  formToRagPolicy,
  NEW_ASSISTANT_POLICY,
  type RagPolicyFormState,
  ragPolicyToForm,
  validateRagPolicy,
} from "./assistant-advanced-fields";

export const AUTO_MODEL = "auto";

export const NAME_MAX_CHARS = 160;
export const DESCRIPTION_MAX_CHARS = 2000;
export const PERSONA_MAX_CHARS = 4000;

export const MAX_COLLECTIONS = 20;

export type AssistantFormState = {
  name: string;
  description: string;
  persona: string;
  collectionIds: string[];
  providerId: string;
  topK: string;
  historyTurns: string;
  maxOutputTokens: string;
  isActive: boolean;
  policy: RagPolicyFormState;
};

/** The effective collection set; scalar ``collection_id`` mirrors its first entry. */
export function collectionIdsOf(assistant: AssistantResponse): string[] {
  if (assistant.collection_ids?.length) return assistant.collection_ids;
  return assistant.collection_id ? [assistant.collection_id] : [];
}

export function initialState(
  assistant?: AssistantResponse | null,
): AssistantFormState {
  return {
    name: assistant?.name ?? "",
    description: assistant?.description ?? "",
    persona: assistant?.persona ?? "",
    collectionIds: assistant ? collectionIdsOf(assistant) : [],
    providerId: assistant?.chat_provider_id ?? AUTO_MODEL,
    topK: String(assistant?.top_k ?? 5),
    historyTurns: String(assistant?.history_turns ?? 3),
    maxOutputTokens:
      assistant?.max_output_tokens != null
        ? String(assistant.max_output_tokens)
        : "",
    isActive: assistant?.is_active ?? true,
    policy: ragPolicyToForm(assistant?.rag_policy ?? NEW_ASSISTANT_POLICY),
  };
}

export function validateAssistantForm(form: AssistantFormState): string | null {
  if (!form.name.trim()) return "Vui lòng nhập tên trợ lý.";
  if (form.name.trim().length > NAME_MAX_CHARS) {
    return `Tên trợ lý tối đa ${NAME_MAX_CHARS} ký tự.`;
  }
  if (form.description.length > DESCRIPTION_MAX_CHARS) {
    return `Mô tả ngắn tối đa ${DESCRIPTION_MAX_CHARS} ký tự.`;
  }
  if (form.persona.length > PERSONA_MAX_CHARS) {
    return `Chỉ dẫn vai trò tối đa ${PERSONA_MAX_CHARS} ký tự.`;
  }
  if (form.collectionIds.length > MAX_COLLECTIONS) {
    return `Trợ lý liên kết tối đa ${MAX_COLLECTIONS} kho tri thức.`;
  }
  const topK = Number(form.topK);
  if (!Number.isInteger(topK) || topK < 1 || topK > 20) {
    return "Số đoạn trích dẫn phải là số nguyên từ 1 đến 20.";
  }
  const historyTurns = Number(form.historyTurns);
  if (
    !Number.isInteger(historyTurns) ||
    historyTurns < 0 ||
    historyTurns > 10
  ) {
    return "Số lượt hội thoại ghi nhớ phải là số nguyên từ 0 đến 10.";
  }
  if (form.maxOutputTokens.trim()) {
    const tokens = Number(form.maxOutputTokens);
    if (!Number.isInteger(tokens) || tokens <= 0) {
      return "Giới hạn token đầu ra phải là số nguyên dương hoặc để trống.";
    }
  }
  return validateRagPolicy(form.policy, topK);
}

export function buildAssistantPayload(
  form: AssistantFormState,
  basePolicy: RagPolicy,
): AssistantCreateRequest {
  return {
    name: form.name.trim(),
    description: form.description.trim(),
    persona: form.persona.trim(),
    collection_id: form.collectionIds[0] ?? null,
    collection_ids: form.collectionIds,
    chat_provider_id: form.providerId === AUTO_MODEL ? null : form.providerId,
    top_k: Number(form.topK),
    history_turns: Number(form.historyTurns),
    max_output_tokens: form.maxOutputTokens.trim()
      ? Number(form.maxOutputTokens)
      : null,
    is_active: form.isActive,
    rag_policy: formToRagPolicy(form.policy, basePolicy),
  };
}
