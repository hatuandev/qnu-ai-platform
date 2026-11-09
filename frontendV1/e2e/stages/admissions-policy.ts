import { createHash } from "node:crypto";
import { benchmark, context } from "./admissions-context";
import { type Api, type Checkpoint, collection, save } from "./session";

export const fingerprint = (value: unknown): string =>
  createHash("sha256").update(JSON.stringify(value)).digest("hex");

export async function requireAdmissionsQuota(
  api: Pick<Api, "get">,
  state: Checkpoint,
  required = 1,
) {
  const quota = await api.get<{
    configured: boolean;
    is_blocked: boolean;
    monthly_token_limit: number | null;
    tokens_used: number;
    tokens_reserved: number;
  }>(`/workspaces/${state.workspace}/quota`);
  if (
    !quota.configured ||
    quota.is_blocked ||
    (quota.monthly_token_limit !== null &&
      quota.monthly_token_limit - quota.tokens_used - quota.tokens_reserved <
        required)
  ) {
    throw new Error(
      `BLOCKED: quota chưa sẵn sàng; cần ${required} token theo dự toán chặng. Kiểm tra ModelOps; không tự tăng/reset quota.`,
    );
  }
  return quota;
}

export interface IndexManifest {
  run_id: string;
  inputs: NonNullable<NonNullable<Checkpoint["admissions"]>["indexInputs"]>;
  config: { chunk_max_bytes: number };
  chunks: { id: string }[];
}

export async function verifyAdmissionsIndex(
  api: Pick<Api, "get">,
  state: Checkpoint,
) {
  const scenario = state.admissions;
  if (!scenario?.combinedIndex)
    throw new Error("BLOCKED: thiếu combined index.");
  const run = await api.get<{
    status: string;
    is_active: boolean;
    provider_id: string;
  }>(`${collection(context(state))}/indexing-runs/${scenario.combinedIndex}`);
  if (
    run.status !== "completed" ||
    !run.is_active ||
    run.provider_id !== state.runtimeDefaults?.embedding
  )
    throw new Error(
      "BLOCKED: index chưa active hoặc embedding provider đã đổi.",
    );
  const manifest = await api.get<IndexManifest>(
    `${collection(context(state))}/indexing-runs/${scenario.combinedIndex}/manifest`,
  );
  if (
    manifest.run_id !== scenario.combinedIndex ||
    manifest.inputs.length !== Object.keys(benchmark.documents).length ||
    !manifest.chunks.length
  ) {
    throw new Error("BLOCKED: index không chứa đúng bộ ba tài liệu.");
  }
  const expected = Object.keys(benchmark.documents).map(
    (key) => scenario.documents?.[key]?.publication?.document,
  );
  if (
    expected.some((id) => !id) ||
    new Set(expected).size !== expected.length ||
    new Set(manifest.inputs.map((i) => i.document_id)).size !==
      expected.length ||
    manifest.inputs.some((i) => !expected.includes(i.document_id))
  )
    throw new Error("BLOCKED: tập document của index không khớp checkpoint.");
  const published = [];
  for (const key of Object.keys(benchmark.documents)) {
    const entry = scenario.documents?.[key];
    if (
      !entry?.source ||
      !entry.publication?.document ||
      !entry.publication.version
    )
      throw new Error(`BLOCKED: chưa xuất bản ${key}.`);
    const value = await api.get<{
      version: { id: string; bundle_sha256: string; state_version: number };
      decision: { id: string };
      content: unknown;
    }>(
      `${collection(context(state))}/compiled-documents/${entry.publication.document}/published`,
    );
    const input = manifest.inputs.find(
      (i) => i.document_id === entry.publication?.document,
    );
    if (
      !input ||
      input.version_id !== entry.publication.version ||
      value.version.id !== input.version_id ||
      value.decision.id !== input.publication_decision_id ||
      value.version.bundle_sha256 !== input.bundle_sha256 ||
      value.version.state_version !== input.version_state
    )
      throw new Error(`BLOCKED: index/publication ${key} đã đổi.`);
    published.push({
      key,
      content_bytes: Buffer.byteLength(JSON.stringify(value.content)),
      bundle: input.bundle_sha256,
    });
  }
  scenario.indexInputs = manifest.inputs;
  save(state);
  return { manifest, published };
}

interface Provider {
  model_name: string;
  capacity_status: string;
  token_limits: {
    context_window_tokens?: number | null;
    max_input_tokens?: number | null;
    max_output_tokens?: number | null;
  } | null;
}
export function planAdmissionsBudget(provider: Provider) {
  const limits = provider.token_limits;
  if (
    provider.capacity_status !== "configured" ||
    !limits?.max_output_tokens ||
    (!limits.max_input_tokens && !limits.context_window_tokens)
  )
    throw new Error("BLOCKED: capacity model chưa xác minh.");
  const output = limits.max_output_tokens;
  if (!Number.isSafeInteger(output) || output < 4096)
    throw new Error(
      "BLOCKED: profile benchmark cần output tối thiểu 4096 token.",
    );
  // Conservative UTF-8 byte envelope. ModelOps still measures the complete final
  // prompt/schema/catalog at dispatch; this reserve is not a tokenizer guarantee.
  const overhead = 16_384;
  const input = Math.min(
    limits.max_input_tokens ?? Infinity,
    (limits.context_window_tokens ?? Infinity) - output,
  );
  const contextBytes = Math.min(128_000, input - overhead);
  if (contextBytes < 256)
    throw new Error("BLOCKED: capacity không đủ cho evidence và prompt.");
  return {
    context_max_bytes: contextBytes,
    max_output_tokens: output,
    input_tokens_plan: contextBytes + overhead,
    overhead_reserve_bytes: overhead,
  };
}

// Planning ratio for rerank input. Vietnamese UTF-8 text spends 2-3 bytes per
// character, so tokenizers normally emit well under one token per byte; 2 is a
// conservative planning value, never a tokenizer guarantee.
export const RERANK_PLAN_BYTES_PER_TOKEN = 2;

export function planAdmissionsRerankPair(
  provider: Provider,
  chunkMaxBytes: number,
  maxQuestionBytes: number,
) {
  const limits = provider.token_limits;
  const limit = limits?.max_input_tokens ?? limits?.context_window_tokens;
  if (provider.capacity_status !== "configured" || !limit)
    throw new Error("BLOCKED: chưa biết capacity rerank.");
  // Mirrors the production per-pair byte bound in modelops/rerank.py budget().
  const pairBytes = chunkMaxBytes + maxQuestionBytes + 64;
  if (!Number.isSafeInteger(pairBytes) || pairBytes < 1)
    throw new Error("BLOCKED: dự toán cặp query/chunk không hợp lệ.");
  const tokenEstimate = Math.ceil(pairBytes / RERANK_PLAN_BYTES_PER_TOKEN);
  // A token cannot decode to fewer than one UTF-8 byte, so byte count bounds
  // tokens from above. The production guard compares this same byte count to
  // the token limit; the estimate above is for quota planning only.
  const tokenUpperBound = pairBytes + 2;
  if (pairBytes > limit)
    throw new Error(
      "BLOCKED: cận trên byte của cặp query/chunk vượt rerank input; kiểm tra cấu hình index/provider.",
    );
  return {
    pair_bytes: pairBytes,
    input_tokens_limit: limit,
    plan_bytes_per_token: RERANK_PLAN_BYTES_PER_TOKEN,
    token_estimate: tokenEstimate,
    token_upper_bound: tokenUpperBound,
    worst_case_within_byte_guard: pairBytes <= limit,
  };
}

export function freezeCohort(state: Checkpoint, value: unknown) {
  const scenario = state.admissions;
  if (!scenario) throw new Error("BLOCKED: thiếu admissions.");
  const hash = fingerprint(value);
  if (scenario.cohort && scenario.cohort.fingerprint !== hash)
    throw new Error(
      "BLOCKED: cấu hình/index/benchmark cohort đã đổi; không trộn kết quả.",
    );
  scenario.cohort ||= { fingerprint: hash };
  save(state);
  return scenario.cohort;
}
