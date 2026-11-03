import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import type { LiveProfile } from "./live-profile";
import { configureTestModelCapacity } from "./provider-capacity";
import { verifyRouterProvider } from "./router-provider";
import { authenticate, checkpoint, save } from "./session";

test.use({ trace: "off", video: "off", screenshot: "off" });

test("QNU nhà cung cấp: tạo, khóa, kết nối, model và sidebar", async ({
  page,
}) => {
  test.setTimeout(360_000);
  const state = checkpoint();
  if (state.mode !== "live" || !state.providerSetup)
    throw new Error(
      "BLOCKED: chạy provider-setup qua runner trong phiên live.",
    );
  const profileFile = process.env.E2E_MODEL_PROFILE;
  if (!profileFile) throw new Error("Thiếu profile.");
  const profile = JSON.parse(readFileSync(profileFile, "utf8")) as LiveProfile;
  const api = await authenticate(page);
  const id = state.providerSetup.connectionId;
  const base = `/modelops/connections/${id}`;
  const connection = await api.get<{
    id: string;
    name: string;
    base_url: string;
    is_active: boolean;
  }>(base);
  expect(connection.base_url.replace(/\/+$/, "")).toBe(
    profile.base_url.replace(/\/+$/, ""),
  );
  expect(connection.is_active).toBe(true);
  const keys = await api.get<{ id: string; status: string }[]>(
    `/modelops/providers/${id}/keys`,
  );
  expect(
    keys.some(
      (key) => key.id === state.providerSetup?.keyId && key.status === "active",
    ),
  ).toBe(true);

  // Verify the provider edit contract without leaving renamed settings on retry.
  try {
    const edited = await api.json<{ name: string }>("PATCH", base, {
      name: `${connection.name.slice(0, 100)} kiểm tra`,
    });
    expect(edited.name).toBe(`${connection.name.slice(0, 100)} kiểm tra`);
    expect((await api.get<{ name: string }>(base)).name).toBe(edited.name);
  } finally {
    await api.json("PATCH", base, { name: connection.name });
  }
  const checked = await api.post<{
    ok: boolean;
    code: string;
    http_status: number | null;
    models: string[];
    key_id: string;
    check_id: string | null;
  }>(`${base}/test`, { key_id: state.providerSetup.keyId });
  if (!checked.ok)
    throw new Error(
      `Provider test FAIL: code=${checked.code}, upstream_http=${checked.http_status ?? "unknown"}`,
    );
  expect(checked.code).toBe("diagnostic_ok");
  expect(checked.http_status).toBe(200);
  expect(checked.key_id).toBe(state.providerSetup.keyId);
  for (const model of Object.values(profile.models))
    expect(checked.models).toContain(model);

  for (const [capability, model] of Object.entries(profile.models)) {
    const registered = await api.get<
      {
        id: string;
        model_name: string;
        parent_id: string;
        capabilities: string[];
      }[]
    >(`${base}/models`);
    let selected = registered.find((row) => row.model_name === model);
    if (!selected)
      selected = await api.post(`${base}/models`, {
        model_name: model,
        capabilities: [capability],
        discovery_check_id: checked.check_id,
      });
    expect(selected?.parent_id).toBe(id);
    expect(selected?.capabilities).toContain(capability);
  }
  const rows = await api.get<{ id: string; model_name: string }[]>(
    `${base}/models`,
  );
  expect(
    rows.filter((row) =>
      Object.values(profile.models).includes(row.model_name),
    ),
  ).toHaveLength(Object.keys(profile.models).length);
  await configureTestModelCapacity(api, id, profile, checked.check_id);
  console.log(
    "Đã lưu capacity từ server và thông số vận hành của profile E2E; tiếp tục kiểm từng model.",
  );
  // Check parent disable enforcement, and always restore it before model inference tests.
  try {
    await api.json("PATCH", base, { is_active: false });
    const chat = rows.find((row) => row.model_name === profile.models.chat);
    if (!chat) throw new Error("Thiếu model chat dưới nhà cung cấp.");
    const probe = await api.raw(
      "POST",
      `/modelops/providers/${chat.id}/probe`,
      { capability: "chat" },
    );
    expect(probe.status()).toBe(409);
    expect(((await probe.json()) as { code: string }).code).toBe(
      "provider_inactive",
    );
  } finally {
    await api.json("PATCH", base, { is_active: true });
  }
  await page.reload();
  await page.getByRole("link", { name: "Nhà cung cấp", exact: true }).click();
  await expect(page).toHaveURL(/\/providers\/?(?:\?.*)?$/);
  // Exercise the real FE creation form with a disposable, credential-free provider.
  const temporaryName = `UI provider E2E ${state.runId}`;
  const temporaryEndpoint = "http://127.0.0.1:9/v1";
  const existingUi = await api.get<
    { id: string; name: string; base_url: string }[]
  >("/modelops/connections");
  for (const previous of existingUi.filter(
    (row) =>
      row.name === temporaryName &&
      row.base_url === temporaryEndpoint &&
      row.id !== id,
  )) {
    await api.json("DELETE", `/modelops/connections/${previous.id}`);
  }
  await page.getByRole("button", { name: "Thêm mới", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Tên hiển thị", { exact: true }).fill(temporaryName);
  await dialog
    .getByLabel("Địa chỉ API", { exact: true })
    .fill(temporaryEndpoint);
  const createdResponse = page.waitForResponse(
    (response) =>
      response.url().endsWith("/modelops/connections") &&
      response.request().method() === "POST",
  );
  await dialog
    .getByRole("button", { name: "Lưu nhà cung cấp", exact: true })
    .click();
  const created = await createdResponse;
  expect(created.status()).toBe(201);
  const uiProvider = (await created.json()) as {
    id: string;
    name: string;
    base_url: string;
  };
  expect(uiProvider.name).toBe(temporaryName);
  expect(uiProvider.base_url).toBe(temporaryEndpoint);
  expect(uiProvider.id).not.toBe(id);
  try {
    await expect(
      page.getByRole("heading", { name: temporaryName, exact: true }),
    ).toBeVisible();
    const stored = await api.get<{ name: string }>(
      `/modelops/connections/${uiProvider.id}`,
    );
    expect(stored.name).toBe(temporaryName);
  } finally {
    await api.json("DELETE", `/modelops/connections/${uiProvider.id}`);
  }
  expect(
    (await api.raw("GET", `/modelops/connections/${uiProvider.id}`)).status(),
  ).toBe(404);
  await page.goto("/providers");
  await expect(
    page.getByText(connection.name, { exact: true }).first(),
  ).toBeVisible();
  await page.goto(`/providers/${id}`);
  await expect(
    page.getByRole("heading", { name: connection.name, exact: true }),
  ).toBeVisible();
  for (const model of Object.values(profile.models))
    await expect(page.getByText(model, { exact: true }).first()).toBeVisible();
  state.providerSetup.modelsRegistered = true;
  if (profile.additional_ocr_provider) {
    const ocr = profile.additional_ocr_provider;
    const setup = state.ocrProviderSetup;
    if (!setup)
      throw new Error("BLOCKED: thiếu kết nối MinerU từ provider-setup.");
    const ocrBase = `/modelops/connections/${setup.connectionId}`;
    const registeredConnection = await api.get<{
      api_type: string;
      base_url: string;
    }>(ocrBase);
    expect(registeredConnection.api_type).toBe("mineru");
    expect(registeredConnection.base_url).toBe(ocr.base_url);
    let models = await api.get<
      { model_name: string; provider_type: string; capabilities: string[] }[]
    >(`${ocrBase}/models`);
    if (!models.some((m) => m.model_name === ocr.models.ocr)) {
      await api.post(`${ocrBase}/models`, {
        model_name: ocr.models.ocr,
        capabilities: ["ocr"],
      });
      models = await api.get(`${ocrBase}/models`);
    }
    const model = models.filter((m) => m.model_name === ocr.models.ocr);
    expect(model).toHaveLength(1);
    expect(model[0].provider_type).toBe("mineru");
    expect(model[0].capabilities).toEqual(["ocr"]);
    setup.modelsRegistered = true;
  }
  await verifyRouterProvider(api, state, profile);
  console.info(
    `Mặc định chat/biên soạn: ${state.chatSelection === "router" ? profile.additional_chat_provider?.models.chat : profile.models.chat}`,
  );
  save(state);
});
