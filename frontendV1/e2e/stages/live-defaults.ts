import { readFileSync } from "node:fs";
import path from "node:path";
import { type LiveProfile, profileForCapability } from "./live-profile";
import { type Api, type Checkpoint, directory, sha256 } from "./session";

type Capability = "chat" | "embedding" | "rerank" | "ocr";
export type RuntimeDefaults = Record<Capability, string>;
interface RuntimeProvider {
  id: string;
  parent_id: string | null;
  model_name: string;
  base_url: string;
  capabilities: string[];
  is_active: boolean;
  capacity_status: string;
  token_limits: {
    max_input_tokens?: number | null;
    context_window_tokens?: number | null;
    max_output_tokens?: number | null;
    ocr_page_input?: {
      prompt_sha256: string;
      input_tokens_upper_bound: number;
      max_image_width: number;
      max_image_height: number;
    } | null;
  } | null;
  embedding_dimension: number | null;
  embedding_dimension_status: string;
}
interface Observation {
  stage: string;
  model: string;
  provider_id: string;
  diagnostic_id: string;
  upstream_http: number;
  code: string;
  observed_dimension: number | null;
}

export async function liveDefaults(api: Api, state: Checkpoint) {
  const file = process.env.E2E_MODEL_PROFILE;
  if (!file) throw new Error("BLOCKED: thiếu profile model cho pipeline live.");
  const profile = JSON.parse(readFileSync(file, "utf8")) as LiveProfile;
  if (
    !Number.isSafeInteger(profile.test_monthly_token_limit) ||
    profile.test_monthly_token_limit <= 0 ||
    profile.test_monthly_token_limit > 20_000_000
  ) {
    throw new Error(
      "BLOCKED: quota thử phải là số nguyên dương, tối đa 20.000.000 token trong profile.",
    );
  }
  const connections = await api.get<
    { id: string; base_url: string; is_active: boolean }[]
  >("/modelops/connections");
  const defaults = {} as RuntimeDefaults;
  for (const capability of ["chat", "embedding", "rerank", "ocr"] as const) {
    const target = profileForCapability(
      profile,
      state.chatSelection,
      capability,
    );
    const connection = connections.filter(
      (row) =>
        row.is_active &&
        row.base_url.replace(/\/+$/, "") ===
          target.base_url.replace(/\/+$/, ""),
    );
    if (connection.length !== 1)
      throw new Error(
        "BLOCKED: cần đúng một nhà cung cấp đang bật cho model đã chọn.",
      );
    const providers = await api.get<RuntimeProvider[]>(
      `/modelops/connections/${connection[0].id}/models`,
    );
    const stage = `model-${capability}`;
    const result = state.results[stage];
    if (result?.status !== "PASS" || !result.report)
      throw new Error(`BLOCKED: chạy ${stage} đạt trước navigation.`);
    const report = path.resolve(result.report);
    if (path.dirname(path.dirname(report)) !== directory)
      throw new Error("BLOCKED: báo cáo model không thuộc phiên.");
    const observation = JSON.parse(
      readFileSync(path.join(report, "model-observation.json"), "utf8"),
    ) as Observation;
    const provider = providers.find(
      (row) => row.id === observation.provider_id,
    );
    if (
      !provider?.is_active ||
      provider.parent_id !== connection[0].id ||
      provider.model_name !== target.models[capability] ||
      !provider.capabilities.includes(capability) ||
      provider.base_url.replace(/\/+$/, "") !==
        target.base_url.replace(/\/+$/, "")
    ) {
      throw new Error(
        `BLOCKED: model ${capability} đã thay đổi hoặc không khớp profile, chạy lại test model.`,
      );
    }
    if (
      observation.stage !== stage ||
      observation.model !== provider.model_name ||
      observation.code !== "diagnostic_ok" ||
      observation.upstream_http !== 200
    )
      throw new Error(`BLOCKED: observation ${capability} không hợp lệ.`);
    const history = await api.get<{
      checks: { id: string; outcome: string; configuration_status: string }[];
    }>(`/modelops/providers/${provider.id}/diagnostics`);
    if (
      !history.checks.some(
        (row) =>
          row.id === observation.diagnostic_id &&
          row.outcome === "ok" &&
          row.configuration_status === "current",
      )
    )
      throw new Error(
        `BLOCKED: kiểm định ${capability} đã cũ; cấu hình capacity/dimension xong cần chạy lại model-${capability}.`,
      );
    if (provider.capacity_status !== "configured" || !provider.token_limits)
      throw new Error(
        `BLOCKED: khai báo capacity thực tế cho ${provider.model_name}, rồi test lại model.`,
      );
    if (
      capability === "embedding" &&
      (provider.embedding_dimension_status !== "configured" ||
        !provider.embedding_dimension ||
        provider.embedding_dimension !== observation.observed_dimension)
    )
      throw new Error(
        "BLOCKED: cấu hình dimension embedding theo số chiều quan sát rồi chạy lại model-embedding.",
      );
    if (capability === "ocr") {
      const accounting = provider.token_limits.ocr_page_input;
      const promptHash = sha256(
        Buffer.from(
          "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>",
        ),
      );
      if (
        !accounting ||
        accounting.prompt_sha256 !== promptHash ||
        accounting.input_tokens_upper_bound <= 0 ||
        accounting.max_image_width <= 0 ||
        accounting.max_image_height <= 0
      )
        throw new Error(
          "BLOCKED: cấu hình ngân sách ảnh OCR/prompt theo server thật rồi chạy lại model-ocr.",
        );
    }
    defaults[capability] = provider.id;
  }
  return { defaults, monthlyTokenLimit: profile.test_monthly_token_limit };
}
