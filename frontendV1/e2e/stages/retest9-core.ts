import { createHash } from "node:crypto";
import type { AdmissionCase } from "./admissions-context";
import type { Answer } from "./admissions-evaluation";

export const fingerprint = (value: unknown): string =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");

export const TARGET_RETEST9_IDS = [
  "F13",
  "F14",
  "I25-04",
  "I25-05",
  "BC24-05",
  "BC24-08",
  "MX-02",
  "MX-05",
  "MX-10",
] as const;

export type Retest9Id = (typeof TARGET_RETEST9_IDS)[number];

export interface Retest9Record {
  id: string;
  group: string;
  scope: string;
  target_doc: string;
  question: string;
  status: "NOT_RUN" | "PASS" | "FAIL" | "UNCERTAIN";
  dispatched: boolean;
  conversation_key?: string;
  conversation_id?: string;
  turn_key?: string;
  turn_id?: string;
  client_elapsed_ms: number;
  inference_ms: number | null;
  tokens: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
  };
  response: Answer | null;
  error?: string;
  error_code?: string;
}

export interface Retest9Report {
  benchmark_version: string;
  cohort_id: string;
  created_at: string;
  updated_at: string;
  expected: number;
  dispatched: number;
  passed: number;
  failed: number;
  not_run: number;
  uncertain: number;
  halted: string | null;
  config_fingerprint: string;
  records: Retest9Record[];
}

/**
 * Phân giải danh sách document ID cho câu hỏi.
 * BẮT BUỘC FAIL-CLOSED: Scope 'single' thiếu binding phải ném lỗi BLOCKED,
 * tuyệt đối không trả về undefined (mở thành scope all).
 */
export function resolveDocumentBinding(
  item: Pick<AdmissionCase, "id" | "scope" | "target_doc">,
  scenarioDocuments?: Record<string, { publication?: { document?: string } }>,
): string[] | undefined {
  if (item.scope === "single") {
    if (!item.target_doc) {
      throw new Error(
        `BLOCKED: Case ${item.id} có scope 'single' nhưng thiếu target_doc.`,
      );
    }
    const docEntry = scenarioDocuments?.[item.target_doc];
    const boundDocId = docEntry?.publication?.document;
    if (!boundDocId) {
      throw new Error(
        `BLOCKED: Không tìm thấy document binding cho target_doc '${item.target_doc}' của case ${item.id} trong scenario.`,
      );
    }
    return [boundDocId];
  }

  if (item.scope === "all") {
    // Với scope 'all', trả về undefined để backend tra cứu trên toàn bộ kho của assistant
    return undefined;
  }

  throw new Error(`BLOCKED: Scope không hợp lệ: '${item.scope}'.`);
}

/**
 * Tính toán fingerprint cấu hình thực tế của runtime để kiểm soát drift.
 */
export function buildCohortConfigFingerprint(input: {
  benchmarkVersion: string;
  benchmarkHash: string;
  indexId?: string;
  indexManifestHash?: string;
  assistant: {
    id: string;
    revision: number;
    max_output_tokens: number;
    context_max_bytes?: number;
  };
  provider: {
    id: string;
    model: string;
    reasoningPolicy?: unknown;
  };
  rerank: {
    id: string;
    model: string;
  };
  runtime?: unknown;
}): string {
  return fingerprint({
    benchmark_version: input.benchmarkVersion,
    benchmark_hash: input.benchmarkHash,
    index_id: input.indexId,
    index_manifest_hash: input.indexManifestHash,
    assistant: {
      id: input.assistant.id,
      revision: input.assistant.revision,
      max_output_tokens: input.assistant.max_output_tokens,
      context_max_bytes: input.assistant.context_max_bytes,
    },
    provider: {
      id: input.provider.id,
      model: input.provider.model,
      reasoning_policy: input.provider.reasoningPolicy,
    },
    rerank: {
      id: input.rerank.id,
      model: input.rerank.model,
    },
    runtime: input.runtime,
  });
}

/**
 * Kiểm tra drift cấu hình. Ném lỗi nếu phát hiện sai lệch so với baseline.
 */
export function checkConfigDrift(
  baselineHash: string,
  currentHash: string,
): void {
  if (baselineHash !== currentHash) {
    throw new Error(
      `DRIFT_DETECTED: Cấu hình runtime đã thay đổi giữa các câu hỏi (baseline: ${baselineHash}, hiện tại: ${currentHash}).`,
    );
  }
}

export function mustHaltRetest(message: string): boolean {
  return /DRIFT_DETECTED|BLOCKED:|quota_|provider_|timeout|ECONN|HTTP (401|403|429|5\d\d)|capacity_|input_limit|context_budget|uncertain/i.test(
    message,
  );
}

/** Persist intent before network I/O; an ambiguous result never authorizes a resend. */
export async function dispatchRetestOnce<T>(
  record: Retest9Record,
  persist: () => void,
  post: () => Promise<T>,
): Promise<T> {
  if (record.dispatched)
    throw new Error(
      "BLOCKED: request đã dispatch; chỉ GET đối soát, không POST lại.",
    );
  if (!record.conversation_id || !record.turn_key)
    throw new Error("BLOCKED: thiếu danh tính request.");
  record.dispatched = true;
  persist();
  return post();
}

/**
 * Kiểm tra tính toàn vẹn của kết quả runner.
 * BẮT BUỘC: Đủ 9 IDs duy nhất, không halted, và passed === 9, failed === 0, not_run === 0, uncertain === 0.
 * Ném lỗi nếu có bất kỳ câu nào chưa đạt hoặc có lỗi hạ tầng.
 */
export function assertRunnerCompletion(report: Retest9Report): void {
  // 1. Kiểm tra số lượng và danh tính các câu hỏi
  if (report.records.length !== 9) {
    throw new Error(
      `RUNNER_FAILURE: Số lượng records không khớp 9 (thực tế: ${report.records.length}).`,
    );
  }

  const seenIds = new Set<string>();
  for (const r of report.records) {
    if (!TARGET_RETEST9_IDS.includes(r.id as Retest9Id)) {
      throw new Error(
        `RUNNER_FAILURE: Gặp ID không thuộc phạm vi retest9: '${r.id}'.`,
      );
    }
    if (seenIds.has(r.id)) {
      throw new Error(
        `RUNNER_FAILURE: Phát hiện ID trùng lặp trong report: '${r.id}'.`,
      );
    }
    seenIds.add(r.id);
  }

  if (seenIds.size !== 9) {
    throw new Error(
      `RUNNER_FAILURE: Thiếu câu hỏi trong report (chỉ có ${seenIds.size}/9).`,
    );
  }

  // 2. Kiểm tra nếu bị dừng giữa chừng
  if (report.halted) {
    throw new Error(
      `RUNNER_HALTED: Cohort bị dừng do lỗi hạ tầng/drift: ${report.halted}`,
    );
  }

  // 3. Kiểm tra kết quả
  const unpassed = report.records.filter((r) => r.status !== "PASS");
  if (
    unpassed.length > 0 ||
    report.passed !== 9 ||
    report.failed > 0 ||
    report.not_run > 0 ||
    report.uncertain > 0
  ) {
    const details = unpassed
      .map(
        (r) => `${r.id}:${r.status}[${r.error_code || r.error || "unknown"}]`,
      )
      .join(", ");
    throw new Error(
      `RUNNER_INCOMPLETE: Có ${unpassed.length}/9 câu chưa đạt tiêu chuẩn PASS: ${details}`,
    );
  }
  if (
    report.expected !== 9 ||
    report.dispatched !== 9 ||
    report.records.some(
      (r) =>
        !r.dispatched ||
        !r.conversation_id ||
        !r.turn_id ||
        !r.turn_key ||
        !r.response,
    )
  )
    throw new Error(
      "RUNNER_FAILURE: PASS thiếu dispatch/turn/response thực tế.",
    );
  for (const field of ["conversation_id", "turn_id", "turn_key"] as const) {
    if (new Set(report.records.map((r) => r[field])).size !== 9)
      throw new Error("RUNNER_FAILURE: trùng danh tính lượt hỏi.");
  }
}
