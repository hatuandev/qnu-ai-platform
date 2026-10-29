import { createHash } from "node:crypto";
import { readFileSync, renameSync, writeFileSync } from "node:fs";
import path from "node:path";
import { type APIResponse, expect, type Page } from "@playwright/test";

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
  review?: string;
  document?: string;
  version?: string;
  index?: string;
}
export interface Checkpoint {
  runId: string;
  mode: "workflow" | "live";
  results: Record<string, { status: string }>;
  workspace?: string;
  collection?: string;
  folder?: string;
  provider?: string;
  sources: Source[];
  publications?: Publication[];
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
      timeout: 180_000,
    });
  }
  async json<T>(
    method: string,
    suffix: string,
    body?: unknown,
    key?: string,
  ): Promise<T> {
    const response = await this.raw(method, suffix, body, key);
    await requireOk(response, method, suffix);
    if (response.status() === 204) return undefined as T;
    return (await response.json()) as T;
  }
  get<T>(suffix: string): Promise<T> {
    return this.json<T>("GET", suffix);
  }
  post<T>(suffix: string, body: unknown, key?: string): Promise<T> {
    return this.json<T>("POST", suffix, body, key);
  }
  async wait<T extends Run>(suffix: string): Promise<T> {
    let last: T | undefined;
    await expect
      .poll(
        async () => {
          last = await this.get<T>(suffix);
          if (["failed", "cancelled", "rejected"].includes(last.status)) {
            throw new Error(
              `Job ${last.id}: ${last.status}; code=${last.error_code || "unknown"}`,
            );
          }
          return last.status;
        },
        { timeout: 240_000, intervals: [300, 700, 1500] },
      )
      .toBe("completed");
    if (!last) throw new Error("Không có trạng thái job.");
    return last;
  }
  async upload(state: Checkpoint, file: string, idempotencyKey: string) {
    const bytes = readFileSync(path.join(directory, "fixtures", file));
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

export async function ensureSessionQuota(api: Api, state: Checkpoint) {
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
  if (!quota.configured) {
    if (state.mode !== "workflow") {
      throw new Error(
        "BLOCKED: cần cấu hình quota tháng hiện tại trong workspace E2E trước khi gọi model thật.",
      );
    }
    // A finite fixture allowance; never disable accounting or change an existing limit.
    quota = await api.json<Quota>("PUT", base, {
      monthly_token_limit: 1_000_000,
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
