import type { ProviderSetupProfile } from "./provider-capacity";

export type Capability = "chat" | "embedding" | "rerank" | "ocr";
export type LiveProfile = ProviderSetupProfile & {
  name: string;
  models: Record<Capability, string>;
  test_monthly_token_limit: number;
  additional_chat_provider?: ProviderSetupProfile & {
    name: string;
    models: { chat: string };
  };
};

export function profileForCapability(
  profile: LiveProfile,
  selection: "qnu" | "router" | undefined,
  capability: Capability,
): ProviderSetupProfile & { base_url: string } {
  if (profile.additional_chat_provider && !selection)
    throw new Error("BLOCKED: chạy provider-setup để chọn model mặc định.");
  if (selection === "router" && capability === "chat") {
    if (!profile.additional_chat_provider)
      throw new Error("BLOCKED: profile thiếu cấu hình 9router đã chọn.");
    return profile.additional_chat_provider;
  }
  return profile;
}

export function configuredProfiles(
  profile: LiveProfile,
): ProviderSetupProfile[] {
  return [
    profile,
    ...(profile.additional_chat_provider
      ? [profile.additional_chat_provider]
      : []),
  ];
}

export function acceptsModelObservation(
  target: ProviderSetupProfile,
  capability: Capability,
  requested: string,
  observed: string | null,
): boolean {
  if (!requested || target.models[capability] !== requested) return false;
  return (
    observed === null ||
    observed === requested ||
    target.observed_model_aliases?.[requested]?.includes(observed) === true
  );
}
