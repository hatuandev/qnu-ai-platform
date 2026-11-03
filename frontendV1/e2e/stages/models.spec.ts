import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  acceptsModelObservation,
  configuredProfiles,
  type LiveProfile,
  profileForCapability,
} from "./live-profile";
import type { ProviderSetupProfile } from "./provider-capacity";
import { type Api, authenticate, checkpoint, directory } from "./session";

type Capability = "chat" | "embedding" | "rerank" | "ocr";
interface Provider {
  id: string;
  parent_id: string | null;
  model_name: string;
  base_url: string;
  is_active: boolean;
  capabilities: string[];
}
interface Connection {
  id: string;
  base_url: string;
  is_active: boolean;
  active_keys_count: number;
}
interface Diagnostic {
  id: string;
  kind: string;
  outcome: "ok" | "failed" | "unsupported";
  code: string;
  http_status: number | null;
  configuration_status: "current" | "stale";
  requested_model: string;
  observed_model: string | null;
  observed_dimension: number | null;
  total_tokens: number | null;
  latency_ms: number | null;
  models: string[];
}
const stage = process.env.E2E_STAGE;
if (!stage?.startsWith("model-"))
  throw new Error("Chọn chặng model-* bằng runner.");
const profilePath = process.env.E2E_MODEL_PROFILE;
if (!profilePath) throw new Error("BLOCKED: chưa chọn profile kiểm tra model.");
const profile = JSON.parse(readFileSync(profilePath, "utf8")) as LiveProfile;
for (const configured of configuredProfiles(profile)) {
  const endpoint = new URL(configured.base_url);
  if (
    !/^(http|https):$/.test(endpoint.protocol) ||
    endpoint.username ||
    endpoint.password ||
    endpoint.search ||
    endpoint.hash
  ) {
    throw new Error("BLOCKED: profile endpoint không hợp lệ.");
  }
}
const normalize = (url: string) => url.replace(/\/+$/, "");
const sameEndpoint = (url: string, target: ProviderSetupProfile) =>
  normalize(url) === normalize(target.base_url);

// Diagnostic APIs keep credentials in ModelOps; do not capture network tokens in traces.
test.use({ trace: "off", video: "off", screenshot: "off" });

async function connectionFor(
  api: Api,
  target: ProviderSetupProfile,
): Promise<Connection> {
  const rows = await api.get<Connection[]>("/modelops/connections");
  const matches = rows.filter(
    (row) => row.is_active && sameEndpoint(row.base_url, target),
  );
  if (matches.length !== 1) {
    throw new Error(
      "BLOCKED: cần đúng một nhà cung cấp đang bật với Base URL trong profile; thêm qua ModelOps của phiên live.",
    );
  }
  if (matches[0].active_keys_count < 1) {
    throw new Error(
      "BLOCKED: thêm khóa server AI đang hoạt động trong ModelOps trước; không truyền key vào lệnh hoặc .env.",
    );
  }
  return matches[0];
}

async function requireDiagnostic(
  api: Api,
  providerId: string,
  result: Diagnostic,
  expectedKind: string,
  mineru = false,
) {
  // HTTP 200 from the admin API alone can still contain a failed upstream check.
  if (result.outcome !== "ok") {
    throw new Error(
      `Model diagnostic FAIL: kind=${expectedKind}, code=${result.code}, upstream_http=${result.http_status ?? "unknown"}`,
    );
  }
  expect(result.kind).toBe(expectedKind);
  expect(result.code).toBe("diagnostic_ok");
  if (mineru) expect(result.http_status).toBeNull();
  else expect(result.http_status).toBe(200);
  expect(result.latency_ms).not.toBeNull();
  expect(result.latency_ms).toBeGreaterThanOrEqual(0);
  const history = await api.get<{ checks: Diagnostic[] }>(
    `/modelops/providers/${providerId}/diagnostics`,
  );
  const recorded = history.checks.find((check) => check.id === result.id);
  expect(
    recorded,
    "Kết quả diagnostic phải được lưu trong ModelOps",
  ).toBeDefined();
  expect(recorded?.configuration_status).toBe("current");
  expect(recorded?.outcome).toBe("ok");
}

test(`Model thật đã chọn: ${stage}`, async ({ page }) => {
  test.setTimeout(360_000);
  const state = checkpoint();
  if (state.mode !== "live") throw new Error("BLOCKED: cần init --mode live.");
  const api = await authenticate(page);
  const target = profileForCapability(
    profile,
    state.chatSelection,
    stage === "model-discovery" ? "embedding" : (stage.slice(6) as Capability),
  );
  const connection = await connectionFor(api, target);
  const capabilities: Capability[] = ["chat", "embedding", "rerank", "ocr"];
  for (const capability of capabilities) {
    if (
      !profileForCapability(profile, state.chatSelection, capability).models[
        capability
      ]?.trim()
    )
      throw new Error(`BLOCKED: profile thiếu model ${capability}.`);
  }
  let result: Diagnostic;
  let providerId: string;
  if (stage === "model-discovery") {
    providerId = connection.id;
    result = await api.post<Diagnostic>(
      `/modelops/providers/${providerId}/discover`,
      {},
    );
    await requireDiagnostic(api, providerId, result, "discovery");
    for (const model of Object.values(profile.models))
      expect(result.models).toContain(model);
    for (const additional of configuredProfiles(profile).slice(1)) {
      if (additional.api_type === "mineru") continue;
      const extra = await connectionFor(api, additional);
      const discovered = await api.post<Diagnostic>(
        `/modelops/providers/${extra.id}/discover`,
        {},
      );
      await requireDiagnostic(api, extra.id, discovered, "discovery");
      for (const model of Object.values(additional.models))
        expect(discovered.models).toContain(model);
    }
  } else {
    const capability = capabilities.find((value) => stage === `model-${value}`);
    if (!capability) throw new Error("Chặng model không được hỗ trợ.");
    const providers = await api.get<Provider[]>(
      `/modelops/connections/${connection.id}/models`,
    );
    const matches = providers.filter(
      (provider) =>
        provider.is_active &&
        provider.parent_id === connection.id &&
        sameEndpoint(provider.base_url, target) &&
        provider.model_name === target.models[capability] &&
        provider.capabilities.includes(capability),
    );
    if (matches.length !== 1)
      throw new Error(
        `BLOCKED: thêm đúng một model ${target.models[capability]} có chức năng ${capability} dưới nhà cung cấp đã chọn.`,
      );
    providerId = matches[0].id;
    result = await api.post<Diagnostic>(
      `/modelops/providers/${providerId}/probe`,
      { capability },
    );
    await requireDiagnostic(
      api,
      providerId,
      result,
      capability,
      target.api_type === "mineru",
    );
    expect(result.requested_model).toBe(target.models[capability]);
    expect(
      acceptsModelObservation(
        target,
        capability,
        result.requested_model,
        result.observed_model,
      ),
      "Model phản hồi phải trùng model yêu cầu hoặc alias khai báo riêng của provider.",
    ).toBe(true);
    if (capability === "embedding") {
      expect(result.observed_dimension).not.toBeNull();
      expect(result.observed_dimension).toBeGreaterThan(0);
    }
  }
  // Safe observation summary only; no upstream raw response, prompt, key or token.
  const observation = {
    stage,
    mode: "live",
    model: result.requested_model,
    observed_model: result.observed_model,
    diagnostic_id: result.id,
    provider_id: providerId,
    code: result.code,
    upstream_http: result.http_status,
    latency_ms: result.latency_ms,
    observed_dimension: result.observed_dimension,
    total_tokens: result.total_tokens,
    listed_models: stage === "model-discovery" ? result.models : undefined,
  };
  const output = process.env.E2E_OUTPUT;
  if (!output || path.dirname(path.dirname(path.resolve(output))) !== directory)
    throw new Error("Báo cáo phải nằm trong thư mục phiên.");
  writeFileSync(
    path.join(output, "model-observation.json"),
    `${JSON.stringify(observation, null, 2)}\n`,
    "utf8",
  );
  console.log(
    `Model ${result.requested_model || "catalog"}: ${result.code}; HTTP ${result.http_status}; ${result.latency_ms}ms; dimension=${result.observed_dimension ?? "n/a"}`,
  );
});
