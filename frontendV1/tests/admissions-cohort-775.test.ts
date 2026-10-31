import { beforeEach, expect, test, vi } from "vitest";
import type { Api, Checkpoint } from "../e2e/stages/session";

const capture = vi.hoisted(() => ({
  reports: [] as {
    records: { status: string; origin?: string; dispatched?: boolean }[];
  }[],
  checks: 0,
}));
vi.mock("node:fs", () => ({
  writeFileSync: (_p: string, value: string) =>
    capture.reports.push(JSON.parse(value)),
}));
vi.mock("@playwright/test", async () => {
  const { expect } = await import("vitest");
  return {
    expect,
    test: { step: async (_s: string, fn: () => Promise<void>) => fn() },
  };
});
vi.mock("../e2e/stages/session", () => ({
  save: vi.fn(),
  workspace: () => "/workspaces/ws",
}));
vi.mock("../e2e/stages/admissions-context", () => ({
  benchmark: {
    version: "cohort-test",
    documents: {},
    cases: ["one", "two", "three"].map((id) => ({
      id,
      scope: "single",
      target_doc: "doc",
      group: "test",
      question: `Question ${id}`,
    })),
  },
  modelTimeout: () => 1000,
}));
vi.mock("../e2e/stages/admissions-policy", () => ({
  fingerprint: (x: unknown) => JSON.stringify(x),
  freezeCohort: (s: Checkpoint) => {
    present(s.admissions).cohort = { fingerprint: "fixed" };
  },
  planAdmissionsBudget: () => ({
    context_max_bytes: 32768,
    input_tokens_plan: 49152,
    max_output_tokens: 4096,
  }),
  requireAdmissionsQuota: vi.fn(),
  verifyAdmissionsIndex: () => ({
    published: [],
    manifest: { config: { chunk_max_bytes: 2048 } },
  }),
}));
vi.mock("../e2e/stages/admissions-evaluation", () => ({
  checkAdmissionAnswer: () => {
    capture.checks++;
    if (capture.checks === 1) throw new Error("Không chứng minh được fact");
  },
}));

function present<T>(value: T | null | undefined): T {
  if (value === null || value === undefined)
    throw new Error("Missing fixture value");
  return value;
}

function setup(failDispatch = false) {
  const state: Checkpoint = {
    runId: "test",
    mode: "live",
    results: {},
    sources: [],
    runtimeDefaults: {
      chat: "chat",
      rerank: "rerank",
      embedding: "embed",
      ocr: "ocr",
    },
    admissions: {
      collection: "col",
      combinedIndex: "idx",
      assistant: "assistant",
      documents: {
        doc: { key: "doc", publication: { run: "cmp", document: "doc" } },
      },
    },
  };
  let sequence = 0;
  const api = {
    get: vi.fn(async (url: string) => {
      if (url.includes("/providers/"))
        return {
          model_name: "model",
          capacity_status: "configured",
          token_limits: { max_input_tokens: 8192 },
        };
      if (url.endsWith("/assistants/assistant"))
        return {
          id: "assistant",
          revision: 1,
          collection_id: "col",
          chat_provider_id: "chat",
          top_k: 20,
          history_turns: 0,
          max_output_tokens: 4096,
          rag_policy: {
            retrieval_mode: "hybrid_rerank",
            candidate_k: 50,
            context_window: 0,
            context_max_bytes: 32768,
            rerank_provider_id: "rerank",
          },
        };
      if (url.endsWith("/turns")) return [];
      return { assistant_id: "assistant", document_ids: ["doc"] };
    }),
    post: vi.fn(async (url: string) => {
      if (url.endsWith("/conversations"))
        return { id: `conversation-${++sequence}` };
      if (failDispatch) throw new Error("POST HTTP 429, code=quota_exceeded");
      return {
        id: `turn-${sequence}`,
        status: "completed",
        result: {
          status: "answered",
          trace: {
            prompt_version: "v1",
            configuration_hash: "fixed",
            stage_ms: {},
          },
        },
      };
    }),
    wait: vi.fn(),
    json: vi.fn(),
  };
  return { state, api };
}

beforeEach(() => {
  capture.reports = [];
  capture.checks = 0;
});

test("the actual cohort loop runs subsequent cases after a gold failure, then fails in aggregate", async () => {
  const { questionAdmissionDraft } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state } = setup();
  await expect(
    questionAdmissionDraft(api as unknown as Api, state),
  ).rejects.toThrow();
  expect(
    api.post.mock.calls.filter(([p]) => p.endsWith("/turns")),
  ).toHaveLength(3);
  expect(present(capture.reports.at(-1)).records.map((r) => r.status)).toEqual([
    "FAIL",
    "PASS",
    "PASS",
  ]);
  expect(api.json).not.toHaveBeenCalled();
});

test("a failed fresh dispatch is counted and infrastructure failure leaves later questions NOT_RUN", async () => {
  const { questionAdmissionDraft } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state } = setup(true);
  await expect(
    questionAdmissionDraft(api as unknown as Api, state),
  ).rejects.toThrow();
  expect(
    api.post.mock.calls.filter(([p]) => p.endsWith("/turns")),
  ).toHaveLength(1);
  const records = present(capture.reports.at(-1)).records;
  expect(records.map((r) => r.status)).toEqual(["FAIL", "NOT_RUN", "NOT_RUN"]);
  expect(records[0]).toMatchObject({ origin: "fresh", dispatched: true });
});
