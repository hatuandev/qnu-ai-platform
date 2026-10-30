import { readFileSync } from "node:fs";
import path from "node:path";
import { expect } from "@playwright/test";
import { benchmark, checkSource, context, sourcePath } from "./admissions-context";
import {
  type Api, type Checkpoint, ensureSessionQuota, processing,
  requireOk, save, sha256, sourceBase, workspace,
} from "./session";

export async function uploadAdmissionSource(api: Api, state: Checkpoint) {
  checkSource();
  state.admissions ||= {};
  await ensureSessionQuota(api, state);
  if (!state.admissions.collection) {
    const created = await api.post<{ id: string }>(`${workspace(state)}/collections`, {
      name: `TB điểm sàn 2026 — ${state.runId}`,
      description: "Chỉ một PDF đã chốt hash; không trộn tài liệu tuyển sinh khác.",
    });
    state.admissions.collection = created.id;
    save(state);
  }
  if (!state.admissions.source) {
    state.admissions.source = await api.upload(
      context(state), path.basename(sourcePath), `${state.runId}-floor-upload`, sourcePath,
    );
    save(state);
  }
  expect(state.admissions.source.sha256).toBe(benchmark.source.sha256);
  const response = await api.raw(
    "GET", `${sourceBase(context(state), state.admissions.source)}/revisions/${state.admissions.source.revision}/content`,
  );
  await requireOk(response, "GET", "PDF gốc điểm sàn");
  expect(sha256(await response.body())).toBe(sha256(readFileSync(sourcePath)));
}

export async function extractAdmissionSource(api: Api, state: Checkpoint) {
  const source = state.admissions?.source;
  if (!source) throw new Error("BLOCKED: chưa upload TB điểm sàn 26.");
  const config = await api.get<{ timeout_seconds: number }>(
    `/modelops/providers/${state.runtimeDefaults?.ocr}`,
  );
  const run = await api.wait(
    processing(context(state), source),
    (config.timeout_seconds + 30) * 1000 * benchmark.source.pages,
  );
  expect(run.results_ready).toBe(true);
  expect(run.pages_total).toBe(benchmark.source.pages);
  expect(run.pages_done).toBe(run.pages_total);
  console.info(`Đã bóc tách đủ ${run.pages_done} trang; giữ nguyên PDF nguồn.`);
}
