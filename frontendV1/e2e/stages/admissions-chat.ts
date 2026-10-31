import { writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  type AdmissionCase,
  benchmark,
  modelTimeout,
} from "./admissions-context";
import {
  type Api,
  type Checkpoint,
  type Run,
  ensureSessionQuota,
  save,
  workspace,
} from "./session";

interface Answer {
  status: "answered" | "insufficient_evidence";
  reason?: string;
  answer: string | null;
  index_run_id: string;
  statements: { text: string; evidence_ids: string[] }[];
  sources: {
    evidence_id: string;
    version_id: string;
    citations: Record<
      string,
      { page: number; source_sha256: string; revision_id: string }
    >;
  }[];
  trace: {
    provider_id?: string;
    retrieval: { mode?: string; rerank_provider?: { provider_id: string } };
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
  };
}
type Turn = Run & { result: Answer };

async function ask(
  api: Api,
  state: Checkpoint,
  item: AdmissionCase,
  timeout: number,
): Promise<{ answer: Answer; elapsedMs: number }> {
  const scenario = state.admissions;
  if (!scenario?.assistant)
    throw new Error("BLOCKED: chưa có trợ lý điểm sàn.");
  scenario.queries ||= {};
  let query: { conversation: string; turn?: string } | undefined =
    scenario.queries[item.id];
  const idempotencyKey = `${state.runId}-floor-${benchmark.version}-${item.id}`;

  if (!query) {
    const conversation = await api.post<{ id: string }>(
      `${workspace(state)}/conversations`,
      {
        assistant_id: scenario.assistant,
        document_ids: [scenario.publication?.document],
      },
    );
    query = { conversation: conversation.id };
    scenario.queries[item.id] = query;
    save(state);
  }

  const base = `${workspace(state)}/conversations/${query.conversation}/turns`;
  let turn: Turn;
  const startedAt = Date.now();

  if (query.turn) {
    // Trường hợp mất kết nối hoặc khôi phục: kiểm tra lượt cũ trước khi gửi mới
    const existing = await api
      .get<Turn>(`${base}/${query.turn}`)
      .catch(() => null);
    if (existing && existing.status === "completed") {
      turn = existing;
    } else if (
      existing &&
      (existing.status === "running" || existing.status === "pending")
    ) {
      turn = await api.wait<Turn>(`${base}/${query.turn}`, timeout);
    } else {
      turn = await api.post<Turn>(
        base,
        { question: item.question, expected_turn_no: 0 },
        idempotencyKey,
        timeout,
      );
      query.turn = turn.id;
      save(state);
      if (turn.status !== "completed") {
        turn = await api.wait<Turn>(`${base}/${turn.id}`, timeout);
      }
    }
  } else {
    turn = await api.post<Turn>(
      base,
      { question: item.question, expected_turn_no: 0 },
      idempotencyKey,
      timeout,
    );
    query.turn = turn.id;
    save(state);
    if (turn.status !== "completed") {
      turn = await api.wait<Turn>(`${base}/${turn.id}`, timeout);
    }
  }

  const elapsedMs = Date.now() - startedAt;
  return { answer: turn.result, elapsedMs };
}

function checkAnswer(answer: Answer, item: AdmissionCase, state: Checkpoint) {
  const scenario = state.admissions;
  expect(answer.index_run_id).toBe(scenario?.publication?.index);
  if (item.kind === "unanswerable") {
    expect(answer.status, "Không được đoán dữ kiện ngoài PDF đã chốt.").toBe(
      "insufficient_evidence",
    );
    expect(answer.statements).toHaveLength(0);
    return;
  }
  expect(answer.status).toBe("answered");
  expect(answer.trace.provider_id).toBe(state.runtimeDefaults?.chat);
  expect(answer.trace.retrieval.mode).toBe("hybrid_rerank");
  expect(answer.trace.retrieval.rerank_provider?.provider_id).toBe(
    state.runtimeDefaults?.rerank,
  );
  expect(answer.statements.length).toBeGreaterThan(0);
  expect(answer.sources.length).toBeGreaterThan(0);
  const numbers = [
    ...(answer.answer || "").matchAll(
      /(?<![\p{L}\d])\d+(?:[.,]\d+)?(?![\p{L}\d])/gu,
    ),
  ].map((match) => Number(match[0].replace(",", ".")));
  for (const value of item.expected_numbers) expect(numbers).toContain(value);
  const text = (answer.answer || "").replace(/\s+/g, " ");
  for (const pattern of item.expected_patterns)
    expect(text).toMatch(new RegExp(pattern, "iu"));
  const refs = answer.sources.flatMap((source) => {
    expect(source.version_id).toBe(scenario?.publication?.version);
    expect(Object.keys(source.citations).length).toBeGreaterThan(0);
    return Object.entries(source.citations);
  });
  for (const [ref, citation] of refs) {
    expect(ref.startsWith(`${scenario?.source?.run}:`)).toBe(true);
    expect(citation.source_sha256).toBe(benchmark.source.sha256);
    expect(citation.revision_id).toBe(scenario?.source?.revision);
  }
  expect(refs.some(([, citation]) => item.pages.includes(citation.page))).toBe(
    true,
  );
  const evidence = new Set(answer.sources.map((source) => source.evidence_id));
  for (const statement of answer.statements)
    expect(
      statement.evidence_ids.length > 0 &&
        statement.evidence_ids.every((id) => evidence.has(id)),
    ).toBe(true);
}

async function ensureAssistant(api: Api, state: Checkpoint) {
  if (!state.admissions) throw new Error("BLOCKED: chưa tạo kho điểm sàn.");
  if (state.admissions.assistant) {
    const existing = await api
      .get<{
        revision: number;
        name: string;
        description: string;
        persona: string;
        collection_id: string;
        chat_provider_id: string | null;
        top_k: number;
        history_turns: number;
        max_output_tokens: number;
        is_active: boolean;
        rag_policy: {
          retrieval_mode: string;
          candidate_k: number;
          rrf_k: number;
          rerank_provider_id: string | null;
          [k: string]: unknown;
        };
      }>(`${workspace(state)}/assistants/${state.admissions.assistant}`)
      .catch(() => null);

    if (
      existing &&
      (existing.top_k !== 20 || existing.rag_policy?.candidate_k !== 50)
    ) {
      await api
        .json(
          "PUT",
          `${workspace(state)}/assistants/${state.admissions.assistant}`,
          {
            name: existing.name,
            description: existing.description,
            persona: existing.persona,
            collection_id: existing.collection_id,
            chat_provider_id: existing.chat_provider_id,
            top_k: 20,
            history_turns: existing.history_turns,
            max_output_tokens: existing.max_output_tokens,
            is_active: existing.is_active,
            rag_policy: {
              ...existing.rag_policy,
              candidate_k: 50,
            },
            expected_revision: existing.revision,
          },
        )
        .catch(() => null);
    }
    return;
  }
  const assistant = await api.post<{ id: string }>(
    `${workspace(state)}/assistants`,
    {
      name: `Điểm sàn QNU 2026 — ${state.runId}`,
      collection_id: state.admissions.collection,
      chat_provider_id: state.runtimeDefaults?.chat,
      top_k: 20,
      rag_policy: {
        retrieval_mode: "hybrid_rerank",
        candidate_k: 50,
        rerank_provider_id: state.runtimeDefaults?.rerank,
      },
    },
  );
  state.admissions.assistant = assistant.id;
  save(state);
}

export async function questionAdmissionDraft(api: Api, state: Checkpoint) {
  if (!state.admissions?.publication?.index)
    throw new Error("BLOCKED: chưa xuất bản/lập chỉ mục.");
  await ensureSessionQuota(api, state, 5_000_000);
  await ensureAssistant(api, state);
  const timeout = await modelTimeout(api, state);
  const records: {
    id: string;
    status: string;
    first_attempt_pass: boolean;
    elapsed_ms?: number;
    tokens?: {
      prompt_tokens?: number | null;
      completion_tokens?: number | null;
      total_tokens?: number | null;
    };
    response?: Answer;
    error?: string;
  }[] = benchmark.cases.map((item) => ({
    id: item.id,
    status: "NOT_RUN",
    first_attempt_pass: false,
  }));
  const report = () =>
    writeFileSync(
      path.join(
        process.env.E2E_OUTPUT || "test-results",
        "admissions-answers.json",
      ),
      `${JSON.stringify(
        {
          benchmark: benchmark.version,
          source_sha256: benchmark.source.sha256,
          publication: state.admissions?.publication,
          label_status: benchmark.label_status,
          semantic_review: "NOT_RUN",
          expected: records.length,
          passed: records.filter((r) => r.status === "PASS").length,
          failed: records.filter((r) => r.status === "FAIL").length,
          not_run: records.filter((r) => r.status === "NOT_RUN").length,
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
  for (const [index, item] of benchmark.cases.entries()) {
    await test.step(`${item.id}: ${item.question}`, async () => {
      const stepStart = Date.now();
      try {
        const { answer, elapsedMs } = await ask(api, state, item, timeout);
        records[index].response = answer;
        records[index].elapsed_ms = elapsedMs;
        records[index].tokens = {
          prompt_tokens: answer?.trace?.prompt_tokens,
          completion_tokens: answer?.trace?.completion_tokens,
          total_tokens: answer?.trace?.total_tokens,
        };
        checkAnswer(answer, item, state);
        records[index].status = "PASS";
        records[index].first_attempt_pass = true;
      } catch (error) {
        records[index].status = "FAIL";
        records[index].first_attempt_pass = false;
        records[index].elapsed_ms ||= Date.now() - stepStart;
        records[index].error =
          error instanceof Error ? error.message : String(error);
        throw error;
      } finally {
        report();
      }
    });
  }
}
