import { spawnSync } from "node:child_process";
import path from "node:path";
import { afterEach, expect, test, vi } from "vitest";
import {
  askAdmissionQuestion,
  ensureAdmissionsAssistant,
} from "../e2e/stages/admissions-chat";
import { benchmark } from "../e2e/stages/admissions-context";
import {
  planAdmissionsBudget,
  verifyAdmissionsIndex,
} from "../e2e/stages/admissions-policy";
import {
  compileAdmissionDrafts,
  compileAdmissionSource,
  publishAdmissionDraft,
} from "../e2e/stages/admissions-publication";
import type { Api, Checkpoint } from "../e2e/stages/session";

vi.mock("../e2e/stages/session", () => ({
  save: vi.fn(),
  workspace: () => "/workspaces/ws",
  collection: () => "/workspaces/ws/collections/col",
  processing: (
    _s: unknown,
    source: { id: string; revision: string; run: string },
  ) =>
    `/workspaces/ws/collections/col/sources/${source.id}/revisions/${source.revision}/processing-runs/${source.run}`,
  versionBase: (_s: unknown, p: { document: string; version: string }) =>
    `/workspaces/ws/collections/col/compiled-documents/${p.document}/versions/${p.version}`,
}));
afterEach(() => vi.unstubAllEnvs());

type Body = Record<string, unknown>;
type Request = {
  method: string;
  path: string;
  body?: unknown;
  headers?: Record<string, string>;
};
function requireValue<T>(v: T | undefined): T {
  if (v === undefined) throw new Error("Missing fixture value");
  return v;
}

function fixture() {
  const requests: Request[] = [];
  const state: Checkpoint = {
    runId: "test777",
    mode: "live",
    results: {},
    sources: [],
    workspace: "ws",
    runtimeDefaults: {
      chat: "chat",
      embedding: "embed",
      rerank: "rerank",
      ocr: "ocr",
    },
    admissions: { collection: "col", documents: {} },
  };
  const scenario = requireValue(state.admissions);
  for (const [key, doc] of Object.entries(benchmark.documents)) {
    requireValue(scenario.documents)[key] = {
      key,
      source: {
        id: `src_${key}`,
        revision: `rev_${key}`,
        run: `ocr_${key}`,
        file: doc.path,
        sha256: doc.sha256,
      },
    };
  }
  const statuses = new Map<string, string>();
  const previews = new Map<string, { key: string; action: string }>();
  const conversations = new Map<string, Body>();
  const provider = {
    model_name: "chosen-model",
    timeout_seconds: 600,
    capacity_status: "configured",
    token_limits: { context_window_tokens: 131072, max_output_tokens: 16384 },
  };
  let assistant: Body | undefined;
  const options = {
    findingsKey: "",
    wrongReview: false,
    failCompile: false,
    wrongText: false,
    inactiveIndex: false,
    stalePlanner: false,
    missingQuota: false,
  };
  const captured = (
    method: string,
    url: string,
    body?: unknown,
    key?: string,
  ) =>
    requests.push({
      method,
      path: url,
      body,
      headers: key ? { "Idempotency-Key": key } : {},
    });
  const indexInputs = () =>
    Object.keys(benchmark.documents).map((key) => ({
      document_id: `doc_${key}`,
      version_id: `ver_${key}`,
      publication_decision_id: `pub_${key}`,
      bundle_sha256: "a".repeat(64),
      version_state: 3,
    }));
  const get = vi.fn(async (url: string): Promise<unknown> => {
    if (url.startsWith("/modelops/")) return provider;
    if (url.endsWith("/quota"))
      return {
        configured: !options.missingQuota,
        is_blocked: false,
        monthly_token_limit: 20_000_000,
        tokens_used: 0,
        tokens_reserved: 0,
      };
    captured("GET", url);
    const key = Object.keys(benchmark.documents).find((key) =>
      url.includes(key),
    );
    if (url.includes("/text-review"))
      return {
        run_id: `ocr_${key}`,
        version: 0,
        canonical_sha256: (options.wrongText ? "b" : "a").repeat(64),
        units: [{}],
      };
    if (url.includes("/processing-runs/"))
      return {
        status: "completed",
        results_ready: true,
        pages_done: benchmark.documents[key || ""].pages,
        pages_total: benchmark.documents[key || ""].pages,
      };
    if (url.endsWith("/progress"))
      return {
        status: "completed",
        total: 1,
        planner_version: options.stalePlanner
          ? "older"
          : "qnu.compiler.plan/v5",
        segments: [],
      };
    if (url.endsWith("/draft"))
      return { sections: [{}], citations: { [`ocr_${key}:evidence`]: {} } };
    if (url.endsWith("/report"))
      return {
        review_id: `review_${key}`,
        findings:
          options.findingsKey === key ? [{ issue: "source_omitted" }] : [],
      };
    if (url.includes("/reviews/"))
      return {
        id: `review_${key}`,
        compilation_run_id: `cmp_${key}`,
        status: "completed",
        trace: {
          context_resolution_version: 2,
          literal_check_version: 1,
          review_concurrency: 2,
          reference_contract_version: 2,
        },
      };
    if (url.endsWith("/review-gate"))
      return {
        review_id: options.wrongReview ? "another-review" : `review_${key}`,
        report_sha256: "c".repeat(64),
        findings: [],
      };
    if (url.endsWith("/manifest"))
      return {
        run_id: "index",
        inputs: indexInputs(),
        config: { chunk_max_bytes: 2048 },
        chunks: [{ id: "chunk" }],
      };
    if (url.includes("/indexing-runs/"))
      return {
        id: "index",
        status: "completed",
        is_active: !options.inactiveIndex,
        chunks_total: 1,
        provider_id: "embed",
      };
    if (url.endsWith("/published"))
      return {
        version: {
          id: `ver_${key}`,
          bundle_sha256: "a".repeat(64),
          state_version: 3,
        },
        decision: { id: `pub_${key}` },
        content: {},
      };
    if (url.includes("/versions/"))
      return {
        id: `ver_${key}`,
        bundle_sha256: "a".repeat(64),
        status: statuses.get(key || "") || "draft",
      };
    if (url.includes("/compilation-runs/"))
      return { id: `cmp_${key}`, status: "completed", provider_id: "chat" };
    if (url.endsWith("/assistants/assistant")) return assistant;
    if (url.endsWith("/turns")) return [];
    if (url.includes("/conversations/"))
      return conversations.get(requireValue(url.split("/").at(-1)));
    throw new Error(`Unhandled fixture GET ${url}`);
  });
  const post = vi.fn(
    async (url: string, body: Body, idempotency?: string): Promise<unknown> => {
      captured("POST", url, body, idempotency);
      if (url.endsWith("/compilation-runs")) {
        if (options.failCompile) throw new Error("transport stopped");
        const key = String(
          (body.ocr_run_ids as string[] | undefined)?.[0] || "ocr_floor2026",
        ).replace("ocr_", "");
        return { run: { id: `cmp_${key}`, status: "queued" } };
      }
      const key =
        Object.keys(benchmark.documents).find((key) => url.includes(key)) || "";
      if (url.endsWith("/reviews"))
        return { id: `review_${key}`, status: "completed" };
      if (url.endsWith("/compiled-documents")) {
        const docKey = String(body.document_key).split("-test777")[0];
        return {
          document: { id: `doc_${docKey}` },
          version: { id: `ver_${docKey}` },
        };
      }
      if (url.endsWith("/decision-preview")) {
        const id = `preview_${key}_${body.action}`;
        previews.set(id, { key, action: String(body.action) });
        return { id, preview_sha256: "d".repeat(64) };
      }
      if (url.endsWith("/decisions")) {
        const preview = requireValue(previews.get(String(body.preview_id)));
        statuses.set(
          preview.key,
          preview.action === "approve" ? "approved" : "published",
        );
        return { id: `decision_${key}` };
      }
      if (url.endsWith("/indexing-runs")) return { run: { id: "index" } };
      if (url.endsWith("/assistants")) {
        assistant = {
          ...body,
          id: "assistant",
          revision: 1,
          description: "",
          persona: "",
          is_active: true,
        };
        return { id: "assistant" };
      }
      if (url.endsWith("/conversations")) {
        const id = `conversation${conversations.size}`;
        conversations.set(id, body);
        return { id };
      }
      if (url.endsWith("/turns"))
        return {
          id: "turn",
          status: "completed",
          result: { status: "insufficient_evidence", trace: {} },
        };
      throw new Error(`Unhandled fixture POST ${url}`);
    },
  );
  const api = {
    get,
    post,
    waitProgress: vi.fn(async (url: string) => get(url)),
    wait: vi.fn(async (url: string) => get(url)),
    json: vi.fn(async (method: string, url: string, body: Body) => {
      captured(method, url, body);
      assistant = { ...body, id: "assistant", revision: 2 };
      return assistant;
    }),
  } as unknown as Api;
  return {
    api,
    state,
    requests,
    options,
    scenario,
    get,
    post,
    provider,
    driftAssistant: () => {
      assistant = { ...requireValue(assistant), top_k: 5 };
    },
  };
}

function contracts(requests: Request[]) {
  const python = path.resolve(
    "../backendV1/.venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  const result = spawnSync(
    python,
    ["-X", "utf8", "../scripts/check_v1_e2e_contracts.py"],
    { input: JSON.stringify(requests), encoding: "utf8", timeout: 30_000 },
  );
  expect(result.error).toBeUndefined();
  expect(result.status, result.stdout || result.stderr).toBe(0);
  return JSON.parse(result.stdout) as { checked: unknown[] };
}

test("actual three-document runner requests conform to backend routes through publication, index and single/all chat", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  await publishAdmissionDraft(f.api, f.state);
  await verifyAdmissionsIndex(f.api, f.state);
  const budget = planAdmissionsBudget(f.provider);
  await ensureAdmissionsAssistant(f.api, f.state, budget);
  f.driftAssistant();
  await ensureAdmissionsAssistant(f.api, f.state, budget);
  await askAdmissionQuestion(f.api, f.state, benchmark.cases[0], 1000);
  await askAdmissionQuestion(
    f.api,
    f.state,
    requireValue(benchmark.cases.find((c) => c.id === "MX-01")),
    1000,
  );
  const creates = f.requests.filter(
    (r) => r.method === "POST" && r.path.endsWith("/compilation-runs"),
  );
  expect(creates).toHaveLength(3);
  expect(
    f.requests.filter(
      (r) => r.method === "POST" && r.path.endsWith("/reviews"),
    ),
  ).toHaveLength(3);
  for (const request of creates) {
    expect(request.body).toMatchObject({
      auto_review: false,
      structured_output: true,
    });
    expect(Object.values((request.body as Body).text_versions as Body)).toEqual(
      [0],
    );
  }
  expect(contracts(f.requests).checked).toHaveLength(f.requests.length);
}, 30_000);

test("draft-only compiles all documents without review/publication and normal compilation reuses them", async () => {
  const f = fixture();
  await compileAdmissionDrafts(f.api, f.state);
  const posts = () => f.requests.filter((r) => r.method === "POST");
  expect(posts()).toHaveLength(3);
  expect(posts().every((r) => r.path.endsWith("/compilation-runs"))).toBe(true);
  expect(posts().every((r) => (r.body as Body).auto_review === false)).toBe(
    true,
  );
  const before = f.requests.length;
  await expect(publishAdmissionDraft(f.api, f.state)).rejects.toThrow(
    /thiếu review/,
  );
  expect(f.requests.length).toBe(before);
  await compileAdmissionSource(f.api, f.state);
  expect(
    posts().filter((r) => r.path.endsWith("/compilation-runs")),
  ).toHaveLength(3);
  expect(posts().filter((r) => r.path.endsWith("/reviews"))).toHaveLength(3);
});

test("draft-only checks provenance even when review is disabled", async () => {
  const f = fixture();
  await compileAdmissionDrafts(f.api, f.state);
  f.options.wrongText = true;
  const before = f.post.mock.calls.length;
  await expect(compileAdmissionDrafts(f.api, f.state)).rejects.toThrow(/OCR/);
  expect(f.post.mock.calls.length).toBe(before);
});

test("draft-only refuses missing monthly quota before creating any model job", async () => {
  const f = fixture();
  f.options.missingQuota = true;
  await expect(compileAdmissionDrafts(f.api, f.state)).rejects.toThrow(/quota/);
  expect(f.post).not.toHaveBeenCalled();
});

test("explicit fast publication uses skip acknowledgements and never creates reviews", async () => {
  const f = fixture();
  await compileAdmissionDrafts(f.api, f.state);
  vi.stubEnv("E2E_SKIP_REVIEW", "1");
  await publishAdmissionDraft(f.api, f.state);
  const posts = f.requests.filter((r) => r.method === "POST");
  expect(posts.some((r) => r.path.endsWith("/reviews"))).toBe(false);
  const approvals = posts.filter(
    (r) =>
      r.path.endsWith("/decision-preview") &&
      (r.body as Body).action === "approve",
  );
  expect(approvals).toHaveLength(3);
  expect(
    approvals.every(
      (r) => !!(r.body as Body).review_skip && !(r.body as Body).review_ack,
    ),
  ).toBe(true);
  expect(contracts(f.requests).checked).toHaveLength(f.requests.length);
}, 30_000);

test("backend contract rejects the old source/revision payload", () => {
  const python = path.resolve(
    "../backendV1/.venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  const result = spawnSync(
    python,
    ["-X", "utf8", "../scripts/check_v1_e2e_contracts.py"],
    {
      input: JSON.stringify([
        {
          method: "POST",
          path: "/workspaces/ws/collections/col/compilation-runs",
          headers: { "Idempotency-Key": "legacy" },
          body: { source_id: "s", revision_id: "r" },
        },
      ]),
      encoding: "utf8",
      timeout: 30_000,
    },
  );
  expect(result.status).toBe(1);
  expect(result.stdout).toMatch(/topic/);
  expect(result.stdout).toMatch(/ocr_run_ids/);
  expect(result.stdout).toMatch(/extra_forbidden/);
}, 30_000);

test("review findings block before any document is created/published", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  f.options.findingsKey = "info2025";
  const before = f.requests.length;
  await expect(publishAdmissionDraft(f.api, f.state)).rejects.toThrow();
  expect(f.requests.slice(before).some((r) => r.method === "POST")).toBe(false);
});

test("a different publication review cannot be acknowledged using the old checkpoint", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  f.options.wrongReview = true;
  await expect(publishAdmissionDraft(f.api, f.state)).rejects.toThrow(
    /Review gate/,
  );
  expect(f.requests.some((r) => r.path.endsWith("/decisions"))).toBe(false);
});

test("changing pinned OCR text cannot create a new compilation", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  f.options.wrongText = true;
  const before = f.post.mock.calls.length;
  await expect(compileAdmissionSource(f.api, f.state)).rejects.toThrow(/OCR/);
  expect(f.post.mock.calls.length).toBe(before);
});

test("re-running completed stages reuses compile/review/publication instead of sending duplicate model jobs", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  await publishAdmissionDraft(f.api, f.state);
  const before = f.post.mock.calls.length;
  await compileAdmissionSource(f.api, f.state);
  await publishAdmissionDraft(f.api, f.state);
  expect(f.post.mock.calls.length).toBe(before);
});

test("a failed recovery POST keeps history and the same idempotency key", async () => {
  const f = fixture();
  const entry = requireValue(f.scenario.documents).floor2026;
  entry.publication = { run: "cmp_floor2026" };
  f.options.stalePlanner = true;
  f.options.failCompile = true;
  vi.stubEnv("E2E_RECOVER_COMPILATION", "1");
  await expect(compileAdmissionSource(f.api, f.state)).rejects.toThrow(
    "transport stopped",
  );
  await expect(compileAdmissionSource(f.api, f.state)).rejects.toThrow(
    "transport stopped",
  );
  expect(entry.compilationHistory).toBeUndefined();
  expect(entry.publication.run).toBe("cmp_floor2026");
  const keys = f.requests
    .filter((r) => r.method === "POST")
    .map((r) => r.headers?.["Idempotency-Key"]);
  expect(keys).toEqual([
    "test777-floor2026-compile-v5-r1",
    "test777-floor2026-compile-v5-r1",
  ]);
});

test("inactive index is blocked before chat creates any conversation", async () => {
  const f = fixture();
  await compileAdmissionSource(f.api, f.state);
  await publishAdmissionDraft(f.api, f.state);
  f.options.inactiveIndex = true;
  await expect(verifyAdmissionsIndex(f.api, f.state)).rejects.toThrow(
    /index chưa active/,
  );
});

test("all source bindings are checked before starting the first model job", async () => {
  const f = fixture();
  requireValue(requireValue(f.scenario.documents).info2025.source).sha256 =
    "0".repeat(64);
  await expect(compileAdmissionSource(f.api, f.state)).rejects.toThrow(
    /hash nguồn/,
  );
  expect(f.post).not.toHaveBeenCalled();
});
