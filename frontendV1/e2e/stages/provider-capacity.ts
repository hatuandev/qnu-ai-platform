import type {
  Capability,
  Provider,
  TokenLimits,
} from "../../src/features/modelops/types";
import type { Api } from "./session";

export type ProviderSetupProfile = {
  base_url: string;
  models: Partial<Record<Capability, string>>;
  observed_model_aliases?: Record<string, string[]>;
  model_runtime?: Partial<
    Record<
      Capability,
      {
        timeout_seconds?: number;
        max_input_tokens?: number;
        ocr_page_input?: NonNullable<TokenLimits["ocr_page_input"]>;
      }
    >
  >;
};

type SetupApi = Pick<Api, "post" | "json">;

function runtimePatch(
  model: Provider,
  profile: ProviderSetupProfile,
  capability: Capability,
) {
  const configured = profile.model_runtime?.[capability];
  const patch: { timeout_seconds?: number; token_limits?: TokenLimits } = {};
  if (!configured) return patch;
  if (
    configured.timeout_seconds !== undefined &&
    model.timeout_seconds !== configured.timeout_seconds
  ) {
    patch.timeout_seconds = configured.timeout_seconds;
  }
  const limits = model.token_limits;
  if (!limits)
    throw new Error(`BLOCKED: chưa có capacity cho ${model.model_name}.`);
  const merged = { ...limits };
  if (
    limits.max_input_tokens == null &&
    configured.max_input_tokens !== undefined
  ) {
    merged.max_input_tokens = configured.max_input_tokens;
  }
  if (limits.ocr_page_input == null && configured.ocr_page_input) {
    merged.ocr_page_input = configured.ocr_page_input;
  }
  if (JSON.stringify(merged) !== JSON.stringify(limits))
    patch.token_limits = merged;
  return patch;
}

export async function configureTestModelCapacity(
  api: SetupApi,
  connectionId: string,
  profile: ProviderSetupProfile,
  checkId: string | null | undefined,
  requireCapacity = true,
) {
  if (!checkId)
    throw new Error(
      "BLOCKED: backend chưa trả snapshot discovery để đồng bộ capacity.",
    );
  const models = await api.post<Provider[]>(
    `/modelops/connections/${connectionId}/sync-capacity`,
    {
      check_id: checkId,
      model_names: Object.values(profile.models),
    },
  );
  for (const [capability, name] of Object.entries(profile.models) as [
    Capability,
    string,
  ][]) {
    const matching = models.filter((item) => item.model_name === name);
    const model = matching[0];
    if (
      matching.length !== 1 ||
      model.parent_id !== connectionId ||
      !model.is_active ||
      model.base_url.replace(/\/+$/, "") !==
        profile.base_url.replace(/\/+$/, "") ||
      !model.capabilities.includes(capability)
    ) {
      throw new Error(`BLOCKED: chưa đồng bộ đúng capacity cho ${name}.`);
    }
    if (model.capacity_status !== "configured" || !model.token_limits) {
      if (!requireCapacity) continue;
      throw new Error(
        `BLOCKED: chưa đồng bộ đúng capacity cho ${name}; cấu hình giới hạn thật trong ModelOps rồi chạy lại.`,
      );
    }
    const patch = runtimePatch(model, profile, capability);
    if (Object.keys(patch).length) {
      await api.json("PATCH", `/modelops/providers/${model.id}`, patch);
    }
  }
}
