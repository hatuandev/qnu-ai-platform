import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  type AdmissionCase,
  benchmark,
  modelTimeout,
} from "./admissions-context";
import { type Answer, checkAdmissionAnswer } from "./admissions-evaluation";
import {
  fingerprint,
  freezeCohort,
  planAdmissionsBudget,
  planAdmissionsRerankPair,
  requireAdmissionsQuota,
  verifyAdmissionsIndex,
} from "./admissions-policy";
import {
  type Api,
  type Checkpoint,
  type Run,
  save,
  workspace,
} from "./session";

export type Attempt = {
  origin?: "fresh" | "replayed" | "resumed";
  dispatched?: boolean;
  conversation?: string;
  turn?: string;
};
type Turn = Run & { result: Answer; question?: string };

export async function askAdmissionQuestion(
  api: Pick<Api, "get" | "post" | "wait">,
  state: Checkpoint,
  item: AdmissionCase,
  timeout: number,
  attempt: Attempt = {},
): Promise<{
  answer: Answer;
  elapsedMs: number;
  inferenceMs: number | null;
  origin: "fresh" | "replayed" | "resumed";
  firstAttempt: boolean;
}> {
  const scenario = state.admissions;
  if (!scenario?.assistant)
    throw new Error("BLOCKED: chưa có trợ lý tuyển sinh.");
  let documentIds: string[] | undefined;
  if (item.scope === "single") {
    const docId = scenario.documents?.[item.target_doc]?.publication?.document;
    if (!docId)
      throw new Error(
        "BLOCKED: thiếu tài liệu scope single; không mở rộng sang cả kho.",
      );
    documentIds = [docId];
  } else if (item.scope !== "all")
    throw new Error("BLOCKED: scope không hợp lệ.");
  const requestHash = fingerprint({
    question: item.question,
    assistant: scenario.assistant,
    documentIds: documentIds || null,
    benchmark: benchmark.version,
  });
  scenario.queries ||= {};
  let query = scenario.queries[item.id];
  if (!query) {
    const conversation = await api.post<{ id: string }>(
      `${workspace(state)}/conversations`,
      { assistant_id: scenario.assistant, document_ids: documentIds },
      `${state.runId}-adm-${benchmark.version}-${item.id}-conversation`,
    );
    query = { conversation: conversation.id, request_sha256: requestHash };
    scenario.queries[item.id] = query;
    save(state);
  }
  attempt.conversation = query.conversation;
  if (query.request_sha256 && query.request_sha256 !== requestHash)
    throw new Error("BLOCKED: câu hỏi/scope checkpoint đã đổi.");
  const conversation = await api.get<{
    assistant_id: string;
    document_ids: string[] | null;
  }>(`${workspace(state)}/conversations/${query.conversation}`);
  if (
    conversation.assistant_id !== scenario.assistant ||
    JSON.stringify(conversation.document_ids || null) !==
      JSON.stringify(documentIds || null)
  )
    throw new Error("BLOCKED: hội thoại cũ sai assistant/scope.");
  const base = `${workspace(state)}/conversations/${query.conversation}/turns`;
  const startedAt = Date.now();
  // Khôi phục reservation của server trước khi quyết định turn mới
  const existing = query.turn
    ? await api.get<Turn>(`${base}/${query.turn}`)
    : (await api.get<Turn[]>(base))[0];
  if (
    existing &&
    existing.question !== undefined &&
    existing.question !== item.question
  )
    throw new Error("BLOCKED: lượt hỏi cũ khác câu đang kiểm tra.");
  const origin = !existing
    ? "fresh"
    : existing.status === "completed"
      ? "replayed"
      : "resumed";
  attempt.origin = origin;
  if (!existing && query.dispatched)
    throw new Error(
      "BLOCKED: lượt đã dispatch nhưng chưa đối soát được; không gửi lại.",
    );
  let turn = existing;
  if (!turn) {
    query.dispatched = true;
    query.request_sha256 = requestHash;
    attempt.dispatched = true;
    save(state); // durable before network dispatch, including timeout/HTTP failures
    turn = await api.post<Turn>(
      base,
      { question: item.question, expected_turn_no: 0 },
      `${state.runId}-adm-${benchmark.version}-${item.id}`,
      timeout,
    );
  }
  attempt.turn = turn.id;
  query.turn = turn.id;
  save(state);
  if (["failed", "uncertain", "cancelled"].includes(turn.status))
    throw new Error(
      `Lượt hỏi ${turn.status}: ${turn.error_code || "unknown"}; giữ lịch sử, không gửi lại.`,
    );
  if (turn.status !== "completed")
    turn = await api.wait<Turn>(`${base}/${turn.id}`, timeout);
  const elapsedMs = Date.now() - startedAt;
  return {
    answer: turn.result,
    elapsedMs,
    origin,
    inferenceMs:
      origin === "fresh"
        ? (turn.result.trace?.stage_ms?.generation ?? null)
        : null,
    firstAttempt:
      origin === "fresh" &&
      !scenario.queryHistory?.some((h) => h.case_id === item.id),
  };
}

interface AssistantConfig {
  id: string;
  revision: number;
  name: string;
  description: string;
  persona: string;
  collection_id: string;
  chat_provider_id: string;
  top_k: number;
  history_turns: number;
  max_output_tokens: number;
  is_active: boolean;
  rag_policy: {
    candidate_k: number;
    context_max_bytes: number;
    [k: string]: unknown;
  };
}

export async function ensureAdmissionsAssistant(
  api: Api,
  state: Checkpoint,
  budget: ReturnType<typeof planAdmissionsBudget>,
) {
  const scenario = state.admissions;
  if (!scenario?.collection)
    throw new Error("BLOCKED: chưa tạo kho tuyển sinh.");
  const desired = {
    collection_id: scenario.collection,
    chat_provider_id: state.runtimeDefaults?.chat,
    top_k: 20,
    history_turns: 0,
    max_output_tokens: budget.max_output_tokens,
    rag_policy: {
      retrieval_mode: "hybrid_rerank",
      candidate_k: 50,
      context_window: 0,
      context_max_bytes: budget.context_max_bytes,
      rerank_provider_id: state.runtimeDefaults?.rerank,
    },
  };
  if (!scenario.assistant) {
    const created = await api.post<{ id: string }>(
      `${workspace(state)}/assistants`,
      { name: `Tuyển sinh QNU (Đa tài liệu) — ${state.runId}`, ...desired },
    );
    scenario.assistant = created.id;
    save(state);
  }
  const existing = await api.get<AssistantConfig>(
    `${workspace(state)}/assistants/${scenario.assistant}`,
  );
  const same =
    existing.collection_id === desired.collection_id &&
    existing.chat_provider_id === desired.chat_provider_id &&
    existing.top_k === desired.top_k &&
    existing.history_turns === 0 &&
    existing.max_output_tokens === desired.max_output_tokens &&
    Object.entries(desired.rag_policy).every(
      ([k, v]) => existing.rag_policy[k] === v,
    );
  if (!same) {
    if (scenario.cohort || Object.keys(scenario.queries || {}).length)
      throw new Error(
        "BLOCKED: assistant khác cấu hình cohort; không tự đổi khi đã có lượt hỏi.",
      );
    await api.json(
      "PUT",
      `${workspace(state)}/assistants/${scenario.assistant}`,
      {
        name: existing.name,
        description: existing.description,
        persona: existing.persona,
        is_active: existing.is_active,
        ...desired,
        expected_revision: existing.revision,
      },
    );
    return api.get<AssistantConfig>(
      `${workspace(state)}/assistants/${scenario.assistant}`,
    );
  }
  return existing;
}

export function stopsAdmissionsCohort(message: string) {
  return /BLOCKED:|quota_|provider_|timeout|ECONN|HTTP (401|403|429|5\d\d)|capacity_|input_limit|context_budget|uncertain/i.test(
    message,
  );
}

interface SemanticReviewRow {
  case_id?: string;
  verdict?: string;
  benchmark?: string;
  cohort_fingerprint?: string;
}

export function semanticReviewStatus(
  cohort: { fingerprint: string } | undefined,
) {
  const file = path.join(
    process.env.E2E_OUTPUT || "test-results",
    "semantic-review.jsonl",
  );
  if (!existsSync(file))
    return { status: "NOT_RUN", reason: "chưa có semantic-review.jsonl" };
  const rows: SemanticReviewRow[] = readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as SemanticReviewRow);
  if (!cohort?.fingerprint || !rows.length)
    return { status: "NOT_RUN", reason: "chưa chốt cohort hoặc review rỗng" };
  if (
    rows.some(
      (row) =>
        row.cohort_fingerprint !== cohort.fingerprint ||
        row.benchmark !== benchmark.version,
    )
  )
    return {
      status: "NOT_RUN",
      reason: "semantic review khác cohort/benchmark",
    };
  if (
    rows.some(
      (row) =>
        !row.case_id || (row.verdict !== "PASS" && row.verdict !== "FAIL"),
    )
  )
    return {
      status: "NOT_RUN",
      reason: "semantic review có dòng không hợp lệ",
    };
  const failed = rows.filter((row) => row.verdict === "FAIL").length;
  return {
    status: failed ? "FAIL" : "PASS",
    reviewed: rows.length,
    failed,
  };
}

export async function questionAdmissionDraft(api: Api, state: Checkpoint) {
  if (!state.admissions?.combinedIndex && !state.admissions?.publication?.index)
    throw new Error("BLOCKED: chưa xuất bản/lập chỉ mục.");
  const timeout = await modelTimeout(api, state);
  const records: {
    id: string;
    group: string;
    scope: string;
    target_doc: string;
    status: string;
    first_attempt_pass: boolean;
    dispatched?: boolean;
    conversation?: string;
    turn?: string;
    error_code?: string;
    client_elapsed_ms?: number;
    inference_ms?: number | null;
    origin?: "fresh" | "replayed" | "resumed";
    tokens?: {
      prompt_tokens?: number | null;
      completion_tokens?: number | null;
      total_tokens?: number | null;
      rerank_tokens?: number | null;
    };
    response?: Answer;
    error?: string;
  }[] = benchmark.cases.map((item) => ({
    id: item.id,
    group: item.group,
    scope: item.scope,
    target_doc: item.target_doc,
    status: "NOT_RUN",
    first_attempt_pass: false,
  }));

  let preflight: unknown;
  const report = () =>
    writeFileSync(
      path.join(
        process.env.E2E_OUTPUT || "test-results",
        "admissions-answers.json",
      ),
      `${JSON.stringify(
        {
          benchmark: benchmark.version,
          preflight,
          cohort: state.admissions?.cohort,
          documents: benchmark.documents,
          combined_index: state.admissions?.combinedIndex,
          label_status: benchmark.label_status,
          semantic_review: semanticReviewStatus(state.admissions?.cohort),
          compilation_review:
            state.results["admissions-publication"]?.review_mode === "skipped"
              ? "SKIPPED_BY_USER"
              : "reviewed",
          prompt_versions: [
            ...new Set(
              records
                .map((r) => r.response?.trace.prompt_version)
                .filter(Boolean),
            ),
          ],
          configuration_hashes: [
            ...new Set(
              records
                .map((r) => r.response?.trace.configuration_hash)
                .filter(Boolean),
            ),
          ],
          expected: records.length,
          passed: records.filter((r) => r.status === "PASS").length,
          failed: records.filter((r) => r.status === "FAIL").length,
          not_run: records.filter((r) => r.status === "NOT_RUN").length,
          replayed: records.filter((r) => r.origin === "replayed").length,
          resumed: records.filter((r) => r.origin === "resumed").length,
          fresh_results: records.filter((r) => r.origin === "fresh").length,
          first_attempt_passed: records.filter((r) => r.first_attempt_pass)
            .length,
          records,
        },
        null,
        2,
      )}\n`,
      "utf8",
    );
  report();

  try {
    const index = await verifyAdmissionsIndex(api, state);
    const provider = await api.get<Parameters<typeof planAdmissionsBudget>[0]>(
      `/modelops/providers/${state.runtimeDefaults?.chat}`,
    );
    const budget = planAdmissionsBudget(provider);
    const assistant = await ensureAdmissionsAssistant(api, state, budget);
    const rerank = await api.get<Parameters<typeof planAdmissionsBudget>[0]>(
      `/modelops/providers/${state.runtimeDefaults?.rerank}`,
    );
    const maxQuestion = Math.max(
      ...benchmark.cases.map((c) => Buffer.byteLength(c.question)),
    );
    const rerankPlan = planAdmissionsRerankPair(
      rerank,
      index.manifest.config.chunk_max_bytes,
      maxQuestion,
    );
    const fresh = benchmark.cases.filter(
      (c) => !state.admissions?.queries?.[c.id]?.turn,
    ).length;
    const quotaEstimate =
      fresh *
      (budget.input_tokens_plan +
        budget.max_output_tokens +
        50 * rerankPlan.token_estimate +
        maxQuestion +
        256);
    preflight = {
      budget,
      published: index.published,
      rerank_pair: rerankPlan,
      fresh_cases: fresh,
      quota_tokens_plan: quotaEstimate,
      budget_basis:
        "UTF8-byte conservative planning; rerank bytes convert to a documented token estimate; per-pair bytes and final prompt/schema/catalog still guarded by ModelOps",
    };
    freezeCohort(state, {
      benchmark: fingerprint(benchmark),
      manifest: fingerprint(index.manifest),
      assistant,
      provider,
      rerank,
    });
    await requireAdmissionsQuota(api, state, quotaEstimate);
    report();
  } catch (error) {
    preflight = {
      error: error instanceof Error ? error.message : String(error),
      details: preflight,
    };
    report();
    throw error;
  }
  let halt = false;
  for (const [index, item] of benchmark.cases.entries()) {
    if (halt) break;
    await test.step(`[${item.id}] [${item.group}] ${item.question}`, async () => {
      const stepStart = Date.now();
      const attempt: Attempt = {};
      try {
        const { answer, elapsedMs, inferenceMs, origin, firstAttempt } =
          await askAdmissionQuestion(api, state, item, timeout, attempt);
        records[index].response = answer;
        records[index].client_elapsed_ms = elapsedMs;
        records[index].inference_ms = inferenceMs;
        records[index].origin = origin;
        records[index].tokens = {
          prompt_tokens: answer.trace.prompt_tokens,
          completion_tokens: answer.trace.completion_tokens,
          total_tokens: answer.trace.total_tokens,
          rerank_tokens: answer.trace.rerank_tokens ?? null,
        };
        const cohort = state.admissions?.cohort;
        if (!answer.trace.prompt_version || !answer.trace.configuration_hash)
          throw new Error("BLOCKED: thiếu prompt/config trace.");
        if (cohort) {
          if (
            (cohort.prompt_version &&
              cohort.prompt_version !== answer.trace.prompt_version) ||
            (cohort.configuration_hash &&
              cohort.configuration_hash !== answer.trace.configuration_hash)
          )
            throw new Error("BLOCKED: prompt/config đã đổi giữa cohort.");
          cohort.prompt_version ||= answer.trace.prompt_version;
          cohort.configuration_hash ||= answer.trace.configuration_hash;
          save(state);
        }
        checkAdmissionAnswer(answer, item, state, benchmark.documents);
        records[index].status = "PASS";
        records[index].first_attempt_pass = firstAttempt;
      } catch (error) {
        records[index].status = "FAIL";
        records[index].first_attempt_pass = false;
        records[index].client_elapsed_ms ||= Date.now() - stepStart;
        records[index].error =
          error instanceof Error ? error.message : String(error);
        records[index].error_code = records[index].error.match(
          /(?:code=|: )([a-z]+_[a-z_]+)/,
        )?.[1];
        halt = stopsAdmissionsCohort(records[index].error);
      } finally {
        Object.assign(records[index], attempt);
        report();
      }
    });
  }
  expect(
    records
      .filter((r) => r.status !== "PASS")
      .map((r) => `${r.id}:${r.status}`),
    "Một lượt/câu; không retry. Các lỗi độc lập được chấm hết, hạ tầng dừng và để NOT_RUN.",
  ).toEqual([]);
}
