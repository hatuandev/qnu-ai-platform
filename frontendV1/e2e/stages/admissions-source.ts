import { readFileSync } from "node:fs";
import path from "node:path";
import { expect } from "@playwright/test";
import {
  benchmark,
  checkAllSources,
  context,
  docPaths,
} from "./admissions-context";
import { requireAdmissionsQuota } from "./admissions-policy";
import {
  type Api,
  type Checkpoint,
  processing,
  requireOk,
  save,
  sha256,
  sourceBase,
  workspace,
} from "./session";

export async function uploadAdmissionSource(api: Api, state: Checkpoint) {
  checkAllSources();
  state.admissions ||= {};
  state.admissions.documents ||= {};
  // Admission only; upload never changes an operator's monthly allowance.
  await requireAdmissionsQuota(api, state);

  if (!state.admissions.collection) {
    const created = await api.post<{ id: string }>(
      `${workspace(state)}/collections`,
      {
        name: `Tuyển sinh QNU (3 tài liệu) — ${state.runId}`,
        description:
          "Bộ tài liệu tuyển sinh QNU: Điểm sàn 2026 (8 trang), Thông tin 2025 (13 trang), Báo cáo 2024 (7 trang).",
      },
    );
    state.admissions.collection = created.id;
    save(state);
  }

  for (const [key, docMeta] of Object.entries(benchmark.documents)) {
    const filePath = docPaths[key];
    if (!state.admissions.documents[key]) {
      state.admissions.documents[key] = { key };
    }
    const entry = state.admissions.documents[key];
    if (!entry.source) {
      entry.source = await api.upload(
        context(state),
        path.basename(filePath),
        `${state.runId}-${key}-upload`,
        filePath,
      );
      if (key === "floor2026") {
        state.admissions.source = entry.source;
      }
      save(state);
    }
    expect(entry.source.sha256).toBe(docMeta.sha256);
    const response = await api.raw(
      "GET",
      `${sourceBase(context(state), entry.source)}/revisions/${entry.source.revision}/content`,
    );
    await requireOk(response, "GET", `PDF gốc ${key}`);
    expect(sha256(await response.body())).toBe(sha256(readFileSync(filePath)));
  }

  // Tương thích ngược
  if (state.admissions.documents.floor2026?.source) {
    state.admissions.source = state.admissions.documents.floor2026.source;
  }
}

export async function extractAdmissionSource(api: Api, state: Checkpoint) {
  if (!state.admissions?.documents) {
    throw new Error("BLOCKED: chưa upload bộ tài liệu tuyển sinh.");
  }
  const config = await api.get<{ timeout_seconds: number }>(
    `/modelops/providers/${state.runtimeDefaults?.ocr}`,
  );

  let totalPagesExtracted = 0;
  for (const [key, docMeta] of Object.entries(benchmark.documents)) {
    const entry = state.admissions.documents[key];
    if (!entry?.source) {
      throw new Error(`BLOCKED: chưa có source cho ${key}.`);
    }
    const run = await api.wait(
      processing(context(state), entry.source),
      (config.timeout_seconds + 30) * 1000 * docMeta.pages,
    );
    expect(run.results_ready).toBe(true);
    expect(run.pages_total).toBe(docMeta.pages);
    expect(run.pages_done).toBe(run.pages_total);
    totalPagesExtracted += run.pages_done ?? 0;
    console.info(
      `Đã bóc tách đủ ${run.pages_done}/${docMeta.pages} trang cho ${key} (${path.basename(docPaths[key])}).`,
    );
  }
  console.info(
    `Hoàn tất OCR extraction cho cả 3 tài liệu: tổng ${totalPagesExtracted} trang.`,
  );
}
