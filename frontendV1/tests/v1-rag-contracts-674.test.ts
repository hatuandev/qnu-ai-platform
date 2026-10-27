// @vitest-environment node
/**
 * Contract regressions for the Context674 hand-off (F3 + RAG G1/G2).
 *
 * These assert the *request bodies* the backend will receive, not the rendering:
 * the Context673 backend rejects unknown fields (`extra="forbid"`) and treats a
 * missing `metadata_filter` differently from an empty one, so the transport has
 * to be exact.
 */

import { expect, test } from "vitest";
import { ApiProblemError, createV1Client } from "../src/app/api/v1/client.ts";
import { sendTurn } from "../src/features/conversations/requests.ts";
import type { TurnRequestInput } from "../src/features/conversations/types.ts";
import {
  requestIndex,
  searchCollection,
} from "../src/features/knowledge/index-requests.ts";
import {
  createCompiledDocument,
  createCompiledVersion,
  createDecisionPreview,
  getPublishedCompiledDocument,
} from "../src/features/knowledge/publication-requests.ts";
import {
  DEFAULT_RAG_POLICY_FORM,
  ragPolicyFormSchema,
  toRagPolicy,
  toRagPolicyForm,
} from "../src/features/rag/schemas.ts";
import type { RetrievalAnnotation } from "../src/features/rag/types.ts";
import {
  DEFAULT_RAG_POLICY,
  validateRagPolicy,
} from "../src/features/rag/types.ts";

type RecordedCall = {
  url: string;
  method: string;
  headers: Headers;
  body: Record<string, unknown>;
};

function recordingClient(respond: (call: RecordedCall) => unknown) {
  const calls: RecordedCall[] = [];
  const client = createV1Client({
    fetchImpl: async (input: string, init?: RequestInit) => {
      const body =
        typeof init?.body === "string" ? JSON.parse(init.body) : init?.body;
      const call: RecordedCall = {
        url: input,
        method: init?.method ?? "GET",
        headers: new Headers(init?.headers),
        body,
      };
      calls.push(call);
      return new Response(JSON.stringify(respond(call) ?? {}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    },
  });
  return { calls, client };
}

const turnResponse = {
  id: "turn_1",
  conversation_id: "cnv_1",
  turn_no: 1,
  question: "Học phí ngành CNTT?",
  status: "completed",
  created_at: "2026-10-27T00:00:00Z",
  result: null,
};

const annotation: RetrievalAnnotation = {
  target: "paragraph:0:1",
  values: { data_year: 2026, program: "Kỹ thuật phần mềm", intake: "Đợt 1" },
  evidence: [
    {
      citation: "run_1:ev_9",
      quote: "Năm 2026, ngành Kỹ thuật phần mềm, Đợt 1",
    },
  ],
};

test("a turn without an explicit scope omits metadata_filter so the backend can inherit", async () => {
  const { calls, client } = recordingClient(() => turnResponse);
  await sendTurn(
    client,
    "ws",
    "cnv_1",
    {
      question: "  Học phí?  ",
      expected_turn_no: 1,
    } satisfies TurnRequestInput,
    "turn_key_1",
  );

  expect(calls).toHaveLength(1);
  expect(calls[0].body).toEqual({
    question: "Học phí?",
    expected_turn_no: 1,
  });
  expect("metadata_filter" in calls[0].body).toBe(false);
});

test("an explicit scope is sent verbatim, never merged with an earlier answer", async () => {
  const { calls, client } = recordingClient(() => turnResponse);
  const scope = { data_year: 2026, program: "Kỹ thuật phần mềm" };
  await sendTurn(
    client,
    "ws",
    "cnv_1",
    { question: "Học phí?", expected_turn_no: 2, metadata_filter: scope },
    "turn_key_2",
  );

  expect(calls[0].body).toMatchObject({ metadata_filter: scope });
});

test("an empty scope object is still omitted, so it cannot narrow the search to nothing", async () => {
  const { calls, client } = recordingClient(() => turnResponse);
  await sendTurn(
    client,
    "ws",
    "cnv_1",
    { question: "Học phí?", expected_turn_no: 3, metadata_filter: {} },
    "turn_key_3",
  );

  expect("metadata_filter" in calls[0].body).toBe(false);
});

test("registering a document sends the declared annotations on the request body", async () => {
  const { calls, client } = recordingClient(() => ({
    document: { id: "doc" },
    version: { id: "ver" },
    created: true,
  }));
  await createCompiledDocument(
    client,
    "ws",
    "col",
    {
      document_key: "chi-tieu-2026",
      title: "Chỉ tiêu 2026",
      compilation_run_id: "run_1",
      retrieval_metadata: [annotation],
    },
    "pub_key_1",
  );

  expect(calls[0].body).toMatchObject({ retrieval_metadata: [annotation] });
  expect(calls[0].headers.get("Idempotency-Key")).toBe("pub_key_1");
});

test("registering a version without metadata sends an empty list, not a missing field", async () => {
  const { calls, client } = recordingClient(() => ({
    document: { id: "doc" },
    version: { id: "ver" },
    created: true,
  }));
  await createCompiledVersion(
    client,
    "ws",
    "col",
    "doc",
    { compilation_run_id: "run_1", retrieval_metadata: [] },
    "pub_key_2",
  );

  expect(calls[0].body).toEqual({
    compilation_run_id: "run_1",
    retrieval_metadata: [],
  });
});

test("the approval preview echoes the backend metadata digest exactly", async () => {
  const sha = "a".repeat(64);
  const { calls, client } = recordingClient(() => ({ id: "preview_1" }));
  await createDecisionPreview(client, "ws", "col", "doc", "ver", {
    action: "approve",
    reason: "Đã đối chiếu báo cáo và metadata.",
    review_ack: {
      review_id: "review_1",
      report_sha256: "b".repeat(64),
      confirmed_reviewed: true,
      resolutions: [],
      retrieval_metadata_sha256: sha,
    },
  });

  expect(calls[0].body).toMatchObject({
    review_ack: { retrieval_metadata_sha256: sha, confirmed_reviewed: true },
  });
});

test("a version without metadata never sends a fabricated digest", async () => {
  const { calls, client } = recordingClient(() => ({ id: "preview_2" }));
  await createDecisionPreview(client, "ws", "col", "doc", "ver", {
    action: "approve",
    reason: "Đã đối chiếu báo cáo.",
    review_ack: {
      review_id: "review_1",
      report_sha256: "b".repeat(64),
      confirmed_reviewed: true,
      resolutions: [],
    },
  });

  const ack = calls[0].body.review_ack as Record<string, unknown>;
  expect("retrieval_metadata_sha256" in ack).toBe(false);
});

test("search keeps its explicit scope and drops unset optional fields", async () => {
  const { calls, client } = recordingClient(() => ({ hits: [] }));
  await searchCollection(client, "ws", "col", {
    query: "  học phí  ",
    top_k: 5,
    mode: "hybrid",
    candidate_k: 30,
    rrf_k: 60,
    rerank_provider_id: null,
    metadata_filter: { issued_year: 2025 },
  });

  expect(calls[0].body).toEqual({
    query: "học phí",
    top_k: 5,
    mode: "hybrid",
    candidate_k: 30,
    rrf_k: 60,
    metadata_filter: { issued_year: 2025 },
  });
});

test("requesting an index generation carries a real idempotency key", async () => {
  const { calls, client } = recordingClient(() => ({
    run: { id: "run_1" },
    created: false,
    dispatched: true,
  }));
  const result = await requestIndex(client, "ws", "col", "prov_1", "idx_key_1");

  expect(calls[0].headers.get("Idempotency-Key")).toBe("idx_key_1");
  expect(calls[0].body).toEqual({ provider_id: "prov_1" });
  // `created: false` is an idempotent replay, not a new generation.
  expect(result.created).toBe(false);
});

test("the default RAG form round-trips to the backend-compatible default policy", () => {
  const parsed = ragPolicyFormSchema.safeParse(DEFAULT_RAG_POLICY_FORM);
  expect(parsed.success).toBe(true);
  if (!parsed.success) return;

  expect(toRagPolicy(parsed.data)).toEqual(DEFAULT_RAG_POLICY);
});

test("a stored policy is never silently upgraded to hybrid or to the judge", () => {
  const form = toRagPolicyForm({ ...DEFAULT_RAG_POLICY });
  expect(form.retrieval_mode).toBe("dense");
  expect(form.verification_mode).toBe("off");
  expect(form.context_window).toBe(0);

  const policy = toRagPolicy(form);
  expect(policy.retrieval_mode).toBe("dense");
  expect(policy.verification_mode).toBe("off");
});

test("a rerank provider id is dropped outside hybrid_rerank instead of failing the save", () => {
  const policy = toRagPolicy({
    ...DEFAULT_RAG_POLICY_FORM,
    retrieval_mode: "dense",
    rerank_provider_id: "prov_rerank",
  });
  expect(policy.rerank_provider_id).toBeNull();
});

test("turning verification off drops its provider instead of leaving an unusable id", () => {
  const policy = toRagPolicy({
    ...DEFAULT_RAG_POLICY_FORM,
    verification_mode: "off",
    verification_provider_id: "prov_judge",
  });
  expect(policy.verification_provider_id).toBeNull();
});

test("the candidate budget must cover Top K once retrieval stops being dense", () => {
  expect(
    validateRagPolicy(
      { ...DEFAULT_RAG_POLICY, retrieval_mode: "hybrid", candidate_k: 3 },
      5,
    ),
  ).not.toBeNull();
  expect(
    validateRagPolicy(
      { ...DEFAULT_RAG_POLICY, retrieval_mode: "hybrid", candidate_k: 30 },
      5,
    ),
  ).toBeNull();
});

test.each([
  [404, "compiled_document_not_found"],
  [404, "resource_unavailable"],
  [404, "publication_metadata_review_required"],
  [503, "published_compilation_not_found"],
])(
  "a published read must keep HTTP %s / %s as an error",
  async (status, code) => {
    const client = createV1Client({
      fetchImpl: async () =>
        new Response(JSON.stringify({ status, code, detail: "Synthetic" }), {
          status,
          headers: { "Content-Type": "application/problem+json" },
        }),
    });
    await expect(
      getPublishedCompiledDocument(client, "ws", "col", "doc"),
    ).rejects.toBeInstanceOf(ApiProblemError);
  },
);

test("only the exact no-publication 404 becomes an empty publication state", async () => {
  const client = createV1Client({
    fetchImpl: async () =>
      new Response(
        JSON.stringify({
          status: 404,
          code: "published_compilation_not_found",
        }),
        {
          status: 404,
          headers: { "Content-Type": "application/problem+json" },
        },
      ),
  });
  expect(
    await getPublishedCompiledDocument(client, "ws", "col", "doc"),
  ).toBeNull();
});
