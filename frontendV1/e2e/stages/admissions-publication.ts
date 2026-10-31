import { expect } from "@playwright/test";
import {
  type BenchmarkDoc,
  benchmark,
  context,
  modelTimeout,
} from "./admissions-context";
import { verifyAdmissionsIndex } from "./admissions-policy";
import {
  decideCompilationRecovery,
  invalidReviewCanBeReplanned,
  type RunFacts,
  recoveryAllowed,
  replaceCompletedReview,
  reviewNeedsReplacement,
} from "./admissions-recovery";
import {
  type Api,
  type Checkpoint,
  collection,
  type Publication,
  processing,
  type Run,
  type Source,
  save,
  versionBase,
} from "./session";

type Progress = {
  status: string;
  total: number;
  completed?: number;
  running?: number;
  active_segments?: number[];
  concurrency?: number;
  elapsed_seconds?: number | null;
  queue_timeout_seconds?: number;
  planner_version?: string | null;
  segments?: { status: string; error_code?: string | null }[];
};

const NEW_RUN_MESSAGE: Record<string, string> = {
  stale_planner:
    "lượt cũ do planner khác lập, không resume được theo contract hiện tại",
  unresumable_parts: "lượt cũ còn phần uncertain/failed, không được gửi lại",
};

export async function compileAdmissionSource(api: Api, state: Checkpoint) {
  if (!state.admissions?.documents) {
    throw new Error("BLOCKED: thiếu bộ tài liệu tuyển sinh.");
  }
  const timeout = await modelTimeout(api, state);

  // Validate every source before spending tokens on the first document.
  for (const [key, docMeta] of Object.entries(benchmark.documents)) {
    const source = state.admissions.documents[key]?.source;
    if (!source || source.sha256 !== docMeta.sha256)
      throw new Error(`BLOCKED: thiếu/sai hash nguồn ${key}.`);
    const run = await api.get<Run>(processing(context(state), source));
    if (
      run.status !== "completed" ||
      !run.results_ready ||
      run.pages_done !== docMeta.pages ||
      run.pages_total !== docMeta.pages
    )
      throw new Error(`BLOCKED: OCR ${key} chưa đủ trang/kết quả.`);
    await pinAdmissionText(api, state, source);
  }

  for (const [key, docMeta] of Object.entries(benchmark.documents)) {
    const entry = state.admissions.documents[key];
    if (!entry?.source) {
      throw new Error(`BLOCKED: thiếu nguồn ${key}.`);
    }
    await compileOneAdmissionSource(
      api,
      state,
      key,
      docMeta,
      entry.source,
      timeout,
    );
  }

  // Đồng bộ lại publication của floor2026 cho state.admissions để tương thích ngược
  if (state.admissions.documents.floor2026?.publication) {
    state.admissions.publication =
      state.admissions.documents.floor2026.publication;
    state.admissions.compilationHistory =
      state.admissions.documents.floor2026.compilationHistory;
  }
}

async function pinAdmissionText(api: Api, state: Checkpoint, source: Source) {
  const suffix =
    source.textVersion === undefined ? "" : `?version=${source.textVersion}`;
  const text = await api.get<{
    run_id: string;
    version: number;
    canonical_sha256: string;
    units: unknown[];
  }>(`${processing(context(state), source)}/text-review${suffix}`);
  if (
    text.run_id !== source.run ||
    !Number.isSafeInteger(text.version) ||
    text.version < 0 ||
    !/^[a-f0-9]{64}$/.test(text.canonical_sha256) ||
    !text.units.length ||
    (source.textVersion !== undefined && text.version !== source.textVersion) ||
    (source.textSha256 && text.canonical_sha256 !== source.textSha256)
  )
    throw new Error("BLOCKED: bản văn bản OCR không khớp checkpoint.");
  source.textVersion = text.version;
  source.textSha256 = text.canonical_sha256;
  save(state);
}

async function compileOneAdmissionSource(
  api: Api,
  state: Checkpoint,
  docKey: string,
  docMeta: BenchmarkDoc,
  source: Source,
  timeout: number,
) {
  const base = collection(context(state));
  const entry = state.admissions?.documents?.[docKey];
  if (!entry) {
    throw new Error(`BLOCKED: thiếu thông tin lưu trữ cho ${docKey}.`);
  }
  const previous = entry.publication;
  let replaceWith: "raise_output" | "new_run" | undefined;
  let reason = "";
  let recoverOutput: number | undefined;

  if (previous) {
    const run = await api.get<Run>(`${base}/compilation-runs/${previous.run}`);
    let outputLimit: number | null | undefined;
    let facts: RunFacts = { ...run };
    if (
      run.status !== "queued" &&
      run.status !== "running" &&
      run.status !== "dispatched"
    ) {
      const progress = await api.get<Progress>(
        `${base}/compilation-runs/${previous.run}/progress`,
      );
      facts = {
        ...run,
        planner_version: progress.planner_version,
        parts: progress.segments,
      };
      if (
        run.status === "failed" &&
        run.error_code === "chat_output_truncated"
      ) {
        const provider = await api.get<{
          token_limits?: { max_output_tokens?: number | null } | null;
        }>(`/modelops/providers/${state.runtimeDefaults?.chat}`);
        outputLimit = provider.token_limits?.max_output_tokens;
      }
    }
    const decision = decideCompilationRecovery(
      facts,
      previous,
      state.runtimeDefaults?.chat,
      outputLimit,
    );
    if (decision.action === "raise_output") {
      replaceWith = "raise_output";
      recoverOutput = decision.output;
    } else if (decision.action === "new_run") {
      replaceWith = "new_run";
      reason = decision.reason;
    }
  }

  if (replaceWith && !recoveryAllowed(process.env.E2E_RECOVER_COMPILATION)) {
    throw new Error(
      `BLOCKED: [${docKey}] ${NEW_RUN_MESSAGE[reason] ?? reason}. ` +
        "Chạy lại chặng với --recover để tạo lượt mới từ nguồn OCR đã xong; " +
        "lượt cũ được giữ trong compilationHistory.",
    );
  }

  if (!previous || replaceWith) {
    let idempotencyKey = `${state.runId}-${docKey}-compile-v5`;
    const history = previous
      ? [...(entry.compilationHistory ?? []), previous]
      : entry.compilationHistory;
    if (previous) {
      idempotencyKey = `${state.runId}-${docKey}-compile-v5-r${history?.length}`;
      console.info(
        `[${docKey}] Tạo lượt biên soạn mới (${NEW_RUN_MESSAGE[reason] ?? reason}); ` +
          `giữ lượt ${previous.run} trong lịch sử.`,
      );
    }
    const body: Record<string, unknown> = {
      topic: `Biên soạn đầy đủ tài liệu: ${docMeta.title}`,
      ocr_run_ids: [source.run],
      text_versions: { [source.run]: source.textVersion },
      provider_id: state.runtimeDefaults?.chat,
      structured_output: true,
      auto_review: false,
    };
    if (recoverOutput !== undefined) {
      body.max_output_tokens = recoverOutput;
    }
    const created = await api.post<{ run: Run }>(
      `${base}/compilation-runs`,
      body,
      idempotencyKey,
    );
    // A failed POST must not advance history and generate another recovery key.
    entry.compilationHistory = history;
    entry.publication = {
      run: created.run.id,
      compilationRecoveryOf: previous?.run,
    };
    save(state);
  }

  const publication = entry.publication;
  if (!publication) {
    throw new Error(
      `[${docKey}] Lỗi logic: không tìm thấy publication sau khi tạo.`,
    );
  }
  const progress = await api.waitProgress<Progress>(
    `${base}/compilation-runs/${publication.run}/progress`,
    timeout,
  );
  expect(
    progress.status,
    `[${docKey}] Biên soạn không đạt; dừng chặng để rà soát artifact/log.`,
  ).toBe("completed");

  const draft = await api.get<{
    sections: unknown[];
    citations: Record<string, unknown>;
  }>(`${base}/compilation-runs/${publication.run}/draft`);
  expect(draft.sections.length).toBeGreaterThan(0);
  expect(Object.keys(draft.citations).length).toBeGreaterThan(0);
  expect(
    Object.keys(draft.citations).every((id) => id.startsWith(`${source.run}:`)),
  ).toBe(true);

  await reviewOneAdmissionDraft(
    api,
    state,
    docKey,
    publication,
    timeout,
    progress.total,
  );
}

async function reviewOneAdmissionDraft(
  api: Api,
  state: Checkpoint,
  docKey: string,
  publication: Publication,
  timeout: number,
  parts: number,
) {
  const base = `${collection(context(state))}/compilation-runs/${publication.run}/reviews`;
  if (publication.review) {
    const old = await api.get<{
      status: string;
      trace?: Record<string, unknown>;
    }>(`${base}/${publication.review}`);
    if (
      replaceCompletedReview(
        old,
        recoveryAllowed(process.env.E2E_RECOVER_COMPILATION),
        !!publication.version,
      )
    ) {
      publication.reviewHistory = [
        ...(publication.reviewHistory ?? []),
        publication.review,
      ];
      publication.reviewAttempts = (publication.reviewAttempts ?? 0) + 1;
      delete publication.review;
      save(state);
      console.info(
        `[${docKey}] Tạo review theo chính sách mới; giữ báo cáo cũ trong lịch sử.`,
      );
    }
  }

  if (!publication.review) {
    const reviewTimeout = timeout * Math.max(8, parts * 4);
    const body = {
      provider_id: state.runtimeDefaults?.chat,
      structured_output: true,
    };
    const attempts = publication.reviewAttempts ?? 0;
    const key =
      attempts === 0
        ? `${state.runId}-${docKey}-review-${publication.run}`
        : `${state.runId}-${docKey}-review-${publication.run}-r${attempts}`;
    let review: Run;
    try {
      review = await api.post<Run>(base, body, key, reviewTimeout);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      let replace = reviewNeedsReplacement(
        message,
        recoveryAllowed(process.env.E2E_RECOVER_COMPILATION),
      );
      if (
        !replace &&
        recoveryAllowed(process.env.E2E_RECOVER_COMPILATION) &&
        message.includes("code=compilation_review_invalid")
      ) {
        const latest = await api.get<
          {
            id: string;
            status: string;
            error_code?: string;
            trace?: Record<string, unknown>;
          }[]
        >(`${base}?limit=1`);
        if (latest[0]) {
          const progress = await api.get<{ segments: { status: string }[] }>(
            `${base}/${latest[0].id}/progress`,
          );
          replace = invalidReviewCanBeReplanned(latest[0], progress.segments);
        }
      }
      if (!replace) {
        throw error;
      }
      const stopped = await api.get<{ id: string; status: string }[]>(
        `${base}?limit=20`,
      );
      publication.reviewHistory = [
        ...(publication.reviewHistory ?? []),
        ...stopped
          .filter((row) => row.status !== "running")
          .map((row) => row.id)
          .filter((id) => !(publication.reviewHistory ?? []).includes(id)),
      ];
      publication.reviewAttempts = attempts + 1;
      save(state);
      review = await api.post<Run>(
        base,
        body,
        `${state.runId}-${docKey}-review-${publication.run}-r${attempts + 1}`,
        reviewTimeout,
      );
    }
    publication.review = review.id;
    save(state);
  }

  await api.waitProgress<Progress>(
    `${base}/${publication.review}/progress`,
    timeout,
  );
  const report = await api.get<{ review_id: string; findings: unknown[] }>(
    `${base}/${publication.review}/report`,
  );
  expect(report.review_id).toBe(publication.review);
  expect(
    report.findings,
    `[${docKey}] Review còn finding; không tự chấp nhận rủi ro để xuất bản.`,
  ).toHaveLength(0);
}

async function decide(
  api: Api,
  state: Checkpoint,
  docKey: string,
  publication: Publication,
  action: "approve" | "publish",
) {
  const base = versionBase(context(state), publication);
  const body: Record<string, unknown> = {
    action,
    reason: `E2E ${docKey} tuyển sinh`,
  };
  if (action === "approve") {
    const gate = await api.get<{
      review_id: string;
      report_sha256: string;
      findings: unknown[];
    }>(`${base}/review-gate`);
    expect(
      gate.findings,
      `[${docKey}] Finding chưa xử lý; giữ nguyên chốt xuất bản.`,
    ).toHaveLength(0);
    expect(gate.review_id, "Review gate phải là báo cáo đã kiểm tra.").toBe(
      publication.review,
    );
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
    `${state.runId}-${docKey}-${publication.version}-${action}`,
  );
}

export async function publishAdmissionDraft(api: Api, state: Checkpoint) {
  if (!state.admissions?.documents) {
    throw new Error("BLOCKED: chưa có tài liệu nào được biên soạn.");
  }
  const base = collection(context(state));

  // No document is published if another document is known to have no valid review.
  for (const key of Object.keys(benchmark.documents)) {
    const publication = state.admissions.documents[key]?.publication;
    if (!publication?.review)
      throw new Error(`BLOCKED: thiếu review của ${key}.`);
    const reviewBase = `${base}/compilation-runs/${publication.run}/reviews/${publication.review}`;
    const review = await api.get<Run & { compilation_run_id: string }>(
      reviewBase,
    );
    if (
      review.status !== "completed" ||
      review.compilation_run_id !== publication.run
    )
      throw new Error(`BLOCKED: review ${key} chưa hoàn tất/không khớp.`);
    const report = await api.get<{ review_id: string; findings: unknown[] }>(
      `${reviewBase}/report`,
    );
    expect(report.review_id).toBe(publication.review);
    expect(
      report.findings,
      `[${key}] Finding chưa xử lý; không xuất bản.`,
    ).toHaveLength(0);
  }

  // Xuất bản từng tài liệu
  for (const [key, docMeta] of Object.entries(benchmark.documents)) {
    const entry = state.admissions.documents[key];
    const publication = entry?.publication;
    if (!publication) {
      throw new Error(`BLOCKED: chưa biên soạn ${key}.`);
    }

    if (!publication.version) {
      const created = await api.post<{
        document: { id: string };
        version: { id: string };
      }>(
        `${base}/compiled-documents`,
        {
          document_key: `${key}-${state.runId}`,
          title: docMeta.title,
          compilation_run_id: publication.run,
        },
        `${state.runId}-${key}-document`,
      );
      publication.document = created.document.id;
      publication.version = created.version.id;
      save(state);
    }

    let version = await api.get<{ status: string }>(
      versionBase(context(state), publication),
    );
    if (version.status === "draft") {
      await decide(api, state, key, publication, "approve");
    }
    version = await api.get<{ status: string }>(
      versionBase(context(state), publication),
    );
    if (version.status === "approved") {
      await decide(api, state, key, publication, "publish");
    }
    expect(
      (
        await api.get<{ status: string }>(
          versionBase(context(state), publication),
        )
      ).status,
    ).toBe("published");
    console.info(
      `Đã xuất bản thành công tài liệu ${key}: version=${publication.version}`,
    );
  }

  // Đồng bộ lại publication floor2026 cho state.admissions
  if (state.admissions.documents.floor2026?.publication) {
    state.admissions.publication =
      state.admissions.documents.floor2026.publication;
  }

  // Tạo indexing-run chung cho toàn bộ collection chứa đủ cả 3 tài liệu
  await indexCombinedAdmissionsDrafts(api, state);
}

async function indexCombinedAdmissionsDrafts(api: Api, state: Checkpoint) {
  const base = collection(context(state));
  const admissions = state.admissions;
  if (!admissions) {
    throw new Error("BLOCKED: thiếu dữ liệu admissions.");
  }

  if (!admissions.combinedIndex) {
    const created = await api.post<{ run: Run }>(
      `${base}/indexing-runs`,
      {
        provider_id: state.runtimeDefaults?.embedding,
      },
      `${state.runId}-combined-admissions-index`,
    );
    admissions.combinedIndex = created.run.id;
    // Gán index vào publication của các doc để tương thích ngược
    if (admissions.publication) {
      admissions.publication.index = created.run.id;
    }
    for (const entry of Object.values(admissions.documents ?? {})) {
      if (entry.publication) {
        entry.publication.index = created.run.id;
      }
    }
    save(state);
  }

  const run = await api.wait<Run>(
    `${base}/indexing-runs/${admissions.combinedIndex}`,
    900_000,
  );
  expect(run.is_active).toBe(true);
  expect(run.chunks_total).toBeGreaterThan(0);
  expect(run.provider_id).toBe(state.runtimeDefaults?.embedding);
  await verifyAdmissionsIndex(api, state);

  const totalPages = Object.values(benchmark.documents).reduce(
    (sum, d) => sum + d.pages,
    0,
  );
  console.info(
    `Đã xuất bản và lập chỉ mục chung cho cả 3 PDF (${totalPages} trang, ${run.chunks_total} chunks).`,
  );
}
