import { execFileSync } from "node:child_process";
import { createHmac } from "node:crypto";
import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  type CompilationDraft,
  needsUnreadBlockUpgrade,
} from "./compilation-upgrade";
import { liveDefaults } from "./live-defaults";
import {
  type Action,
  type Api,
  authenticate,
  checkpoint,
  collection,
  directory,
  ensureSessionQuota,
  mockRoot,
  type Publication,
  processing,
  type Run,
  recoverMissingQuotaRun,
  requireOk,
  save,
  sha256,
  sourceBase,
  versionBase,
  workspace,
} from "./session";

const stage = process.env.E2E_STAGE;
const names = [
  "navigation",
  "upload",
  "extraction",
  "compilation",
  "publication",
  "chat",
  "permissions",
  "lifecycle",
];

async function expectRejectedKey(
  api: Api,
  secret: string,
  status: 401 | 403,
  code: "invalid_api_key" | "api_key_inactive",
) {
  const response = await api.raw(
    "GET",
    "/integrations/openai/v1/models",
    undefined,
    undefined,
    secret,
  );
  expect(response.status()).toBe(status);
  const problem = (await response.json()) as { error: { code: string } };
  expect(problem.error.code).toBe(code);
}
if (!stage || !names.includes(stage))
  throw new Error("Chặng E2E không hợp lệ.");
// API keys and auth headers must not enter browser traces/screenshots.
test.use({
  trace: "off",
  video: "off",
  screenshot: stage === "permissions" ? "off" : "only-on-failure",
});

async function decision(
  api: Api,
  publication: Publication,
  action: "approve" | "publish" | "withdraw",
) {
  const state = checkpoint();
  const base = versionBase(state, publication);
  const body: Record<string, unknown> = {
    action,
    reason: `Synthetic E2E ${action}`,
  };
  if (action === "approve") {
    const gate = await api.get<{
      review_id: string;
      report_sha256: string;
      findings: unknown[];
    }>(`${base}/review-gate`);
    expect(
      gate.findings,
      "Có finding; cần review thật, không tự xác nhận bỏ qua.",
    ).toHaveLength(0);
    body.review_ack = {
      review_id: gate.review_id,
      report_sha256: gate.report_sha256,
      confirmed_reviewed: true,
      resolutions: [],
    };
  }
  const preview = await api.post<{ id: string; preview_sha256: string }>(
    `${base}/decision-preview`,
    body,
  );
  await api.post(
    `${base}/decisions`,
    { preview_id: preview.id, preview_sha256: preview.preview_sha256 },
    `${state.runId}-${publication.version}-${action}`,
  );
}

async function lifecycle(
  api: Api,
  kind: string,
  resourceId: string,
  action: string,
) {
  const state = checkpoint();
  const base = `${workspace(state)}/lifecycle`;
  const preview = await api.post<Action>(`${base}/previews`, {
    kind,
    resource_id: resourceId,
    action,
    reason: `Synthetic E2E ${action}`,
  });
  const accepted = await api.post<Action>(
    `${base}/actions`,
    { preview_id: preview.id, preview_sha256: preview.preview_sha256 },
    `${state.runId}-${kind}-${resourceId}-${action}`,
  );
  return api.wait<Action>(`${base}/actions/${accepted.id}`);
}

test(`V1 từng chặng: ${stage}`, async ({ page }) => {
  test.setTimeout(900_000);
  const api = await authenticate(page);
  let state = checkpoint();
  if (state.mode === "live" && stage !== "navigation" && !state.runtimeDefaults)
    throw new Error(
      "BLOCKED: chạy navigation để gắn bốn model QNU đã kiểm tra vào workspace thử.",
    );

  if (stage === "navigation") {
    if (!state.workspace) {
      const result = await api.post<{ id: string }>("/workspaces", {
        code: `e2e-${state.runId}`,
        name: `E2E ${state.runId}`,
      });
      state.workspace = result.id;
      save(state);
    }
    const live = state.mode === "live" ? await liveDefaults(api, state) : null;
    await ensureSessionQuota(api, state, live?.monthlyTokenLimit);
    let providers = await api.get<
      { id: string; capabilities: string[]; is_active: boolean }[]
    >("/modelops/providers");
    if (state.mode === "workflow" && !state.provider) {
      const provider = await api.post<{ id: string }>("/modelops/providers", {
        name: `Synthetic ${state.runId}`,
        provider_type: "openai_compatible",
        base_url: mockRoot,
        model_name: "e2e-contract-only",
        capabilities: ["chat", "embedding", "rerank", "ocr"],
        timeout_seconds: 60,
        embedding_dimension: 1024,
        token_limits: {
          max_input_tokens: 32768,
          max_output_tokens: 8192,
          context_window_tokens: 65536,
          ocr_page_input: {
            max_image_width: 4096,
            max_image_height: 4096,
            input_tokens_upper_bound: 4096,
            prompt_sha256: sha256(
              Buffer.from(
                "</s><s><predict_bbox><predict_classes><output_markdown><predict_text_in_pic>",
              ),
            ),
          },
        },
      });
      state.provider = provider.id;
      save(state);
      providers = await api.get("/modelops/providers");
    }
    if (state.mode === "workflow" && state.provider) {
      const keys = await api.get<{ id: string }[]>(
        `/modelops/providers/${state.provider}/keys`,
      );
      if (keys.length === 0) {
        await api.post(`/modelops/providers/${state.provider}/keys`, {
          name: "Synthetic upstream",
          secret: "e2e-contract-only-token",
        });
      }
    }
    const defaults: Record<string, string> = {};
    for (const capability of ["chat", "embedding", "rerank", "ocr"] as const) {
      const preferred = live?.defaults[capability];
      const match = providers.find(
        (p) =>
          p.is_active &&
          p.capabilities.includes(capability) &&
          (!preferred || p.id === preferred),
      );
      if (!match)
        throw new Error(
          `BLOCKED: cấu hình provider ${capability} trong ModelOps của phiên E2E rồi chạy lại navigation.`,
        );
      defaults[capability] = match.id;
    }
    await api.json("PUT", `${workspace(state)}/allowed-providers`, {
      provider_ids: [...new Set(Object.values(defaults))],
      defaults,
    });
    if (live) {
      const granted = await api.get<{
        providers: {
          provider_id: string;
          is_active: boolean;
          default_capabilities: string[];
        }[];
      }>(`${workspace(state)}/allowed-providers`);
      expect(granted.providers.map((item) => item.provider_id).sort()).toEqual(
        [...new Set(Object.values(live.defaults))].sort(),
      );
      const observedDefaults = Object.fromEntries(
        granted.providers.flatMap((item) => {
          expect(item.is_active).toBe(true);
          return item.default_capabilities.map((capability) => [
            capability,
            item.provider_id,
          ]);
        }),
      );
      expect(observedDefaults).toEqual(live.defaults);
      state.runtimeDefaults = live.defaults;
      save(state);
    }
    await page.goto(`/workspaces/${state.workspace}/knowledge`);
    await expect(
      page.getByRole("heading", { name: /Kho tri thức/ }).first(),
    ).toBeVisible();
    for (const label of ["Kho tri thức", "Trợ lý AI", "Hội thoại"]) {
      await expect(
        page.getByRole("link", { name: label, exact: true }),
      ).toBeVisible();
    }
  }

  if (stage === "upload") {
    if (!state.collection) {
      const result = await api.post<{ id: string }>(
        `${workspace(state)}/collections`,
        {
          name: `Synthetic ${state.runId}`,
          description: "Dữ liệu giả lập riêng cho kiểm tra quy trình.",
        },
      );
      state.collection = result.id;
      save(state);
    }
    if (!state.folder) {
      const result = await api.post<{ id: string }>(
        `${collection(state)}/folders`,
        { name: "Tài liệu thử" },
      );
      state.folder = result.id;
      save(state);
    }
    for (const file of [
      "de_an_tuyen_sinh_2026.pdf",
      "thong_bao_scan_2024.pdf",
      "phu_luc_bang_bieu.docx",
    ]) {
      if (!state.sources.some((s) => s.file === file)) {
        state.sources.push(
          await api.upload(
            state,
            file,
            `${state.runId}-upload-${state.sources.length}`,
          ),
        );
        save(state);
      }
    }
    expect(state.sources).toHaveLength(3);
    // A duplicate must be rejected rather than silently replacing an existing revision.
    const bytes = readFileSync(
      path.join(directory, "fixtures", state.sources[0].file),
    );
    const duplicate = await page.request.post(
      `${apiRootForUpload()}${collection(state)}/sources`,
      {
        headers: { Authorization: `Bearer ${api.token}` },
        multipart: {
          file: {
            name: state.sources[0].file,
            mimeType: "application/pdf",
            buffer: bytes,
          },
        },
      },
    );
    expect(duplicate.status()).toBe(409);
    await page.goto(
      `/workspaces/${state.workspace}/knowledge/${state.collection}`,
    );
    await expect(
      page.getByRole("button", { name: /Tải tài liệu/ }).first(),
    ).toBeVisible();
    await expect(
      page.getByText("Tài liệu thử", { exact: true }).first(),
    ).toBeVisible();
  }

  if (stage === "extraction") {
    await ensureSessionQuota(api, state);
    for (const source of state.sources) {
      await recoverMissingQuotaRun(api, state, source);
      const run = await api.wait<Run>(processing(state, source));
      expect(run.pages_total).toBeGreaterThan(0);
      expect(run.pages_done).toBe(run.pages_total);
      expect(run.results_ready).toBe(true);
      if (state.runtimeDefaults && source.file === "thong_bao_scan_2024.pdf")
        expect(run.provider_id).toBe(state.runtimeDefaults.ocr);
      const original = await api.raw(
        "GET",
        `${sourceBase(state, source)}/revisions/${source.revision}/content`,
      );
      await requireOk(original, "GET", "original");
      expect(sha256(await original.body())).toBe(source.sha256);
      const base = `${processing(state, source)}/text-review`;
      type TextReview = {
        version: number;
        canonical_sha256: string;
        units: { evidence_id: string; text: string }[];
      };
      const review = await api.get<TextReview>(base);
      expect(review.units.length).toBeGreaterThan(0);
      if (source.textVersion === undefined) {
        const unit = review.units.find((u) => u.text.trim().length > 2);
        if (!unit) throw new Error("Không có unit văn bản để thử lưu sửa.");
        const changed = await api.post<TextReview>(
          base,
          {
            expected_version: review.version,
            expected_sha256: review.canonical_sha256,
            changes: [
              {
                evidence_id: unit.evidence_id,
                before: unit.text,
                after: `${unit.text} (đã rà soát)`,
              },
            ],
          },
          `${state.runId}-${source.id}-text-edit`,
        );
        expect(changed.version).toBeGreaterThan(review.version);
        expect(changed.canonical_sha256).not.toBe(review.canonical_sha256);
        source.textVersion = changed.version;
        save(state);
      }
      for (const suffix of ["/document", "/markdown"]) {
        const result = await api.raw("GET", base + suffix);
        await requireOk(result, "GET", suffix);
        expect((await result.body()).length).toBeGreaterThan(0);
      }
      const unchanged = await api.raw(
        "GET",
        `${sourceBase(state, source)}/revisions/${source.revision}/content`,
      );
      await requireOk(unchanged, "GET", "original after edit");
      expect(sha256(await unchanged.body())).toBe(source.sha256);
    }
  }

  if (stage === "compilation") {
    state.publications ||= [];
    // Independent publications let lifecycle verify that deleting one source preserves another.
    for (const [index, source] of state.sources.slice(0, 2).entries()) {
      let publication = state.publications[index];
      const startCompilation = (suffix = "") =>
        api.post<{ run: Run }>(
          `${collection(state)}/compilation-runs`,
          {
            topic: `Tóm tắt đầy đủ dữ liệu nguồn ${index + 1}`,
            ocr_run_ids: [source.run],
            auto_review: false,
            ...(state.runtimeDefaults
              ? { provider_id: state.runtimeDefaults.chat }
              : {}),
            text_versions: { [source.run]: source.textVersion },
          },
          `${state.runId}-compile-${index}${suffix}`,
        );
      if (!publication) {
        const created = await startCompilation();
        publication = { run: created.run.id };
        state.publications.push(publication);
        save(state);
      }
      await api.wait(
        `${collection(state)}/compilation-runs/${publication.run}`,
      );
      let draft = await api.get<CompilationDraft>(
        `${collection(state)}/compilation-runs/${publication.run}/draft`,
      );
      if (
        await needsUnreadBlockUpgrade(
          api,
          collection(state),
          publication,
          draft,
          state.compilationHistory,
        )
      ) {
        // Explicit rerun after the server fix: append; never rewrite an old draft/review.
        const created = await startCompilation("-source-limits-v2");
        (state.compilationHistory ||= []).push({ ...publication });
        publication = { run: created.run.id, document: publication.document };
        state.publications[index] = publication;
        save(state);
        await api.wait(`${collection(state)}/compilation-runs/${publication.run}`);
        draft = await api.get<CompilationDraft>(
          `${collection(state)}/compilation-runs/${publication.run}/draft`,
        );
        expect(
          draft.validation?.unread_source_blocks,
          "API/worker chưa nạp bản sửa khối chưa đọc. Dừng cửa sổ serve rồi chạy lại serve; không cleanup/init.",
        ).toBe("retained");
      }
      const paragraphs = draft.sections.flatMap(
        (section) => section.paragraphs,
      );
      expect(paragraphs.length).toBeGreaterThan(0);
      for (const paragraph of paragraphs) {
        expect(paragraph.text.length).toBeGreaterThan(0);
        expect(paragraph.citations.length).toBeGreaterThan(0);
        expect(
          paragraph.citations.every((c) => c.startsWith(`${source.run}:`)),
        ).toBe(true);
      }
      {
        const reviewProvider = state.runtimeDefaults
          ? await api.get<{
              timeout_seconds: number;
              token_limits?: { max_output_tokens?: number | null } | null;
            }>(
              `/modelops/providers/${state.runtimeDefaults.chat}`,
            )
          : undefined;
        const reviewBase = `${collection(state)}/compilation-runs/${publication.run}/reviews`;
        type ReviewRun = Run & { trace?: { max_output_tokens?: number } };
        const previous = publication.review
          ? await api.get<ReviewRun>(`${reviewBase}/${publication.review}`)
          : (await api.get<ReviewRun[]>(`${reviewBase}?limit=1`))[0];
        const previousLimit = previous?.trace?.max_output_tokens;
        const modelLimit = reviewProvider?.token_limits?.max_output_tokens;
        // A new, explicit stage run may recover truncation only after budget increases.
        // Uncertain requests and same-budget failures keep their original review.
        const recoverTruncated =
          previous?.status === "failed" &&
          previous.error_code === "chat_output_truncated" &&
          previous.provider_id === state.runtimeDefaults?.chat &&
          typeof previousLimit === "number" &&
          typeof modelLimit === "number" &&
          previousLimit < modelLimit;
        if (previous && !recoverTruncated) {
          publication.review = previous.id;
        } else {
          if (reviewProvider)
            console.info(
              `Đang review nguồn ${index + 1}; chờ tối đa ${reviewProvider.timeout_seconds}s, trả kết quả ngay khi xử lý xong.`,
            );
          const review = await api.post<Run>(
            reviewBase,
            state.runtimeDefaults
              ? {
                  provider_id: state.runtimeDefaults.chat,
                  structured_output: true,
                }
              : {},
            `${state.runId}-review-${index}-${publication.run}${recoverTruncated ? `-budget-${modelLimit}` : ""}`,
            reviewProvider
              ? (reviewProvider.timeout_seconds + 30) * 1000
              : undefined,
          );
          publication.review = review.id;
        }
        save(state);
      }
      const completedReview = await api.wait<
        Run & { created_at: string; finished_at: string | null }
      >(
        `${collection(state)}/compilation-runs/${publication.run}/reviews/${publication.review}`,
      );
      if (completedReview.finished_at) {
        const elapsedSeconds =
          (Date.parse(completedReview.finished_at) -
            Date.parse(completedReview.created_at)) /
          1000;
        if (Number.isFinite(elapsedSeconds) && elapsedSeconds >= 0)
          console.info(
            `Review nguồn ${index + 1} đã hoàn tất; thời gian xử lý ${elapsedSeconds.toFixed(1)} giây.`,
          );
      }
      const report = await api.raw(
        "GET",
        `${collection(state)}/compilation-runs/${publication.run}/reviews/${publication.review}/report`,
      );
      await requireOk(report, "GET", "compiler review report");
      expect((await report.body()).length).toBeGreaterThan(0);
    }
  }

  if (stage === "publication") {
    if (state.publications?.length !== 2)
      throw new Error("Thiếu hai bản biên soạn độc lập.");
    for (const [index, publication] of state.publications.entries()) {
      if (!publication.version) {
        const documentBase = `${collection(state)}/compiled-documents`;
        const result = await api.post<{
          document: { id: string };
          version: { id: string };
        }>(
          publication.document
            ? `${documentBase}/${publication.document}/versions`
            : documentBase,
          publication.document
            ? { compilation_run_id: publication.run }
            : {
                document_key: `e2e-${state.runId}-${index}`,
                title: `Bản thử ${index + 1}`,
                compilation_run_id: publication.run,
              },
          publication.document
            ? `${state.runId}-publication-${index}-${publication.run}`
            : `${state.runId}-publication-${index}`,
        );
        publication.document = result.document.id;
        publication.version = result.version.id;
        save(state);
      }
      const version = await api.get<{ status: string }>(
        versionBase(state, publication),
      );
      if (version.status === "draft")
        await decision(api, publication, "approve");
      if (version.status !== "published")
        await decision(api, publication, "publish");
      expect(
        (await api.get<{ status: string }>(versionBase(state, publication)))
          .status,
      ).toBe("published");
    }
    const created = await api.post<{ run: Run }>(
      `${collection(state)}/indexing-runs`,
      state.runtimeDefaults
        ? { provider_id: state.runtimeDefaults.embedding }
        : {},
      `${state.runId}-index`,
    );
    for (const publication of state.publications)
      publication.index = created.run.id;
    save(state);
    const indexed = await api.wait<Run>(
      `${collection(state)}/indexing-runs/${created.run.id}`,
    );
    expect(indexed.is_active).toBe(true);
    expect(indexed.chunks_total).toBeGreaterThan(0);
    if (state.runtimeDefaults)
      expect(indexed.provider_id).toBe(state.runtimeDefaults.embedding);
  }

  if (stage === "chat") {
    if (!state.assistant) {
      const result = await api.post<{ id: string }>(
        `${workspace(state)}/assistants`,
        {
          name: `E2E ${state.runId}`,
          collection_id: state.collection,
          ...(state.runtimeDefaults
            ? {
                chat_provider_id: state.runtimeDefaults.chat,
                rag_policy: {
                  retrieval_mode: "hybrid_rerank",
                  rerank_provider_id: state.runtimeDefaults.rerank,
                },
              }
            : {}),
        },
      );
      state.assistant = result.id;
      save(state);
    }
    if (!state.conversation) {
      const result = await api.post<{ id: string }>(
        `${workspace(state)}/conversations`,
        { assistant_id: state.assistant },
      );
      state.conversation = result.id;
      save(state);
    }
    type Turn = {
      id: string;
      status: string;
      result: {
        status: string;
        answer: string;
        sources: {
          version_id: string;
          evidence_id: string;
          citations: Record<string, unknown>;
        }[];
        statements: unknown[];
        trace: {
          provider_id: string;
          retrieval: {
            mode: string;
            rerank_provider?: { provider_id: string };
          };
        };
      };
    };
    const turn = await api.post<Turn>(
      `${workspace(state)}/conversations/${state.conversation}/turns`,
      {
        question: "Tổng chỉ tiêu tuyển sinh năm 2026 là bao nhiêu?",
        expected_turn_no: 0,
      },
      `${state.runId}-turn-0`,
    );
    const result =
      turn.status === "completed"
        ? turn
        : await api.wait<Turn>(
            `${workspace(state)}/conversations/${state.conversation}/turns/${turn.id}`,
          );
    expect(result.result.status).toBe("answered");
    if (state.runtimeDefaults) {
      expect(result.result.trace.provider_id).toBe(state.runtimeDefaults.chat);
      expect(result.result.trace.retrieval.mode).toBe("hybrid_rerank");
      expect(result.result.trace.retrieval.rerank_provider?.provider_id).toBe(
        state.runtimeDefaults.rerank,
      );
    }
    expect(result.result.answer).toMatch(/5[., ]?500/);
    expect(result.result.statements.length).toBeGreaterThan(0);
    expect(result.result.sources.length).toBeGreaterThan(0);
    expect(
      result.result.sources.every(
        (s) =>
          s.version_id === state.publications?.[0].version &&
          Object.keys(s.citations).length > 0,
      ),
    ).toBe(true);
    await page.goto(
      `/workspaces/${state.workspace}/conversations/${state.conversation}`,
    );
    await expect(page.getByText(/5[., ]?500/).first()).toBeVisible();
  }

  if (stage === "permissions") {
    // Signed identity belongs only to this isolated test server; it has no workspace membership.
    const env = JSON.parse(
      readFileSync(path.join(directory, "private-env.json"), "utf8"),
    ) as Record<string, string>;
    const now = Math.floor(Date.now() / 1000);
    const encode = (value: unknown) =>
      Buffer.from(JSON.stringify(value)).toString("base64url");
    const unsigned = `${encode({ alg: "HS256", typ: "JWT" })}.${encode({ sub: "isolated-outsider", actor_id: `e2e-outside-${state.runId}`, roles: [], permissions: [], aud: "qnu-dev-access", iat: now, exp: now + 300 })}`;
    const outsider = `${unsigned}.${createHmac("sha256", env.SECRET_KEY).update(unsigned).digest("base64url")}`;
    const forbidden = await api.raw(
      "GET",
      `${collection(state)}/sources`,
      undefined,
      undefined,
      outsider,
    );
    expect(forbidden.status()).toBe(404);
    const prefix = `${workspace(state)}/integrations/keys`;
    const created = await api.post<{ id: string; secret_key: string }>(prefix, {
      app_name: `Test app ${state.runId}`,
      name: "Ephemeral key",
      allowed_assistant_ids: [state.assistant],
      allow_all_assistants: false,
    });
    const models = await api.raw(
      "GET",
      "/integrations/openai/v1/models",
      undefined,
      undefined,
      created.secret_key,
    );
    await requireOk(models, "GET", "models");
    expect(
      ((await models.json()) as { data: { id: string }[] }).data.map(
        (m) => m.id,
      ),
    ).toEqual([state.assistant]);
    const completion = await api.raw(
      "POST",
      "/integrations/openai/v1/chat/completions",
      {
        model: state.assistant,
        messages: [
          {
            role: "user",
            content: "Tổng chỉ tiêu tuyển sinh năm 2026 là bao nhiêu?",
          },
        ],
        stream: false,
      },
      undefined,
      created.secret_key,
    );
    await requireOk(completion, "POST", "application chat completion");
    const gatewayAnswer = (await completion.json()) as {
      choices: { message: { content: string } }[];
      qnu_extensions: { sources: unknown[] };
    };
    expect(gatewayAnswer.choices[0].message.content).toMatch(/5[., ]?500/);
    expect(gatewayAnswer.qnu_extensions.sources.length).toBeGreaterThan(0);
    const listed = await api.get<unknown>(prefix);
    expect(JSON.stringify(listed).includes(created.secret_key)).toBe(false);
    const rotated = await api.post<{ id: string; secret_key: string }>(
      `${prefix}/${created.id}/rotate`,
      {},
    );
    // Existing but revoked keys are denied by check_access with 403/api_key_inactive.
    await expectRejectedKey(api, created.secret_key, 403, "api_key_inactive");
    const newModels = await api.raw(
      "GET",
      "/integrations/openai/v1/models",
      undefined,
      undefined,
      rotated.secret_key,
    );
    await requireOk(newModels, "GET", "models after key rotation");
    expect(
      ((await newModels.json()) as { data: { id: string }[] }).data.map(
        (model) => model.id,
      ),
    ).toEqual([state.assistant]);
    await api.json("DELETE", `${prefix}/${rotated.id}`, {
      reason: "Synthetic E2E revoke",
    });
    await expectRejectedKey(api, rotated.secret_key, 403, "api_key_inactive");
    // Unknown credentials still use the distinct authentication error contract.
    await expectRejectedKey(
      api,
      `qnu_live_e2e_unknown_${state.runId}`,
      401,
      "invalid_api_key",
    );
  }

  if (stage === "lifecycle") {
    const target = state.sources[0];
    const other = state.sources[1];
    if (!state.publications?.[0] || !state.assistant)
      throw new Error("Chưa có dữ liệu phát hành/trợ lý.");
    if (!state.deletion) {
      if (!state.guardVerified) {
        const guard = await api.raw(
          "POST",
          `${workspace(state)}/lifecycle/previews`,
          {
            kind: "source",
            resource_id: target.id,
            action: "delete",
            reason: "Synthetic publication guard",
          },
        );
        expect(guard.status()).toBe(409);
        expect(((await guard.json()) as { code: string }).code).toBe(
          "source_publication_in_use",
        );
        state.guardVerified = true;
        save(state);
      }
      if (!state.paused) {
        await lifecycle(api, "assistant", state.assistant, "pause");
        state.paused = true;
        save(state);
      }
      if (!state.withdrawn) {
        await decision(api, state.publications[0], "withdraw");
        state.withdrawn = true;
        save(state);
      }
      probe("capture");
      const preview = await api.post<Action>(
        `${workspace(state)}/lifecycle/previews`,
        {
          kind: "source",
          resource_id: target.id,
          action: "delete",
          reason: "Synthetic permanent purge",
        },
      );
      state.deletion = preview.id;
      save(state);
    }
    const pending = await api.get<Action>(
      `${workspace(state)}/lifecycle/actions/${state.deletion}`,
    );
    if (pending.status === "preview") {
      await api.post(
        `${workspace(state)}/lifecycle/actions`,
        { preview_id: pending.id, preview_sha256: pending.preview_sha256 },
        `${state.runId}-purge`,
      );
    }
    const deleted = await api.wait<Action>(
      `${workspace(state)}/lifecycle/actions/${state.deletion}`,
    );
    expect(deleted.result?.permanent).toBe(true);
    expect(deleted.result?.originals_retained).toBe(false);
    expect(deleted.result?.restore_available).toBe(false);
    expect((await api.raw("GET", sourceBase(state, target))).status()).toBe(
      404,
    );
    expect(
      (
        await api.raw(
          "GET",
          `${sourceBase(state, target)}/revisions/${target.revision}/content`,
        )
      ).status(),
    ).toBe(404);
    probe("verify");
    expect((await api.get<{ id: string }>(sourceBase(state, other))).id).toBe(
      other.id,
    );
    expect(
      (
        await api.get<{ status: string }>(
          versionBase(state, state.publications[1]),
        )
      ).status,
    ).toBe("published");
    const preserved = await api.raw(
      "GET",
      `${sourceBase(state, other)}/revisions/${other.revision}/content`,
    );
    await requireOk(preserved, "GET", "unrelated original after purge");
    expect(sha256(await preserved.body())).toBe(other.sha256);
    const answer = await api.post<{
      status: string;
      answer: string;
      sources: { version_id: string }[];
    }>(`${collection(state)}/answers`, {
      question: "Điểm chuẩn ngành Công nghệ thông tin năm 2024 là bao nhiêu?",
      document_ids: [state.publications[1].document],
      ...(state.runtimeDefaults
        ? {
            provider_id: state.runtimeDefaults.chat,
            retrieval_mode: "hybrid_rerank",
            rerank_provider_id: state.runtimeDefaults.rerank,
          }
        : {}),
    });
    expect(answer.status).toBe("answered");
    expect(answer.answer).toMatch(/24[.,]5/);
    expect(answer.sources.length).toBeGreaterThan(0);
    expect(
      answer.sources.every(
        (source) => source.version_id === state.publications?.[1].version,
      ),
    ).toBe(true);
    if (!state.replacement) {
      const replacement = await api.upload(
        state,
        target.file,
        `${state.runId}-reupload`,
      );
      expect(replacement.id).not.toBe(target.id);
      state.replacement = replacement.id;
      save(state);
    }
  }
  state = checkpoint();
  expect(state.runId).toMatch(/^[a-f0-9]{12}$/);
});

function apiRootForUpload() {
  const manifest = JSON.parse(
    readFileSync(path.join(directory, "manifest.json"), "utf8"),
  ) as { ports: { api: number } };
  return `http://127.0.0.1:${manifest.ports.api}/platform/v1alpha1`;
}
function probe(mode: "capture" | "verify") {
  const root = path.resolve(directory, "../../..");
  execFileSync(
    path.join(root, "backendV1/.venv/Scripts/python.exe"),
    [
      path.join(root, "scripts/e2e_data_probe.py"),
      "--session",
      path.basename(directory),
      mode,
    ],
    { cwd: root, stdio: "pipe" },
  );
}
