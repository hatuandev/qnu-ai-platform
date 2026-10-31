import { readFileSync } from "node:fs";
import { afterEach, expect, test, vi } from "vitest";
import { liveDefaults } from "../e2e/stages/live-defaults";
import type { Api, Checkpoint } from "../e2e/stages/session";

const fixture = vi.hoisted(() => ({ limit: 20_000_000 as unknown }));
vi.mock("node:fs", async (original) => {
  const fs = await original<typeof import("node:fs")>();
  return {
    ...fs,
    readFileSync: vi.fn((file: string, encoding: BufferEncoding) =>
      file === "quota-test-profile.json"
        ? JSON.stringify({ test_monthly_token_limit: fixture.limit })
        : fs.readFileSync(file, encoding),
    ),
  };
});
vi.mock("../e2e/stages/session", () => ({
  directory: "test-session",
  sha256: vi.fn(),
}));
afterEach(() => vi.unstubAllEnvs());

test("the checked-in QNU test profile declares the approved twenty million", () => {
  const profile = JSON.parse(
    readFileSync("../scripts/e2e_profiles/qnu-server.json", "utf8"),
  );
  expect(profile.test_monthly_token_limit).toBe(20_000_000);
});

test.each([5_000_000, 20_000_000])(
  "navigation accepts an explicitly configured allowance of %s",
  async (limit) => {
    fixture.limit = limit;
    vi.stubEnv("E2E_MODEL_PROFILE", "quota-test-profile.json");
    // Stop at the first API boundary: no model calls, quota writes or real DB.
    const api = {
      get: vi.fn().mockRejectedValue(new Error("catalog boundary")),
    };
    await expect(
      liveDefaults(api as unknown as Api, {} as Checkpoint),
    ).rejects.toThrow("catalog boundary");
    expect(api.get).toHaveBeenCalledWith("/modelops/connections");
  },
);

test.each([0, -1, 1.5, 20_000_001, "20000000", null])(
  "invalid allowance %s blocks before any API request",
  async (limit) => {
    fixture.limit = limit;
    vi.stubEnv("E2E_MODEL_PROFILE", "quota-test-profile.json");
    const api = { get: vi.fn() };
    await expect(
      liveDefaults(api as unknown as Api, {} as Checkpoint),
    ).rejects.toThrow("tối đa 20.000.000");
    expect(api.get).not.toHaveBeenCalled();
  },
);
