/**
 * Provider PATCH semantics for backendV1.
 *
 * Rules taken from `qnu/domains/modelops/providers/service.py` and
 * `capacity/schemas.py`:
 *  - omitting a field keeps the stored value;
 *  - `token_limits: null` / `embedding_dimension: null` clears the declaration;
 *  - a token-limit object must declare at least one of context/input/output;
 *  - `max_input_tokens` / `max_output_tokens` may not exceed the shared context;
 *  - changing `base_url` or `model_name` invalidates the stored capacity.
 *
 * The form therefore keeps strings, and this module decides what (if anything)
 * is actually sent. Renaming a provider must never wipe its capacity.
 */

import type {
  Capability,
  OcrPageInputBudget,
  Provider,
  ProviderUpdateInput,
  TokenLimits,
} from "./types.ts";

export type CapacityDraft = {
  contextWindowTokens: string;
  maxInputTokens: string;
  maxOutputTokens: string;
  embeddingDimension: string;
  ocrMaxImageWidth: string;
  ocrMaxImageHeight: string;
  ocrInputTokensUpperBound: string;
  ocrPromptSha256: string;
};

export type ProviderFormValues = {
  name: string;
  baseUrl: string;
  modelName: string;
  capabilities: Capability[];
  priority: string;
  timeoutSeconds: string;
  capacity: CapacityDraft;
};

export const EMPTY_CAPACITY_DRAFT: CapacityDraft = {
  contextWindowTokens: "",
  maxInputTokens: "",
  maxOutputTokens: "",
  embeddingDimension: "",
  ocrMaxImageWidth: "",
  ocrMaxImageHeight: "",
  ocrInputTokensUpperBound: "",
  ocrPromptSha256: "",
};

function text(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value);
}

export function draftFromProvider(provider: Provider): CapacityDraft {
  // Strictly read declared `token_limits`, never `operational_budgets` (provisional defaults).
  const limits = provider.token_limits;
  const ocr = limits?.ocr_page_input ?? null;
  return {
    contextWindowTokens: text(limits?.context_window_tokens),
    maxInputTokens: text(limits?.max_input_tokens),
    maxOutputTokens: text(limits?.max_output_tokens),
    embeddingDimension: text(provider.embedding_dimension),
    ocrMaxImageWidth: text(ocr?.max_image_width),
    ocrMaxImageHeight: text(ocr?.max_image_height),
    ocrInputTokensUpperBound: text(ocr?.input_tokens_upper_bound),
    ocrPromptSha256: ocr?.prompt_sha256 ?? "",
  };
}

export function hasManualCapacityDraft(draft: CapacityDraft): boolean {
  return Boolean(
    draft.contextWindowTokens.trim() ||
      draft.maxInputTokens.trim() ||
      draft.maxOutputTokens.trim() ||
      draft.embeddingDimension.trim() ||
      hasOcrBudgetInput(draft),
  );
}

export function buildClearTokenLimitsPatch(): ProviderUpdateInput {
  return { token_limits: null };
}

export function formValuesFromProvider(provider: Provider): ProviderFormValues {
  return {
    name: provider.name,
    baseUrl: provider.base_url,
    modelName: provider.model_name,
    capabilities: provider.capabilities as Capability[],
    priority: String(provider.priority),
    timeoutSeconds: String(provider.timeout_seconds),
    capacity: draftFromProvider(provider),
  };
}

function parsePositive(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (!/^\d+$/.test(trimmed)) return null;
  const parsed = Number(trimmed);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}

export function hasOcrBudgetInput(draft: CapacityDraft): boolean {
  return Boolean(
    draft.ocrMaxImageWidth.trim() ||
      draft.ocrMaxImageHeight.trim() ||
      draft.ocrInputTokensUpperBound.trim() ||
      draft.ocrPromptSha256.trim(),
  );
}

/** Returns the first human-readable problem, or null when the draft is valid. */
export function validateCapacityDraft(draft: CapacityDraft): string | null {
  const numericFields: Array<[string, string]> = [
    ["context_window_tokens", draft.contextWindowTokens],
    ["max_input_tokens", draft.maxInputTokens],
    ["max_output_tokens", draft.maxOutputTokens],
  ];

  for (const [label, value] of numericFields) {
    if (value.trim() && parsePositive(value) === null) {
      return `${label} phải là số nguyên dương.`;
    }
  }

  const context = parsePositive(draft.contextWindowTokens);
  const maxInput = parsePositive(draft.maxInputTokens);
  const maxOutput = parsePositive(draft.maxOutputTokens);

  if (context !== null) {
    if (maxInput !== null && maxInput > context) {
      return "max_input_tokens không được vượt context_window_tokens.";
    }
    if (maxOutput !== null && maxOutput > context) {
      return "max_output_tokens không được vượt context_window_tokens.";
    }
  }

  if (hasOcrBudgetInput(draft)) {
    if (context === null && maxInput === null && maxOutput === null) {
      return "Khai báo ocr_page_input cần kèm ít nhất một giới hạn token của model.";
    }
    if (
      parsePositive(draft.ocrMaxImageWidth) === null ||
      parsePositive(draft.ocrMaxImageHeight) === null ||
      parsePositive(draft.ocrInputTokensUpperBound) === null
    ) {
      return "ocr_page_input cần đủ kích thước ảnh và input_tokens_upper_bound là số nguyên dương.";
    }
    if (!/^[0-9a-f]{64}$/.test(draft.ocrPromptSha256.trim())) {
      return "prompt_sha256 phải là 64 ký tự hex thường (SHA-256 của prompt UTF-8).";
    }
  }

  if (
    draft.embeddingDimension.trim() &&
    parsePositive(draft.embeddingDimension) === null
  ) {
    return "embedding_dimension phải là số nguyên dương.";
  }
  const dimension = parsePositive(draft.embeddingDimension);
  if (dimension !== null && dimension > 65536) {
    return "embedding_dimension tối đa 65536.";
  }

  return null;
}

function buildOcrBudget(draft: CapacityDraft): OcrPageInputBudget | null {
  if (!hasOcrBudgetInput(draft)) return null;
  return {
    max_image_width: parsePositive(draft.ocrMaxImageWidth) as number,
    max_image_height: parsePositive(draft.ocrMaxImageHeight) as number,
    input_tokens_upper_bound: parsePositive(
      draft.ocrInputTokensUpperBound,
    ) as number,
    prompt_sha256: draft.ocrPromptSha256.trim(),
  };
}

/**
 * Build the `token_limits` payload, or `null` when nothing is declared.
 *
 * Unknown fields stay `null`; they are never coerced to 0 or to "unlimited".
 */
export function tokenLimitsFromDraft(draft: CapacityDraft): TokenLimits | null {
  const context = parsePositive(draft.contextWindowTokens);
  const maxInput = parsePositive(draft.maxInputTokens);
  const maxOutput = parsePositive(draft.maxOutputTokens);
  const ocr = buildOcrBudget(draft);

  if (
    context === null &&
    maxInput === null &&
    maxOutput === null &&
    ocr === null
  ) {
    return null;
  }

  return {
    context_window_tokens: context,
    max_input_tokens: maxInput,
    max_output_tokens: maxOutput,
    ocr_page_input: ocr,
  };
}

export function embeddingDimensionFromDraft(
  draft: CapacityDraft,
): number | null {
  return parsePositive(draft.embeddingDimension);
}

function limitsSignature(limits: TokenLimits | null): string {
  if (!limits) return "null";
  return JSON.stringify({
    context: limits.context_window_tokens,
    input: limits.max_input_tokens,
    output: limits.max_output_tokens,
    ocr: limits.ocr_page_input
      ? [
          limits.ocr_page_input.max_image_width,
          limits.ocr_page_input.max_image_height,
          limits.ocr_page_input.input_tokens_upper_bound,
          limits.ocr_page_input.prompt_sha256,
        ]
      : null,
  });
}

function sameCapabilities(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false;
  const a = [...left].sort();
  const b = [...right].sort();
  return a.every((value, index) => value === b[index]);
}

/**
 * Only fields that actually changed are sent.
 *
 * `provider_type` is never included: the update schema does not accept it.
 */
export function buildProviderPatch(
  initial: Provider,
  values: ProviderFormValues,
): ProviderUpdateInput {
  const patch: ProviderUpdateInput = {};

  const name = values.name.trim();
  if (name && name !== initial.name) patch.name = name;

  const baseUrl = values.baseUrl.trim();
  if (baseUrl && baseUrl !== initial.base_url) patch.base_url = baseUrl;

  const modelName = values.modelName.trim();
  if (modelName && modelName !== initial.model_name)
    patch.model_name = modelName;

  if (!sameCapabilities(values.capabilities, initial.capabilities)) {
    patch.capabilities = [...values.capabilities];
  }

  const priority = parsePositive(values.priority);
  if (priority !== null && priority !== initial.priority)
    patch.priority = priority;

  const timeout = parsePositive(values.timeoutSeconds);
  if (timeout !== null && timeout !== initial.timeout_seconds) {
    patch.timeout_seconds = timeout;
  }

  const nextLimits = tokenLimitsFromDraft(values.capacity);
  if (limitsSignature(nextLimits) !== limitsSignature(initial.token_limits)) {
    patch.token_limits = nextLimits;
  }

  const nextDimension = embeddingDimensionFromDraft(values.capacity);
  if (nextDimension !== initial.embedding_dimension) {
    patch.embedding_dimension = nextDimension;
  }

  return patch;
}

export function isEmptyProviderPatch(patch: ProviderUpdateInput): boolean {
  return Object.keys(patch).length === 0;
}
