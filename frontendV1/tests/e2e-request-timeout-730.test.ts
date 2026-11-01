import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import type { Page } from "@playwright/test";
import { afterAll, beforeAll, test, vi } from "vitest";

let Api: typeof import("../e2e/stages/session").Api;
const temporary = mkdtempSync(path.join(tmpdir(), "qnu-e2e-timeout-730-"));
const runId = "aabbcc112233";
const directory = path.join(temporary, runId);

beforeAll(async () => {
  mkdirSync(directory);
  writeFileSync(
    path.join(directory, "manifest.json"),
    JSON.stringify({
      run_id: runId,
      mode: "live",
      cleaned: false,
      ports: { api: 12345, mock: 12346, frontend: 12347 },
    }),
  );
  vi.stubEnv("E2E_SESSION", directory);
  vi.stubEnv("E2E_STAGE", "compilation");
  ({ Api } = await import("../e2e/stages/session"));
});

afterAll(() => {
  vi.unstubAllEnvs();
  assert.equal(path.dirname(temporary), path.resolve(tmpdir()));
  assert.ok(path.basename(temporary).startsWith("qnu-e2e-timeout-730-"));
  rmSync(temporary, { recursive: true });
});

function fixture(status = 200) {
  const fetch = vi.fn().mockResolvedValue({
    ok: () => status === 200,
    status: () => status,
    json: async () =>
      status === 200
        ? { status: "completed" }
        : { code: "chat_provider_uncertain" },
  });
  const page = { request: { fetch } } as unknown as Page;
  return { fetch, api: new Api(page, "synthetic-session-token") };
}

test("ordinary requests retain their default timeout, auth and idempotency", async () => {
  const { api, fetch } = fixture();
  await api.post("/workspaces", { code: "synthetic" }, "ordinary-once");
  const [url, request] = fetch.mock.calls[0];
  assert.equal(url, "http://127.0.0.1:12345/platform/v1alpha1/workspaces");
  assert.equal(request.timeout, 180_000);
  assert.equal(request.headers.Authorization, "Bearer synthetic-session-token");
  assert.equal(request.headers["Idempotency-Key"], "ordinary-once");
  assert.deepEqual(request.data, { code: "synthetic" });
});

test("review can wait beyond 180s without losing its pinned body or request key", async () => {
  const { api, fetch } = fixture();
  const body = { provider_id: "synthetic-provider", max_output_tokens: 8192 };
  const result = await api.post(
    "/workspaces/synthetic/reviews",
    body,
    "explicit-review-once",
    330_000,
  );
  assert.deepEqual(result, { status: "completed" });
  assert.equal(fetch.mock.calls.length, 1);
  const request = fetch.mock.calls[0][1];
  assert.equal(request.timeout, 330_000);
  assert.equal(request.headers["Idempotency-Key"], "explicit-review-once");
  assert.deepEqual(request.data, body);
});

test("uncertain review response surfaces its error without automatic resubmission", async () => {
  const { api, fetch } = fixture(504);
  await assert.rejects(
    api.post(
      "/workspaces/synthetic/reviews",
      {},
      "explicit-review-once",
      330_000,
    ),
    /HTTP 504, code=chat_provider_uncertain/,
  );
  assert.equal(fetch.mock.calls.length, 1);
});

test("transport failure never exposes Authorization or the Playwright request log", async () => {
  const { api, fetch } = fixture();
  fetch.mockRejectedValue(
    new Error(
      "connect ECONNREFUSED\nAuthorization: Bearer synthetic-session-token\nprivate request body",
    ),
  );
  try {
    await api.get("/workspaces/synthetic");
    assert.fail("Expected transport failure");
  } catch (error) {
    assert.ok(error instanceof Error);
    assert.match(error.message, /không kết nối được API/);
    assert.doesNotMatch(
      error.message,
      /Bearer|synthetic-session-token|private request body/,
    );
    assert.equal(error.cause, undefined);
  }
  assert.equal(fetch.mock.calls.length, 1);
});
