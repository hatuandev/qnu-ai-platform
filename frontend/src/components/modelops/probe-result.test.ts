import assert from "node:assert/strict";
import test from "node:test";
import type { SingleModelTestResult } from "../../types/modelops.ts";
import {
  formatProbeDetail,
  formatProbeStatus,
  getConfiguredCapabilities,
} from "./probe-result";

const base: SingleModelTestResult = {
  model_name: "opaque",
  success: false,
  status: "error",
  latency_ms: 1,
  message: "Provider error",
  tested_at: "2026-10-13T00:00:00Z",
};

test("protocol errors do not become 404", () => {
  assert.equal(
    formatProbeDetail({ ...base, http_status: 200 }),
    "Chưa kiểm chứng · HTTP 200: Provider error",
  );
  assert.ok(!formatProbeDetail(base).includes("404"));
});
test("token and authentication errors remain distinct", () => {
  assert.equal(
    formatProbeStatus({ ...base, error_code: "MODEL_OUTPUT_BUDGET_EXHAUSTED" }),
    "Chưa đủ token",
  );
  assert.equal(
    formatProbeStatus({ ...base, http_status: 403 }),
    "Lỗi xác thực",
  );
  assert.equal(
    formatProbeStatus({ ...base, error_code: "PROVIDER_TIMEOUT" }),
    "Hết thời gian",
  );
});
test("catalogue and service health are not inference evidence", () => {
  assert.equal(
    formatProbeStatus({
      ...base,
      success: true,
      status: "available",
      verification_scope: "catalogue",
    }),
    "Có trong danh mục",
  );
  assert.equal(
    formatProbeStatus({
      ...base,
      success: true,
      status: "available",
      verification_scope: "health",
    }),
    "Dịch vụ phản hồi",
  );
});

test("model metadata overrides spelling and legacy spec", () => {
  const provider = {
    id: "p",
    model_specs: { "bge-looking": { type: "embedding" } },
    model_capabilities: {
      "bge-looking": {
        probe_role: "chat" as const,
        vision: false,
        reasoning: true,
      },
    },
  };
  const capability = getConfiguredCapabilities(provider, "bge-looking");
  assert.equal(capability.isEmbedding, false);
  assert.equal(capability.isChat, true);
  assert.equal(capability.hasReasoning, true);
});

test("declared opaque reranker works without name heuristics", () => {
  const provider = {
    id: "p",
    model_specs: { opaque: { type: "reranker" } },
  };
  assert.equal(getConfiguredCapabilities(provider, "opaque").isReranker, true);
});
