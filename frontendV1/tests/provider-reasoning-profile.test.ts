import { describe, expect, it, vi } from "vitest";
import { configureReasoning } from "../e2e/stages/provider-capacity";

describe("explicit provider reasoning profile", () => {
  it("leaves unconfigured providers alone", async () => {
    const api = { json: vi.fn(), post: vi.fn() };
    await configureReasoning(api, "model", undefined);
    expect(api.json).not.toHaveBeenCalled();
  });
  it("persists the declared policy and verifies it", async () => {
    const policy = { mode: "toggle", parameter: "thinking", off_value: false };
    const api = {
      post: vi.fn(),
      json: vi
        .fn()
        .mockResolvedValueOnce({ policy: {} })
        .mockResolvedValueOnce({ policy })
        .mockResolvedValueOnce({ policy }),
    };
    await configureReasoning(api, "model", policy);
    expect(api.json).toHaveBeenNthCalledWith(
      2,
      "PUT",
      "/modelops/providers/model/reasoning",
      { policy },
    );
  });
  it("blocks when the server did not save the policy", async () => {
    const api = {
      post: vi.fn(),
      json: vi.fn().mockResolvedValue({ policy: {} }),
    };
    await expect(
      configureReasoning(api, "model", { mode: "toggle" }),
    ).rejects.toThrow("BLOCKED");
  });
});
