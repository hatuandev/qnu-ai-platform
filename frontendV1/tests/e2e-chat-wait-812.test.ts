import { readFileSync } from "node:fs";
import { expect, test, vi } from "vitest";
import type { Provider } from "@/features/modelops/types";
import {
  configureTestModelCapacity,
  type ProviderSetupProfile,
} from "../e2e/stages/provider-capacity";

function fixture(wait: boolean | undefined = true) {
  const policy = {
    key_pool_enabled: true,
    wait_for_completion: false,
    retry_owner: "gateway",
    max_key_attempts: 1,
    auth_cooldown_seconds: 600,
    rate_cooldown_seconds: 45,
    fallbacks: { answer: ["alternative"] },
  };
  let saved = { status: "configured", policy };
  const model = {
    id: "chat_model",
    parent_id: "connection",
    model_name: "selected-model",
    base_url: "https://provider.test/v1",
    is_active: true,
    capabilities: ["chat"],
    capacity_status: "configured",
    token_limits: { context_window_tokens: 32768, max_output_tokens: 8192 },
    timeout_seconds: 300,
  } as Provider;
  const profile: ProviderSetupProfile = {
    base_url: model.base_url,
    models: { chat: model.model_name },
    model_runtime: { chat: { wait_for_completion: wait } },
  };
  const api = {
    post: vi.fn(async <T>(): Promise<T> => [model] as T),
    json: vi.fn(
      async <T>(method: string, path: string, body?: unknown): Promise<T> => {
        expect(path).toBe("/modelops/providers/chat_model/resilience");
        if (method === "PUT")
          saved = { status: "configured", policy: body as typeof policy };
        return structuredClone(saved) as T;
      },
    ),
  };
  return { api, profile, policy };
}

test("fresh E2E setup enables completion wait and preserves retry/fallback settings", async () => {
  const { api, profile, policy } = fixture();
  await configureTestModelCapacity(api, "connection", profile, "discovery");
  expect(api.json).toHaveBeenCalledWith(
    "PUT",
    "/modelops/providers/chat_model/resilience",
    { ...policy, wait_for_completion: true },
  );
  expect(
    api.json.mock.calls.filter(([method]) => method === "GET"),
  ).toHaveLength(2);
});

test("profiles without a wait setting do not modify the operator policy", async () => {
  const { api, profile } = fixture(undefined);
  profile.model_runtime = undefined;
  await configureTestModelCapacity(api, "connection", profile, "discovery");
  expect(api.json).not.toHaveBeenCalled();
});

test("failure to save the wait policy is surfaced without retry", async () => {
  const { api, profile } = fixture();
  api.json.mockRejectedValueOnce(new Error("permission_denied"));
  await expect(
    configureTestModelCapacity(api, "connection", profile, "discovery"),
  ).rejects.toThrow("permission_denied");
  expect(api.json).toHaveBeenCalledTimes(1);
});

test("setup rejects a backend that does not persist the requested policy", async () => {
  const { api, profile, policy } = fixture();
  api.json.mockResolvedValue({ status: "configured", policy });
  await expect(
    configureTestModelCapacity(api, "connection", profile, "discovery"),
  ).rejects.toThrow("chờ model");
  expect(
    api.json.mock.calls.filter(([method]) => method === "PUT"),
  ).toHaveLength(1);
});

test("the QNU and router profiles explicitly wait for chat completion", () => {
  const profile = JSON.parse(
    readFileSync(
      new URL("../../scripts/e2e_profiles/qnu-server.json", import.meta.url),
      "utf8",
    ),
  ) as ProviderSetupProfile & {
    additional_chat_provider: ProviderSetupProfile;
  };
  expect(profile.model_runtime?.chat?.wait_for_completion).toBe(true);
  expect(
    profile.additional_chat_provider.model_runtime?.chat?.wait_for_completion,
  ).toBe(true);
});
