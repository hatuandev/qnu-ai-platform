import { readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";
import { benchmark, checkAllSources, modelTimeout } from "./admissions-context";
import { type Answer, checkAdmissionAnswer } from "./admissions-evaluation";
import {
  fingerprint,
  requireAdmissionsQuota,
  verifyAdmissionsIndex,
} from "./admissions-policy";
import {
  assertRunnerCompletion,
  checkConfigDrift,
  dispatchRetestOnce,
  mustHaltRetest,
  type Retest9Record,
  type Retest9Report,
  resolveDocumentBinding,
  TARGET_RETEST9_IDS,
} from "./retest9-core";
import { authenticate, checkpoint } from "./session";

interface Turn {
  id: string;
  question: string;
  turn_no: number;
  conversation_id: string;
  status: string;
  error_code: string | null;
  result: Answer | null;
}
type Json = Record<string, unknown>;

export async function runRetest9(page: Page, setTimeout: (ms: number) => void) {
  const state = checkpoint();
  const scenario = state.admissions;
  if (!scenario?.assistant)
    throw new Error("BLOCKED: thiếu assistant/index đã xuất bản.");
  const output = process.env.E2E_OUTPUT;
  if (!output) throw new Error("BLOCKED: cần thư mục report riêng cho cohort.");
  const reportPath = path.resolve(output, "retest9-answers.json");
  const cohort = `retest9-${Date.now()}`;
  const cases = TARGET_RETEST9_IDS.map((id) => {
    const item = benchmark.cases.find((c) => c.id === id);
    if (!item) throw new Error(`BLOCKED: thiếu case ${id}.`);
    resolveDocumentBinding(item, scenario.documents);
    return item;
  });
  const records: Retest9Record[] = cases.map((item) => ({
    id: item.id,
    group: item.group,
    scope: item.scope,
    target_doc: item.target_doc,
    question: item.question,
    status: "NOT_RUN",
    dispatched: false,
    client_elapsed_ms: 0,
    inference_ms: null,
    tokens: {},
    response: null,
  }));
  let baseline = "";
  let halted: string | null = null;
  const created = new Date().toISOString();
  let runtimeSnapshot: unknown;
  let observedInference: string | undefined;
  const save = () => {
    const report: Retest9Report = {
      cohort_id: cohort,
      benchmark_version: benchmark.version,
      created_at: created,
      updated_at: new Date().toISOString(),
      expected: 9,
      dispatched: records.filter((r) => r.dispatched).length,
      passed: records.filter((r) => r.status === "PASS").length,
      failed: records.filter((r) => r.status === "FAIL").length,
      uncertain: records.filter((r) => r.status === "UNCERTAIN").length,
      not_run: records.filter((r) => r.status === "NOT_RUN").length,
      halted,
      config_fingerprint: baseline,
      records,
    };
    writeFileSync(
      `${reportPath}.tmp`,
      `${JSON.stringify({ ...report, runtime_snapshot: runtimeSnapshot }, null, 2)}\n`,
      "utf8",
    );
    renameSync(`${reportPath}.tmp`, reportPath);
    return report;
  };
  save();
  const api = await authenticate(page);
  const timeout = await modelTimeout(api, state);
  setTimeout(Math.max(1_800_000, timeout * 12));
  const promptFile = path.resolve(
    "../backendV1/qnu/domains/rag/answer/drafting.py",
  );
  const backendPrompt = () =>
    readFileSync(promptFile, "utf8").match(/PROMPT_VERSION = "([^"]+)"/)?.[1];
  async function snapshot() {
    checkAllSources();
    const idx = await verifyAdmissionsIndex(api, state);
    const assistant = await api.get<Json>(
      `/workspaces/${state.workspace}/assistants/${scenario?.assistant}`,
    );
    const providers: Record<string, Json> = {};
    for (const capability of ["chat", "rerank", "embedding"] as const) {
      const id = state.runtimeDefaults?.[capability];
      if (!id) throw new Error("BLOCKED: thiếu model capability.");
      const provider = await api.get<Json>(`/modelops/providers/${id}`);
      if (!provider.is_active) throw new Error("BLOCKED: model disabled.");
      const resilience = await api.get<{
        policy: {
          max_key_attempts: number;
          fallbacks?: Record<string, string[]>;
        };
      }>(`/modelops/providers/${id}/resilience`);
      if (
        resilience.policy.max_key_attempts !== 1 ||
        Object.values(resilience.policy.fallbacks || {}).some(
          (ids) => ids.length,
        )
      )
        throw new Error("BLOCKED: retest không cho retry/fallback.");
      providers[capability] = { ...provider, resilience };
    }
    const reasoning = await api.get<{
      policy: {
        mode: string;
        parameter: string;
        off_value: unknown;
        verified: boolean;
        tasks: { off: string[] };
      };
    }>(`/modelops/providers/${state.runtimeDefaults?.chat}/reasoning`);
    const p = reasoning.policy;
    if (
      p.mode !== "chat_template_kwarg" ||
      p.parameter !== "enable_thinking" ||
      p.off_value !== false ||
      !p.verified ||
      !p.tasks.off.includes("answer")
    )
      throw new Error("BLOCKED: answer thinking chưa off.");
    const rag = assistant.rag_policy as Json;
    if (
      assistant.max_output_tokens !== 16384 ||
      rag.context_max_bytes !== 98304 ||
      assistant.chat_provider_id !== state.runtimeDefaults?.chat
    )
      throw new Error("BLOCKED: cấu hình assistant khác yêu cầu.");
    return {
      benchmark: fingerprint(benchmark),
      sources: Object.values(benchmark.documents).map((d) => d.sha256),
      index: fingerprint(idx.manifest),
      assistant,
      providers,
      reasoning,
      prompt_version: backendPrompt(),
    };
  }
  try {
    runtimeSnapshot = await snapshot();
    baseline = fingerprint(runtimeSnapshot);
    // Conservative stage admission, not a quota mutation or tokenizer claim.
    await requireAdmissionsQuota(api, state, 9 * (131072 + 4 * 65536));
    save();
    for (const [i, item] of cases.entries()) {
      if (halted) break;
      const r = records[i];
      const started = Date.now();
      let terminal = false;
      try {
        checkConfigDrift(baseline, fingerprint(await snapshot()));
        r.conversation_key = `${cohort}-${item.id}-conv`;
        r.turn_key = `${cohort}-${item.id}-turn`;
        const conv = await api.post<{ id: string }>(
          `/workspaces/${state.workspace}/conversations`,
          {
            assistant_id: scenario.assistant,
            document_ids: resolveDocumentBinding(item, scenario.documents),
          },
          r.conversation_key,
        );
        r.conversation_id = conv.id;
        save();
        const base = `/workspaces/${state.workspace}/conversations/${conv.id}/turns`;
        let turn: Turn;
        try {
          turn = await dispatchRetestOnce(r, save, () =>
            api.post<Turn>(
              base,
              { question: item.question, expected_turn_no: 0 },
              r.turn_key,
              timeout,
            ),
          );
        } catch {
          // Fresh owned conversation must contain exactly its one matching turn.
          // No POST retry, including HTTP failure after a committed server turn.
          const turns = await api.get<Turn[]>(base).catch(() => []);
          const matched = turns.filter(
            (t) =>
              t.conversation_id === conv.id &&
              t.question === item.question &&
              t.turn_no === 1,
          );
          if (turns.length !== 1 || matched.length !== 1)
            throw new Error(
              "uncertain: POST chưa đối soát được; chỉ GET, không gửi lại.",
            );
          turn = matched[0];
        }
        r.turn_id = turn.id;
        save();
        // Finite transport calls; no 300-second model deadline or second dispatch.
        while (
          !["completed", "failed", "uncertain", "cancelled"].includes(
            turn.status,
          )
        ) {
          await page.waitForTimeout(1000);
          turn = await api.get<Turn>(`${base}/${turn.id}`);
        }
        terminal = ["completed", "failed"].includes(turn.status);
        if (["uncertain", "cancelled"].includes(turn.status))
          throw new Error(`uncertain: ${turn.error_code || turn.status}`);
        if (turn.status === "failed") {
          r.status = "FAIL";
          r.error_code = turn.error_code || "unknown";
          r.error = `Turn failed: ${r.error_code}`;
          if (
            !new Set([
              "answer_response_invalid",
              "answer_cell_invalid",
              "answer_cell_selection_required",
              "answer_source_text_invalid",
              "answer_citation_invalid",
              "answer_verification_invalid",
              "chat_output_truncated",
            ]).has(r.error_code)
          )
            halted = r.error;
        } else {
          if (!turn.result)
            throw new Error("BLOCKED: completed thiếu response.");
          const answer = turn.result;
          r.response = answer;
          r.tokens = {
            prompt_tokens: answer.trace.prompt_tokens,
            completion_tokens: answer.trace.completion_tokens,
            total_tokens: answer.trace.total_tokens,
          };
          r.inference_ms = answer.trace.stage_ms?.generation ?? null;
          const trace = answer.trace as Answer["trace"] & {
            reasoning: { applied: boolean; value: unknown };
            inference_configuration_hash: string;
          };
          if (
            !trace.reasoning?.applied ||
            trace.reasoning.value !== false ||
            !trace.inference_configuration_hash ||
            trace.provider_id !== state.runtimeDefaults?.chat ||
            trace.retrieval.rerank_provider?.provider_id !==
              state.runtimeDefaults?.rerank ||
            trace.prompt_version !== backendPrompt()
          )
            throw new Error("DRIFT_DETECTED: request trace reasoning/prompt.");
          observedInference ||= trace.inference_configuration_hash;
          checkConfigDrift(
            observedInference,
            trace.inference_configuration_hash,
          );
          checkAdmissionAnswer(answer, item, state, benchmark.documents);
          r.status = "PASS";
        }
      } catch (error) {
        r.error = error instanceof Error ? error.message : String(error);
        r.status = r.dispatched && !terminal ? "UNCERTAIN" : "FAIL";
        if (r.status === "UNCERTAIN" || mustHaltRetest(r.error))
          halted = r.error;
      } finally {
        r.client_elapsed_ms = Date.now() - started;
        try {
          checkConfigDrift(baseline, fingerprint(await snapshot()));
        } catch (e) {
          halted = e instanceof Error ? e.message : String(e);
          if (r.status === "PASS") {
            r.status = "FAIL";
            r.error = halted;
          }
        }
        save();
        console.log(
          `${r.id}: ${r.status}, ${(r.client_elapsed_ms / 1000).toFixed(1)}s ${r.error || ""}`,
        );
      }
    }
  } catch (error) {
    halted = error instanceof Error ? error.message : String(error);
  } finally {
    save();
  }
  assertRunnerCompletion(save());
}
