import { readFileSync } from "node:fs";
import { expect, test, vi } from "vitest";
import type {
  AdmissionCase,
  BenchmarkMultiDocs,
} from "../e2e/stages/admissions-context";
import {
  type Answer,
  checkAdmissionAnswer,
  hasNumber,
} from "../e2e/stages/admissions-evaluation";
import {
  fingerprint,
  freezeCohort,
  planAdmissionsBudget,
  requireAdmissionsQuota,
  verifyAdmissionsIndex,
} from "../e2e/stages/admissions-policy";
import type { Api, Checkpoint } from "../e2e/stages/session";

vi.mock("../e2e/stages/session", () => ({
  save: vi.fn(),
  workspace: () => "/workspaces/ws",
  collection: () => "/workspaces/ws/collections/col",
}));
vi.mock("../e2e/stages/admissions-context", async () => {
  const { readFileSync } = await import("node:fs");
  return {
    benchmark: JSON.parse(
      readFileSync("e2e/data/admissions-multi-docs.json", "utf8"),
    ),
    context: (s: unknown) => s,
    modelTimeout: vi.fn(),
  };
});

const benchmark = JSON.parse(
  readFileSync("e2e/data/admissions-multi-docs.json", "utf8"),
) as BenchmarkMultiDocs;
const original = JSON.parse(
  readFileSync("e2e/data/admissions-floor-2026.json", "utf8"),
) as { cases: AdmissionCase[] };

function present<T>(value: T | null | undefined): T {
  if (value === null || value === undefined)
    throw new Error("Missing fixture value");
  return value;
}

function fixture() {
  const state: Checkpoint = {
    runId: "test",
    mode: "live",
    sources: [],
    results: {},
    workspace: "ws",
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
      documents: {},
      indexInputs: [],
    },
  };
  for (const [key, meta] of Object.entries(benchmark.documents)) {
    present(present(state.admissions).documents)[key] = {
      key,
      source: {
        id: key,
        revision: `${key}-rev`,
        run: "ocr",
        file: meta.path,
        sha256: meta.sha256,
      },
      publication: { run: "cmp", document: key, version: `${key}-ver` },
    };
    present(present(state.admissions).indexInputs).push({
      document_id: key,
      version_id: `${key}-ver`,
      publication_decision_id: `${key}-pub`,
      bundle_sha256: `${key}-bundle`,
      version_state: 3,
    });
  }
  const item = present(benchmark.cases.find((c) => c.id === "MX-01"));
  const sources = ["info2025", "floor2026"].map((key, n) => {
    const refs = ["subject", "header", "value"].map((v) => `${key}:${v}`);
    const text = n
      ? ["Quản lý giáo dục", "Điểm thi THPT", "15"]
      : ["Quản lý giáo dục", "Chỉ tiêu", "50"];
    return {
      evidence_id: `E${n + 1}`,
      document_id: key,
      version_id: `${key}-ver`,
      publication_decision_id: `${key}-pub`,
      text: text.join(" "),
      citations: Object.fromEntries(
        refs.map((ref) => [
          ref,
          {
            page: n ? 1 : 2,
            source_sha256: benchmark.documents[key].sha256,
            revision_id: `${key}-rev`,
          },
        ]),
      ),
      structure: {
        source_table_citation: `${key}:table`,
        rows: [
          text.map((v, i) => ({ text: v, evidence_id: refs[i].split(":")[1] })),
        ],
      },
    };
  });
  const answer: Answer = {
    status: "answered",
    index_run_id: "idx",
    answer: "Quản lý giáo dục: chỉ tiêu 2025 là 50; điểm thi THPT 2026 là 15.",
    statements: sources.map((s) => ({
      text: s.text,
      evidence_ids: [s.evidence_id],
    })),
    sources,
    trace: {
      provider_id: "chat",
      retrieval: {
        mode: "hybrid_rerank",
        rerank_provider: { provider_id: "rerank" },
      },
      grounding: {
        cell_proofs: sources.map((s) => ({
          cell_id: `${s.evidence_id}:r1:k1`,
          evidence_ids: [s.evidence_id],
          source_cells: [
            `${s.document_id}:value`,
            `${s.document_id}:subject`,
            `${s.document_id}:header`,
          ],
        })),
      },
    },
  };
  return { state, item, answer };
}

test("restores every field of the original nineteen regression cases", () => {
  for (const gold of original.cases) {
    const current = present(benchmark.cases.find((c) => c.id === gold.id));
    for (const [key, value] of Object.entries(gold))
      expect(current[key as keyof AdmissionCase], `${gold.id}.${key}`).toEqual(
        value,
      );
  }
});

test.each([
  ["300.000 đồng", 300000, "integer", true],
  ["4.681 thí sinh", 4681, "integer", true],
  ["2 974 thí sinh", 2974, "integer", true],
  ["1.65 m", 1.65, "decimal", true],
  ["1,65m", 1.65, "decimal", true],
  ["62,7%", 62.7, "decimal", true],
  ["6.0", 6, "decimal", true],
  ["300.000", 300, "integer", false],
  ["1.65", 165, "integer", false],
  ["2025 50", 50, "integer", true],
  ["2025: 600", 600, "integer", true],
] as const)("numeric parsing %s → %s (%s)", (text, value, kind, result) =>
  expect(hasNumber(text, value, kind)).toBe(result),
);

test("accepts separate proven cells for each document", () => {
  const { state, item, answer } = fixture();
  expect(() =>
    checkAdmissionAnswer(answer, item, state, benchmark.documents),
  ).not.toThrow();
});

test.each([
  "wrong_document",
  "wrong_revision",
  "wrong_version",
  "wrong_decision",
  "wrong_page",
  "wrong_column",
  "missing_proof",
  "wrong_year",
  "unrelated_subject",
])("rejects a plausible numeric answer with %s", (defect) => {
  const { state, item, answer } = fixture();
  const source = answer.sources[0];
  if (defect === "wrong_document") source.document_id = "report2024";
  if (defect === "wrong_revision")
    Object.values(source.citations)[0].revision_id = "stale";
  if (defect === "wrong_version") source.version_id = "stale";
  if (defect === "wrong_decision") source.publication_decision_id = "stale";
  if (defect === "wrong_page")
    for (const c of Object.values(source.citations)) c.page = 8;
  if (defect === "wrong_column")
    present(present(source.structure).rows)[0][1].text = "Mã ngành";
  if (defect === "missing_proof")
    present(answer.trace.grounding).cell_proofs = [];
  if (defect === "wrong_year") answer.statements[0].text += " năm 2026";
  if (defect === "unrelated_subject")
    answer.statements[0].text = "Ngành khác có chỉ tiêu 50";
  expect(() =>
    checkAdmissionAnswer(answer, item, state, benchmark.documents),
  ).toThrow();
});

test("correct numbers from an unrelated report cannot satisfy a cross-document fact", () => {
  const { state, item, answer } = fixture();
  answer.sources = answer.sources.map((s) => ({
    ...s,
    document_id: "report2024",
    version_id: "report2024-ver",
    publication_decision_id: "report2024-pub",
    citations: {
      ref: {
        page: 2,
        source_sha256: benchmark.documents.report2024.sha256,
        revision_id: "report2024-rev",
      },
    },
  }));
  expect(() =>
    checkAdmissionAnswer(answer, item, state, benchmark.documents),
  ).toThrow(/fact/);
});

test("an abstention still rejects leaked evidence from outside its single-document scope", () => {
  const { state, answer } = fixture();
  const item = present(benchmark.cases.find((c) => c.id === "MX-06"));
  answer.status = "insufficient_evidence";
  answer.answer = null;
  answer.statements = [];
  expect(() =>
    checkAdmissionAnswer(answer, item, state, benchmark.documents),
  ).toThrow(/phạm vi/);
});

test("a header on the right page cannot hide a selected value from a different page", () => {
  const { state, item, answer } = fixture();
  answer.sources[0].citations["info2025:value"].page = 8;
  expect(() =>
    checkAdmissionAnswer(answer, item, state, benchmark.documents),
  ).toThrow(/fact/);
});

test("explicit assistant budget fits both input and shared context", () => {
  const p = planAdmissionsBudget({
    model_name: "dynamic",
    capacity_status: "configured",
    token_limits: { context_window_tokens: 131072, max_output_tokens: 16384 },
  });
  expect(p.max_output_tokens).toBe(16384);
  expect(p.context_max_bytes).toBe(98304);
  expect(p.input_tokens_plan + p.max_output_tokens).toBe(131072);
  expect(() =>
    planAdmissionsBudget({
      model_name: "unknown",
      capacity_status: "unknown",
      token_limits: null,
    }),
  ).toThrow(/BLOCKED/);
});

test.each([
  [4096, 131072, 110592],
  [8192, 65536, 40960],
  [32768, 262144, 128000],
])(
  "assistant uses the declared output maximum %i within context %i",
  (output, context, bytes) => {
    const p = planAdmissionsBudget({
      model_name: "dynamic",
      capacity_status: "configured",
      token_limits: {
        context_window_tokens: context,
        max_output_tokens: output,
      },
    });
    expect(p.max_output_tokens).toBe(output);
    expect(p.context_max_bytes).toBe(bytes);
    expect(p.input_tokens_plan + output).toBeLessThanOrEqual(context);
  },
);

test("declared maximum cannot silently consume the evidence reserve", () => {
  expect(() =>
    planAdmissionsBudget({
      model_name: "small-context",
      capacity_status: "configured",
      token_limits: { context_window_tokens: 32768, max_output_tokens: 16384 },
    }),
  ).toThrow(/BLOCKED/);
});

test("quota admission never increases an allowance or clears reservations", async () => {
  const { state } = fixture();
  const api = {
    get: vi.fn().mockResolvedValue({
      configured: true,
      is_blocked: false,
      monthly_token_limit: 100,
      tokens_used: 40,
      tokens_reserved: 40,
    }),
    json: vi.fn(),
  };
  await expect(requireAdmissionsQuota(api, state, 21)).rejects.toThrow(/quota/);
  expect(api.json).not.toHaveBeenCalled();
  await expect(requireAdmissionsQuota(api, state, 20)).resolves.toMatchObject({
    tokens_reserved: 40,
  });
});

test("cohort cannot silently change config or index", () => {
  const { state } = fixture();
  freezeCohort(state, { index: "one", budget: 4000 });
  expect(state.admissions?.cohort?.fingerprint).toBe(
    fingerprint({ index: "one", budget: 4000 }),
  );
  expect(() => freezeCohort(state, { index: "two", budget: 4000 })).toThrow(
    /cohort/,
  );
});

test("index manifest must match all three publication receipts", async () => {
  const { state } = fixture();
  const manifest = {
    run_id: "idx",
    inputs: present(state.admissions).indexInputs,
    config: { chunk_max_bytes: 2048 },
    chunks: [{ id: "chunk" }],
  };
  const api = {
    get: vi.fn(async (url: string) => {
      if (url.endsWith("/manifest")) return manifest;
      if (url.endsWith("/indexing-runs/idx"))
        return { status: "completed", is_active: true, provider_id: "embed" };
      const key = present(url.split("/").at(-2));
      return {
        version: {
          id: `${key}-ver`,
          bundle_sha256: `${key}-bundle`,
          state_version: 3,
        },
        decision: { id: `${key}-pub` },
        content: {},
      };
    }),
  };
  await expect(
    verifyAdmissionsIndex(api as Pick<Api, "get">, state),
  ).resolves.toHaveProperty("published.length", 3);
  manifest.inputs = present(manifest.inputs).slice(0, 2);
  await expect(
    verifyAdmissionsIndex(api as Pick<Api, "get">, state),
  ).rejects.toThrow(/ba tài liệu/);
});

test("single scope missing a publication cannot dispatch", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { state } = fixture();
  const item = { ...benchmark.cases[0], target_doc: "missing" };
  const api = { get: vi.fn(), post: vi.fn(), wait: vi.fn() };
  await expect(askAdmissionQuestion(api, state, item, 1000)).rejects.toThrow(
    /không mở rộng/,
  );
  expect(api.post).not.toHaveBeenCalled();
});

test("replay verifies the server-side conversation scope", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { state } = fixture();
  present(state.admissions).queries = { F01: { conversation: "old" } };
  const api = {
    get: vi
      .fn()
      .mockResolvedValue({ assistant_id: "assistant", document_ids: null }),
    post: vi.fn(),
    wait: vi.fn(),
  };
  await expect(
    askAdmissionQuestion(api, state, benchmark.cases[0], 1000),
  ).rejects.toThrow(/scope/);
  expect(api.post).not.toHaveBeenCalled();
});

test("fresh HTTP failure preserves dispatch; an unknown dispatched request is never sent twice", async () => {
  const { askAdmissionQuestion } = await import(
    "../e2e/stages/admissions-chat"
  );
  const { state } = fixture();
  present(state.admissions).queries = { F01: { conversation: "old" } };
  const api = {
    get: vi.fn(async (url: string) =>
      url.endsWith("/old")
        ? { assistant_id: "assistant", document_ids: ["floor2026"] }
        : [],
    ),
    post: vi.fn().mockRejectedValue(new Error("HTTP 429 code=quota_exceeded")),
    wait: vi.fn(),
  };
  const attempt = {};
  await expect(
    askAdmissionQuestion(
      api as Pick<Api, "get" | "post" | "wait">,
      state,
      benchmark.cases[0],
      1000,
      attempt,
    ),
  ).rejects.toThrow(/429/);
  expect(attempt).toMatchObject({
    origin: "fresh",
    dispatched: true,
    conversation: "old",
  });
  await expect(
    askAdmissionQuestion(
      api as Pick<Api, "get" | "post" | "wait">,
      state,
      benchmark.cases[0],
      1000,
    ),
  ).rejects.toThrow(/không gửi lại/);
  expect(api.post).toHaveBeenCalledTimes(1);
});

test("content failures continue; infrastructure and quota failures halt", async () => {
  const { stopsAdmissionsCohort } = await import(
    "../e2e/stages/admissions-chat"
  );
  expect(stopsAdmissionsCohort("Model từ chối câu có căn cứ.")).toBe(false);
  expect(stopsAdmissionsCohort("Không chứng minh được fact")).toBe(false);
  expect(stopsAdmissionsCohort("HTTP 429 code=quota_exceeded")).toBe(true);
  expect(stopsAdmissionsCohort("chat_provider_uncertain")).toBe(true);
});
