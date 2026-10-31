import { expect } from "@playwright/test";
import type { LiveProfile } from "./live-profile";
import { configureTestModelCapacity } from "./provider-capacity";
import type { Api, Checkpoint } from "./session";

export async function verifyRouterProvider(
  api: Api,
  state: Checkpoint,
  profile: LiveProfile,
) {
  const target = profile.additional_chat_provider;
  if (!target) return;
  const setup = state.routerProviderSetup;
  if (!setup)
    throw new Error("BLOCKED: chạy provider-setup để nhập key 9router trước.");
  const base = `/modelops/connections/${setup.connectionId}`;
  const connection = await api.get<{ base_url: string; is_active: boolean }>(
    base,
  );
  expect(connection.base_url.replace(/\/+$/, "")).toBe(
    target.base_url.replace(/\/+$/, ""),
  );
  expect(connection.is_active).toBe(true);
  const keys = await api.get<{ id: string; status: string }[]>(
    `/modelops/providers/${setup.connectionId}/keys`,
  );
  expect(
    keys.some((key) => key.id === setup.keyId && key.status === "active"),
  ).toBe(true);
  const check = await api.post<{
    ok: boolean;
    models: string[];
    check_id: string | null;
    code: string;
    http_status: number | null;
  }>(`${base}/test`, { key_id: setup.keyId });
  if (!check.ok)
    throw new Error(
      `9router FAIL: code=${check.code}, upstream_http=${check.http_status ?? "unknown"}`,
    );
  expect(check.http_status).toBe(200);
  expect(check.models).toContain(target.models.chat);
  const models = await api.get<
    {
      id: string;
      model_name: string;
      parent_id: string;
      capabilities: string[];
      is_active: boolean;
    }[]
  >(`${base}/models`);
  const matching = models.filter(
    (row) => row.model_name === target.models.chat,
  );
  expect(matching.length).toBeLessThanOrEqual(1);
  const selected =
    matching[0] ??
    (await api.post<{
      id: string;
      parent_id: string;
      capabilities: string[];
      is_active: boolean;
    }>(`${base}/models`, {
      model_name: target.models.chat,
      capabilities: ["chat"],
      discovery_check_id: check.check_id,
    }));
  expect(selected.parent_id).toBe(setup.connectionId);
  expect(selected.is_active).toBe(true);
  expect(selected.capabilities).toContain("chat");
  await configureTestModelCapacity(
    api,
    setup.connectionId,
    target,
    check.check_id,
    state.chatSelection === "router",
  );
  setup.modelsRegistered = true;
}
