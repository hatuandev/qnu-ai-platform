import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { expect, test, vi } from "vitest";
import type { Provider } from "@/features/modelops/types";
import {
  configureTestModelCapacity,
  type ProviderSetupProfile,
} from "../e2e/stages/provider-capacity";

const profile = JSON.parse(
  readFileSync(
    new URL("../../scripts/e2e_profiles/qnu-server.json", import.meta.url),
    "utf8",
  ),
) as ProviderSetupProfile;
function requiredModel(models: Provider[], capability: string) {
  const model = models.find((row) => row.capabilities.includes(capability));
  if (!model?.token_limits)
    throw new Error("Fixture requires configured limits");
  return { ...model, token_limits: model.token_limits };
}
function requiredOcrBudget() {
  const value = profile.model_runtime?.ocr?.ocr_page_input;
  if (!value) throw new Error("Profile requires declared OCR budget");
  return value;
}
function fixture() {
  const models = Object.entries(profile.models).map(
    ([capability, name], index) =>
      ({
        id: `model_${index}`,
        parent_id: "connection_test",
        model_name: name,
        base_url: profile.base_url,
        is_active: true,
        capabilities: [capability],
        capacity_status: "configured",
        capacity_basis: "server_reported",
        timeout_seconds: 60,
        embedding_dimension: capability === "embedding" ? 1024 : null,
        embedding_dimension_status:
          capability === "embedding" ? "configured" : "unknown",
        token_limits: {
          context_window_tokens:
            capability === "chat"
              ? 131072
              : capability === "ocr"
                ? 16384
                : 8192,
          max_output_tokens:
            capability === "chat" ? 16384 : capability === "ocr" ? 8192 : null,
          max_input_tokens: null,
          ocr_page_input: null,
        },
      }) as Provider,
  );
  const post = vi.fn(
    async <T>(_path: string, _body: unknown): Promise<T> =>
      structuredClone(models) as T,
  );
  let policy = { wait_for_completion: false };
  const json = vi.fn(
    async <T>(method: string, path: string, body?: unknown): Promise<T> => {
      if (path.endsWith("/resilience")) {
        if (method === "PUT") policy = body as typeof policy;
        return { status: "configured", policy } as T;
      }
      return undefined as T;
    },
  );
  return { models, api: { post, json } };
}

test("syncs current server metadata before applying explicit E2E runtime settings", async () => {
  const { api, models } = fixture();
  await configureTestModelCapacity(
    api,
    "connection_test",
    profile,
    "diag_current",
  );
  expect(api.post).toHaveBeenCalledExactlyOnceWith(
    "/modelops/connections/connection_test/sync-capacity",
    { check_id: "diag_current", model_names: Object.values(profile.models) },
  );
  const qwen = requiredModel(models, "chat");
  expect(api.json).toHaveBeenCalledWith(
    "PATCH",
    `/modelops/providers/${qwen.id}`,
    { timeout_seconds: 300 },
  );
  const ocr = requiredModel(models, "ocr");
  expect(api.json).toHaveBeenCalledWith(
    "PATCH",
    `/modelops/providers/${ocr.id}`,
    {
      timeout_seconds: 180,
      token_limits: {
        ...ocr.token_limits,
        ocr_page_input: profile.model_runtime?.ocr?.ocr_page_input,
      },
    },
  );
  const rerank = requiredModel(models, "rerank");
  expect(api.json).not.toHaveBeenCalledWith(
    "PATCH",
    `/modelops/providers/${rerank.id}`,
    expect.anything(),
  );
});

test("does not replace operator input/OCR settings that are already configured", async () => {
  const { api, models } = fixture();
  const ocr = requiredModel(models, "ocr");
  ocr.token_limits.ocr_page_input = {
    ...requiredOcrBudget(),
    max_image_width: 1200,
  };
  const rerank = requiredModel(models, "rerank");
  rerank.token_limits.max_input_tokens = 2048;
  await configureTestModelCapacity(
    api,
    "connection_test",
    profile,
    "diag_current",
  );
  expect(api.json).not.toHaveBeenCalledWith(
    "PATCH",
    `/modelops/providers/${rerank.id}`,
    expect.anything(),
  );
  expect(api.json).toHaveBeenCalledWith(
    "PATCH",
    `/modelops/providers/${ocr.id}`,
    { timeout_seconds: 180 },
  );
});

test("missing saved discovery fails before any write", async () => {
  const { api } = fixture();
  await expect(
    configureTestModelCapacity(api, "connection_test", profile, null),
  ).rejects.toThrow("snapshot discovery");
  expect(api.post).not.toHaveBeenCalled();
  expect(api.json).not.toHaveBeenCalled();
});

test("missing capacity is still blocked and never replaced with guessed values", async () => {
  const { api, models } = fixture();
  models[0].capacity_status = "unknown";
  models[0].token_limits = null;
  await expect(
    configureTestModelCapacity(api, "connection_test", profile, "diag_current"),
  ).rejects.toThrow("chưa đồng bộ đúng capacity");
  expect(api.json).not.toHaveBeenCalled();
});

test("a model outside the selected connection cannot receive profile overrides", async () => {
  const { api, models } = fixture();
  models[0].parent_id = "another_connection";
  await expect(
    configureTestModelCapacity(api, "connection_test", profile, "diag_current"),
  ).rejects.toThrow("chưa đồng bộ đúng capacity");
  expect(api.json).not.toHaveBeenCalled();
});

test("sync conflicts remain errors with no fallback capacity", async () => {
  const { api } = fixture();
  api.post.mockRejectedValue(new Error("discovery_capacity_conflict"));
  await expect(
    configureTestModelCapacity(api, "connection_test", profile, "diag_current"),
  ).rejects.toThrow("discovery_capacity_conflict");
  expect(api.json).not.toHaveBeenCalled();
  expect(api.post).toHaveBeenCalledTimes(1);
});

test("a profile without runtime overrides only imports the server limits", async () => {
  const { api } = fixture();
  await configureTestModelCapacity(
    api,
    "connection_test",
    { base_url: profile.base_url, models: profile.models },
    "diag_current",
  );
  expect(api.json).not.toHaveBeenCalled();
});

test("the QNU profile OCR declaration is pinned to the actual backend prompt", () => {
  const code = readFileSync(
    new URL("../../backendV1/qnu/domains/ocr/config.py", import.meta.url),
    "utf8",
  );
  const prompt = code.match(/^OCR_PROMPT = "([^"\n]+)"/m)?.[1];
  if (!prompt)
    throw new Error("OCR prompt format changed; review the budget declaration");
  expect(requiredOcrBudget().prompt_sha256).toBe(
    createHash("sha256").update(prompt, "utf8").digest("hex"),
  );
});

test("an unselected chat alternative may remain unknown without fabricating limits", async () => {
  const { api, models } = fixture();
  models[0].capacity_status = "unknown";
  models[0].token_limits = null;
  const chatOnly = { ...profile, models: { chat: profile.models.chat } };
  await configureTestModelCapacity(
    api,
    "connection_test",
    chatOnly,
    "diag_current",
    false,
  );
  expect(api.json).not.toHaveBeenCalled();
  await expect(
    configureTestModelCapacity(
      api,
      "connection_test",
      chatOnly,
      "diag_current",
    ),
  ).rejects.toThrow("chưa đồng bộ đúng capacity");
  models[0].parent_id = "another_connection";
  await expect(
    configureTestModelCapacity(
      api,
      "connection_test",
      chatOnly,
      "diag_current",
      false,
    ),
  ).rejects.toThrow("chưa đồng bộ đúng capacity");
});
