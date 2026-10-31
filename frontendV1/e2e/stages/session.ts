import { createHash } from "node:crypto";
import { readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { type APIResponse, expect, type Page } from "@playwright/test";
import { progressWaitMs } from "./progress-budget";

export interface Source {
  id: string;
  revision: string;
  run: string;
  file: string;
  sha256: string;
  textVersion?: number;
  quotaRecoveryRunIds?: string[];
}
export interface Publication {
  run: string;
  compilationRecoveryOf?: string;
  review?: string;
  reviewAttempts?: number;
  reviewHistory?: string[];
  document?: string;
  version?: string;
  index?: string;
}
export interface Checkpoint {
  runId: string;
  mode: "workflow" | "live";
  results: Record<string, { status: string; report?: string }>;
  runtimeDefaults?: Record<"chat" | "embedding" | "rerank" | "ocr", string>;
  providerSetup?: {
    connectionId: string;
    keyId: string;
    createdConnection?: boolean;
    createdKey?: boolean;
    modelsRegistered?: boolean;
  };
  chatSelection?: "qnu" | "router";
  routerProviderSetup?: Checkpoint["providerSetup"];
  workspace?: string;
  collection?: string;
  folder?: string;
  provider?: string;
  sources: Source[];
  publications?: Publication[];
  compilationHistory?: Publication[];
  admissions?: {
    collection?: string;
    source?: Source;
    publication?: Publication;
    compilationHistory?: Publication[];
    assistant?: string;
    queries?: Record<string, { conversation: string; turn?: string }>;
    queryHistory?: {
      case_id: string;
      conversation: string;
      turn?: string;
      status: string;
      reason?: string;
      error_code?: string;
    }[];
  };
  assistant?: string;
  conversation?: string;
  deletion?: string;
  replacement?: string;
  guardVerified?: boolean;
  paused?: boolean;
  withdrawn?: boolean;
}
export interface Run {
  id: string;
  provider_id?: string | null;
  status: string;
  error_code?: string;
  pages_total?: number;
  pages_done?: number;
  results_ready?: boolean;
  is_active?: boolean;
  chunks_total?: number;
}
export interface Action extends Run {
  preview_sha256: string;
  result?: {
    permanent: boolean;
    originals_retained: boolean;
    restore_available: boolean;
  };
}
export const directory = path.resolve(
  process.env.E2E_SESSION || ".missing-e2e-session",
);
if (!process.env.E2E_SESSION || !process.env.E2E_STAGE) {
  throw new Error(
    "Dùng .\\test-v1-e2e.ps1 init / serve / run <stage>; không chạy suite trực tiếp.",
  );
}
const manifest = JSON.parse(
  readFileSync(path.join(directory, "manifest.json"), "utf8"),
) as {
  run_id: string;
  mode: string;
  ports: { api: number; mock: number; frontend: number };
  cleaned: boolean;
};
if (
  !/^[a-f0-9]{12}$/.test(manifest.run_id) ||
  manifest.cleaned ||
  path.basename(directory) !== manifest.run_id
) {
  throw new Error("Phiên thử không hợp lệ hoặc đã dọn.");
}
export const apiRoot = `http://127.0.0.1:${manifest.ports.api}/platform/v1alpha1`;
export const mockRoot = `http://127.0.0.1:${manifest.ports.mock}/v1`;
export function checkpoint(): Checkpoint {
  const state = JSON.parse(
    readFileSync(path.join(directory, "checkpoint.json"), "utf8"),
  ) as Checkpoint;
  if (state.runId !== manifest.run_id)
    throw new Error("Checkpoint khác phiên.");
  return state;
}
export function save(state: Checkpoint) {
  const target = path.join(directory, "checkpoint.json");
  writeFileSync(`${target}.tmp`, `${JSON.stringify(state, null, 2)}\n`, "utf8");
  renameSync(`${target}.tmp`, target);
}
export function workspace(state: Checkpoint) {
  if (!state.workspace) throw new Error("BLOCKED: chưa có workspace thử.");
  return `/workspaces/${state.workspace}`;
}
export function collection(state: Checkpoint) {
  if (!state.collection) throw new Error("BLOCKED: chưa có kho thử.");
  return `${workspace(state)}/collections/${state.collection}`;
}
export function sourceBase(state: Checkpoint, source: Source) {
  return `${collection(state)}/sources/${source.id}`;
}
export function processing(state: Checkpoint, source: Source) {
  return `${sourceBase(state, source)}/revisions/${source.revision}/processing-runs/${source.run}`;
}
export function versionBase(state: Checkpoint, publication: Publication) {
  if (!publication.document || !publication.version)
    throw new Error("BLOCKED: chưa có phiên bản.");
  return `${collection(state)}/compiled-documents/${publication.document}/versions/${publication.version}`;
}
export const sha256 = (bytes: Buffer) =>
  createHash("sha256").update(bytes).digest("hex");

export class Api {
  constructor(
    readonly page: Page,
    readonly token: string,
  ) {}
  async raw(
    method: string,
    suffix: string,
    body?: unknown,
    key?: string,
    token = this.token,
    timeoutMs = 180_000,
  ) {
    if (!suffix.startsWith("/") || suffix.includes("://"))
      throw new Error("API path ngoài phiên.");
    return this.page.request.fetch(`${apiRoot}${suffix}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(key ? { "Idempotency-Key": key } : {}),
      },
      data: body,
      timeout: timeoutMs,
    });
  }
  async json<T>(
    method: string,
    suffix: string,
    body?: unknown,
    key?: string,
    timeoutMs = 180_000,
  ): Promise<T> {
    const response = await this.raw(
      method,
      suffix,
      body,
      key,
      undefined,
      timeoutMs,
    );
    await requireOk(response, method, suffix);
    if (response.status() === 204) return undefined as T;
    return (await response.json()) as T;
  }
  get<T>(suffix: string): Promise<T> {
    return this.json<T>("GET", suffix);
  }
  post<T>(
    suffix: string,
    body: unknown,
    key?: string,
    timeoutMs = 180_000,
  ): Promise<T> {
    return this.json<T>("POST", suffix, body, key, timeoutMs);
  }
  async wait<T extends Run>(suffix: string, timeoutMs = 240_000): Promise<T> {
    let last: T | undefined;
    await expect
      .poll(
        async () => {
          last = await this.get<T>(suffix);
          if (
            ["failed", "cancelled", "rejected", "uncertain"].includes(
              last.status,
            )
          ) {
            throw new Error(
              `Job ${last.id}: ${last.status}; code=${last.error_code || "unknown"}`,
            );
          }
          return last.status;
        },
        { timeout: timeoutMs, intervals: [300, 700, 1500] },
      )
      .toBe("completed");
    if (!last) throw new Error("Không có trạng thái job.");
    return last;
  }
  /**
   * Poll a durable progress endpoint and grant one model call per observed part.
   * The part count is read before polling; it is never inferred from elapsed time.
   * A line is printed only when the observed state changes, never on every poll.
   */
  async waitProgress<
    T extends {
      status: string;
      total: number;
      completed?: number;
      running?: number;
      active_segments?: number[];
      concurrency?: number;
      elapsed_seconds?: number | null;
      queue_timeout_seconds?: number;
      refinement_timeout_seconds?: number;
      nodes?: { index: number; status: string }[];
      segments?: { status: string; error_code?: string | null }[];
    },
  >(suffix: string, perPartMs: number, minMs = 240_000): Promise<T> {
    let last = await this.get<T>(suffix);
    const timeoutMs = Math.max(
      (last.refinement_timeout_seconds ?? 0) * 1000 + 60_000,
      progressWaitMs(
        last.total,
        last.concurrency ?? 1,
        perPartMs,
        (last.queue_timeout_seconds ?? 0) * 1000,
        minMs,
      ),
    );
    const describe = (value: T) =>
      [
        `status=${value.status}`,
        `parts=${value.completed ?? 0}/${value.total}`,
        `running=${value.running ?? 0}`,
        `concurrency=${value.concurrency ?? 1}`,
        `active=[${(value.active_segments ?? []).join(",")}]`,
        `nodes=[${(value.nodes ?? []).map((node) => `${node.index}:${node.status}`).join(",")}]`,
      ].join(" ");
    let seen = describe(last);
    console.info(`Tiến độ: ${seen} elapsed=${last.elapsed_seconds ?? 0}s`);
    await expect
      .poll(
        async () => {
          last = await this.get<T>(suffix);
          const current = describe(last);
          if (current !== seen) {
            seen = current;
            console.info(
              `Tiến độ: ${current} elapsed=${last.elapsed_seconds ?? 0}s`,
            );
          }
          if (
            ["failed", "cancelled", "rejected", "uncertain"].includes(
              last.status,
            )
          ) {
            const part = last.segments?.find(
              (segment) => segment.status === last.status || segment.error_code,
            );
            throw new Error(
              `Job: ${last.status}; part=${part?.status || "unknown"}; ` +
                `code=${part?.error_code || "unknown"}; ${JSON.stringify(last.segments || [])}`,
            );
          }
          return last.status;
        },
        { timeout: timeoutMs, intervals: [300, 700, 1500] },
      )
      .toBe("completed");
    return last;
  }
  async upload(
    state: Checkpoint,
    file: string,
    idempotencyKey: string,
    sourcePath?: string,
  ) {
    const bytes = readFileSync(
      sourcePath ?? path.join(directory, "fixtures", file),
    );
    const response = await this.page.request.post(
      `${apiRoot}${collection(state)}/sources`,
      {
        headers: {
          Authorization: `Bearer ${this.token}`,
          "Idempotency-Key": idempotencyKey,
        },
        multipart: {
          file: {
            name: file,
            mimeType: file.endsWith(".pdf")
              ? "application/pdf"
              : "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            buffer: bytes,
          },
          auto_extract: "true",
          ...(state.folder ? { folder_id: state.folder } : {}),
        },
      },
    );
    await requireOk(response, "UPLOAD", file);
    expect([200, 201]).toContain(response.status());
    const result = (await response.json()) as {
      source: { id: string; processing: Run | null };
      revision: { id: string };
    };
    if (!result.source.processing)
      throw new Error("Upload không tạo processing run.");
    return {
      id: result.source.id,
      revision: result.revision.id,
      run: result.source.processing.id,
      file,
      sha256: sha256(bytes),
    } satisfies Source;
  }
}

export async function ensureSessionQuota(
  api: Api,
  state: Checkpoint,
  liveTestAllowance?: number,
) {
  const owner = await api.get<{ code: string }>(workspace(state));
  if (owner.code !== `e2e-${state.runId}`) {
    throw new Error(
      "BLOCKED: workspace không thuộc phiên E2E, từ chối cấu hình quota.",
    );
  }
  const base = `${workspace(state)}/quota`;
  type Quota = {
    configured: boolean;
    is_blocked: boolean;
    monthly_token_limit: number | null;
    tokens_used: number;
    tokens_reserved: number;
  };
  let quota = await api.get<Quota>(base);
  if (
    !quota.configured ||
    (liveTestAllowance !== undefined &&
      quota.monthly_token_limit !== null &&
      quota.monthly_token_limit < liveTestAllowance)
  ) {
    if (state.mode !== "workflow" && liveTestAllowance === undefined) {
      throw new Error(
        "BLOCKED: cần cấu hình quota tháng hiện tại trong workspace E2E trước khi gọi model thật.",
      );
    }
    // A finite fixture allowance; never disable accounting or change an existing limit.
    quota = await api.json<Quota>("PUT", base, {
      monthly_token_limit: liveTestAllowance ?? 5_000_000,
      is_blocked: false,
    });
  }
  expect(quota.configured).toBe(true);
  if (
    quota.is_blocked ||
    (quota.monthly_token_limit !== null &&
      quota.tokens_used + quota.tokens_reserved >= quota.monthly_token_limit)
  ) {
    throw new Error(
      "BLOCKED: quota phiên thử đang khóa hoặc đã hết; không tự tăng/đặt lại usage.",
    );
  }
}

export async function recoverMissingQuotaRun(
  api: Api,
  state: Checkpoint,
  source: Source,
) {
  const failed = await api.get<Run>(processing(state, source));
  if (
    failed.status !== "failed" ||
    failed.error_code !== "quota_not_configured"
  )
    return;
  if (
    state.mode !== "workflow" ||
    state.publications?.length ||
    source.quotaRecoveryRunIds?.length
  ) {
    throw new Error(
      "BLOCKED: job quota lỗi cần kiểm tra thủ công; không lặp OCR hay đổi nguồn đã biên soạn.",
    );
  }
  const previousId = source.run;
  const created = await api.post<{ run: Run }>(
    `${sourceBase(state, source)}/revisions/${source.revision}/processing-runs`,
    {
      strategy: "auto",
      force: false,
    },
  );
  expect(created.run.id).not.toBe(previousId);
  source.quotaRecoveryRunIds = [previousId];
  source.run = created.run.id;
  delete source.textVersion;
  save(state);
}
export async function requireOk(
  response: Pick<APIResponse, "ok" | "status" | "json">,
  method: string,
  suffix: string,
) {
  if (!response.ok()) {
    const problem = (await response.json().catch(() => ({}))) as {
      code?: string;
    };
    throw new Error(
      `${method} ${suffix}: HTTP ${response.status()}, code=${problem.code || "unknown"}`,
    );
  }
}
export async function authenticate(page: Page) {
  const [response] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().endsWith("/__qnu_dev/auto-login") &&
        r.request().method() === "POST",
    ),
    page.goto("/dashboard"),
  ]);
  await requireOk(response, "AUTH", "dev bridge");
  const auth = (await response.json()) as { access_token?: string };
  if (!auth.access_token) throw new Error("Dev bridge không trả token.");
  await expect(page.getByRole("banner")).toBeVisible();
  return new Api(page, auth.access_token);
}
