import { expect, test, vi } from "vitest";
import type { AdmissionCase } from "../e2e/stages/admissions-context";
import type { Api, Checkpoint } from "../e2e/stages/session";

vi.mock("../e2e/stages/session", () => ({
  ensureSessionQuota: vi.fn(),
  save: vi.fn(),
  workspace: () => "/workspaces/test",
}));
vi.mock("../e2e/stages/admissions-context", () => ({
  benchmark: { version: "test", cases: [] },
  modelTimeout: vi.fn(),
}));

function fixture() {
  const api = {
    get: vi.fn<Api["get"]>(),
    post: vi.fn<Api["post"]>(),
    wait: vi.fn<Api["wait"]>(),
  };
  const state: Checkpoint = {
    runId: "session",
    mode: "live",
    results: {},
    sources: [],
    admissions: {
      assistant: "assistant",
      documents: {
        floor2026: {
          key: "floor2026",
          publication: { run: "run", document: "doc" },
        },
      },
      queries: { F01: { conversation: "conversation", turn: "turn" } },
    },
  };
  const item: AdmissionCase = {
    id: "F01",
    group: "floor2026",
    scope: "single",
    target_doc: "floor2026",
    question: "Question",
    kind: "answerable",
    expected_numbers: [],
    expected_patterns: [],
    pages: [],
    expected: "",
    rubric: "",
  };
  const completed = {
    id: "turn",
    status: "completed",
    question: item.question,
    result: {
      status: "insufficient_evidence",
      reason: "model_abstained",
      trace: { stage_ms: { generation: 12 } },
    },
  };
  return { api, state, item, completed };
}

function respond(api: ReturnType<typeof fixture>["api"], value: unknown) {
  api.get.mockImplementation(async (url: string) =>
    url.endsWith("/conversations/conversation")
      ? { assistant_id: "assistant", document_ids: ["doc"] }
      : (value as never),
  );
}

test("completed checkpoint is replayed without claiming fresh model latency", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state, item, completed } = fixture();
  respond(api, completed);
  const result = await askAdmissionQuestion(api, state, item, 1000);
  expect(result.origin).toBe("replayed");
  expect(result.firstAttempt).toBe(false);
  expect(result.inferenceMs).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});

test("a missing local turn ID is reconciled, not resubmitted", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state, item, completed } = fixture();
  const query = state.admissions?.queries?.F01;
  if (!query) throw new Error("Missing fixture query");
  query.turn = undefined;
  respond(api, [completed]);
  expect((await askAdmissionQuestion(api, state, item, 1000)).origin).toBe(
    "replayed",
  );
  expect(api.get).toHaveBeenCalledWith(
    "/workspaces/test/conversations/conversation/turns",
  );
  expect(api.post).not.toHaveBeenCalled();
});

test("new abstained result is returned once instead of retried to match gold", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state, item, completed } = fixture();
  const query = state.admissions?.queries?.F01;
  if (!query) throw new Error("Missing fixture query");
  query.turn = undefined;
  respond(api, []);
  api.post.mockResolvedValue(completed);
  const result = await askAdmissionQuestion(api, state, item, 1000);
  expect(result.origin).toBe("fresh");
  expect(result.inferenceMs).toBe(12);
  expect(result.firstAttempt).toBe(true);
  expect(result.answer.status).toBe("insufficient_evidence");
  expect(api.post).toHaveBeenCalledTimes(1);
});

test.each(["failed", "uncertain", "cancelled"])(
  "%s remains terminal without new inference",
  async (status) => {
    const { askAdmissionQuestion } = await import(
      "../e2e/stages/admissions-chat"
    );
    const { api, state, item, completed } = fixture();
    respond(api, { ...completed, status });
    await expect(askAdmissionQuestion(api, state, item, 1000)).rejects.toThrow(
      status,
    );
    expect(api.post).not.toHaveBeenCalled();
  },
);

test("running turn is resumed without new inference", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state, item, completed } = fixture();
  respond(api, { ...completed, status: "running" });
  api.wait.mockResolvedValue(completed);
  const result = await askAdmissionQuestion(api, state, item, 1000);
  expect(result.origin).toBe("resumed");
  expect(result.inferenceMs).toBeNull();
  expect(api.post).not.toHaveBeenCalled();
});

test("failure to inspect an existing turn does not create a request", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { api, state, item } = fixture();
  api.get.mockRejectedValue(new Error("denied"));
  await expect(askAdmissionQuestion(api, state, item, 1000)).rejects.toThrow(
    "denied",
  );
  expect(api.post).not.toHaveBeenCalled();
});
