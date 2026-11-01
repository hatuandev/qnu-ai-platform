import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { requireAdmissionsQuota } from "./admissions-policy";
import {
  assessScan,
  type ScanDocument,
  type ScanReference,
} from "./scan-ocr-assessment";
import {
  authenticate,
  type Checkpoint,
  checkpoint,
  processing,
  requireOk,
  save,
  sha256,
} from "./session";

test.use({ trace: "off", video: "off", screenshot: "off" });
test("Quy chế 363: OCR thật 32 trang scan, raw/canonical và mẫu đối chiếu", async ({
  page,
}) => {
  if (process.env.E2E_STAGE !== "admissions-scan-ocr")
    throw new Error("Wrong OCR stage");
  const state = checkpoint();
  if (state.mode !== "live" || !state.workspace || !state.runtimeDefaults?.ocr)
    throw new Error("BLOCKED: cần navigation và model OCR thật.");
  const reference = JSON.parse(
    readFileSync(path.resolve("e2e/data/admissions-scan-ocr.json"), "utf8"),
  ) as ScanReference;
  const file = path.resolve("..", reference.source.path);
  expect(
    sha256(readFileSync(file)),
    "PDF changed; revalidate visual labels before inference",
  ).toBe(reference.source.sha256);
  const api = await authenticate(page);
  const provider = await api.get<{
    id: string;
    model_name: string;
    base_url: string;
    timeout_seconds: number;
    is_active: boolean;
    token_limits: unknown;
  }>(`/modelops/providers/${state.runtimeDefaults.ocr}`);
  expect(provider.is_active).toBe(true);
  const snapshot = createHash("sha256")
    .update(JSON.stringify(provider))
    .digest("hex");
  const timeout = Math.max(
    300_000,
    (provider.timeout_seconds + 30) * 1000 * reference.source.pages,
  );
  test.setTimeout(timeout + 120_000);
  await requireAdmissionsQuota(api, state);
  state.scanOcr ||= {};
  if (
    state.scanOcr.providerSnapshotSha256 &&
    state.scanOcr.providerSnapshotSha256 !== snapshot
  )
    throw new Error(
      "BLOCKED: cấu hình OCR đã đổi; giữ lượt cũ, không tự gửi lại.",
    );
  state.scanOcr.providerId = provider.id;
  state.scanOcr.modelName = provider.model_name;
  state.scanOcr.providerSnapshotSha256 = snapshot;
  if (!state.scanOcr.collection) {
    const collection = await api.post<{ id: string }>(
      `/workspaces/${state.workspace}/collections`,
      {
        name: `OCR Quy chế 363 — ${state.runId}`,
        description:
          "PDF scan riêng cho nghiệm thu OCR; không xuất bản hoặc đổi index của bộ 53 câu.",
      },
    );
    state.scanOcr.collection = collection.id;
    save(state);
  }
  const context: Checkpoint = {
    ...state,
    collection: state.scanOcr.collection,
    folder: undefined,
  };
  if (!state.scanOcr.source) {
    if (state.scanOcr.uploadDispatched)
      throw new Error(
        "BLOCKED: upload trước chưa rõ kết quả; không gửi lại để làm xanh.",
      );
    state.scanOcr.uploadDispatched = true;
    save(state);
    state.scanOcr.source = await api.upload(
      context,
      path.basename(file),
      `${state.runId}-scan363-upload-v1`,
      file,
    );
    save(state);
  }
  let source = state.scanOcr.source;
  const renderDpi = process.env.E2E_SCAN_OCR_DPI;
  if (renderDpi) {
    const dpi = Number(renderDpi);
    if (!Number.isInteger(dpi) || dpi < 72 || dpi > 300)
      throw new Error("Invalid explicit OCR DPI");
    state.scanOcr.experiments ||= {};
    const experiments = state.scanOcr.experiments;
    const key = `dpi-${dpi}`;
    experiments[key] ||= { dispatched: false };
    const experiment = experiments[key];
    if (!experiment.source) {
      if (experiment.dispatched)
        throw new Error(
          "BLOCKED: lượt DPI trước chưa rõ kết quả; không gửi lại.",
        );
      experiment.dispatched = true;
      save(state);
      const oldBase = processing(context, source);
      const result = await api.post<{ run: { id: string } }>(
        oldBase.slice(0, oldBase.lastIndexOf("/")),
        { provider_id: provider.id, strategy: "auto", render_dpi: dpi },
      );
      experiment.source = { ...source, run: result.run.id };
      save(state);
    }
    source = experiment.source;
  }
  const base = processing(context, source);
  const started = Date.now();
  let observed = "";
  await expect
    .poll(
      async () => {
        const run = await api.get<{
          status: string;
          provider_id: string;
          pages_done: number;
          pages_total: number;
          pages_failed: number;
          error_code: string | null;
        }>(base);
        const progress = `${run.status} ${run.pages_done}/${run.pages_total ?? "?"} failed=${run.pages_failed}`;
        if (progress !== observed) {
          observed = progress;
          console.info(
            `OCR ${provider.model_name}: ${progress}; elapsed=${((Date.now() - started) / 1000).toFixed(1)}s`,
          );
        }
        if (["failed", "uncertain", "cancelled"].includes(run.status))
          throw new Error(
            `OCR ${run.status}: ${run.error_code ?? "unknown"}; giữ nguyên lượt, không retry.`,
          );
        if (run.status === "completed")
          expect(run.provider_id).toBe(provider.id);
        return run.status;
      },
      { timeout, intervals: [500, 1000, 2000] },
    )
    .toBe("completed");
  const document = await api.get<ScanDocument>(`${base}/document`);
  const manifest = await api.get<Record<string, unknown>>(`${base}/manifest`);
  const assessment = assessScan(document, reference);
  const output = process.env.E2E_OUTPUT;
  if (!output) throw new Error("Missing report directory");
  writeFileSync(
    path.join(output, "ocr-assessment.json"),
    `${JSON.stringify({ model_name: provider.model_name, reference: reference.model_reference, source_sha256: source.sha256, provider_snapshot_sha256: snapshot, run_id: source.run, requested_dpi: renderDpi ? Number(renderDpi) : null, duration_seconds: (Date.now() - started) / 1000, assessment }, null, 2)}\n`,
    "utf8",
  );
  writeFileSync(
    path.join(output, "canonical.json"),
    JSON.stringify(document),
    "utf8",
  );
  writeFileSync(
    path.join(output, "manifest.json"),
    JSON.stringify(manifest),
    "utf8",
  );
  const markdown = await api.raw("GET", `${base}/markdown`);
  await requireOk(markdown, "GET", "OCR Markdown");
  writeFileSync(path.join(output, "document.md"), await markdown.body());
  for (const number of new Set(reference.checks.map((check) => check.page))) {
    const raw = await api.raw("GET", `${base}/pages/${number}/raw`);
    await requireOk(raw, "GET", `raw OCR page ${number}`);
    writeFileSync(
      path.join(output, `raw-page-${number}.json`),
      await raw.body(),
    );
  }
  console.info(
    `Mẫu OCR: ${assessment.anchors.filter((check) => check.passed).length}/${assessment.anchors.length} đoạn; ${assessment.tables.filter((check) => check.passed).length}/${assessment.tables.length} bảng. Đây không phải CER/WER toàn bộ tài liệu.`,
  );
  expect(assessment.technical_pass).toBe(true);
  expect(
    assessment.anchors.filter((check) => !check.passed),
    "OCR differs from pre-labelled visual samples",
  ).toEqual([]);
  expect(
    assessment.tables.filter((check) => !check.passed),
    "Table structure differs from visual samples",
  ).toEqual([]);
});
