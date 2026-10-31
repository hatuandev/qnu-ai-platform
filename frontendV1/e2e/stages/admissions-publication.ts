import { expect } from "@playwright/test";
import { benchmark, context, modelTimeout } from "./admissions-context";
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
  type Run,
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
  const source = state.admissions?.source;
  if (!source || !state.admissions)
    throw new Error("BLOCKED: thiếu nguồn điểm sàn.");
  const base = collection(context(state));
  const timeout = await modelTimeout(api, state);
  const previous = state.admissions.publication;
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
      `BLOCKED: ${NEW_RUN_MESSAGE[reason] ?? reason}. ` +
        "Chạy lại chặng với --recover để tạo lượt mới từ nguồn OCR đã xong; " +
        "lượt cũ được giữ trong compilationHistory.",
    );
  }
  if (!previous || replaceWith) {
    let idempotencyKey = `${state.runId}-floor-compile-v5`;
    if (previous) {
      idempotencyKey =
        replaceWith === "raise_output"
          ? `${state.runId}-floor-recover-output-v5-${previous.run}`
          : `${state.runId}-floor-replan-v5-${previous.run}`;
    }
    const created = await api.post<{ run: Run }>(
      `${base}/compilation-runs`,
      {
        topic:
          "Biên soạn đầy đủ ngưỡng đầu vào đại học chính quy năm 2026: giữ mọi ngành/chương trình, mã xét tuyển, bốn cột phương thức, tổ hợp, dấu gạch và tất cả chú ý/ngoại lệ. Không đổi điểm sàn thành điểm trúng tuyển.",
        ocr_run_ids: [source.run],
        auto_review: false,
        provider_id: state.runtimeDefaults?.chat,
        structured_output: true,
        ...(recoverOutput !== undefined
          ? { max_output_tokens: recoverOutput }
          : {}),
      },
      idempotencyKey,
    );
    if (previous) {
      state.admissions.compilationHistory ??= [];
      if (
        !state.admissions.compilationHistory.some(
          (item) => item.run === previous.run,
        )
      )
        state.admissions.compilationHistory.push({ ...previous });
      console.info(
        replaceWith === "raise_output"
          ? `Tạo lượt phục hồi compiler với JSON Schema và output ${recoverOutput} token; giữ lượt lỗi trong lịch sử.`
          : `Tạo lượt biên soạn mới (${NEW_RUN_MESSAGE[reason] ?? reason}); giữ lượt ${previous.run} trong lịch sử.`,
      );
    }
    state.admissions.publication = {
      run: created.run.id,
      // Only a truncated run replaced with a larger ceiling is a "recovery"; a
      // replanned run must not consume the single allowed output recovery.
      ...(previous && recoverOutput !== undefined
        ? { compilationRecoveryOf: previous.run }
        : {}),
    };
    save(state);
  }
  const publication = state.admissions.publication;
  if (!publication) throw new Error("BLOCKED: chưa tạo lượt biên soạn.");
  const progressSuffix = `${base}/compilation-runs/${publication.run}/progress`;
  const progress = await api.waitProgress<Progress>(progressSuffix, timeout);
  const draft = await api.get<{
    sections: unknown[];
    citations: Record<string, unknown>;
  }>(`${base}/compilation-runs/${publication.run}/draft`);
  expect(draft.sections.length).toBeGreaterThan(0);
  expect(
    Object.keys(draft.citations).every((id) => id.startsWith(`${source.run}:`)),
  ).toBe(true);
  await reviewAdmissionDraft(api, state, publication, timeout, progress.total);
}

async function reviewAdmissionDraft(
  api: Api,
  state: Checkpoint,
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
        "Tạo review theo chính sách mới; giữ báo cáo cũ trong lịch sử.",
      );
    }
  }
  if (!publication.review) {
    // The review endpoint executes its parts synchronously, so this request must
    // survive one model call per part; progress below verifies the observed total.
    const reviewTimeout = timeout * Math.max(8, parts * 4);
    const body = {
      provider_id: state.runtimeDefaults?.chat,
      structured_output: true,
    };
    const attempts = publication.reviewAttempts ?? 0;
    const key =
      attempts === 0
        ? `${state.runId}-floor-review-${publication.run}`
        : `${state.runId}-floor-review-${publication.run}-r${attempts}`;
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
      // The stored review was planned for another model configuration; keep it in
      // history and start exactly one new review under a new key.
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
        `${state.runId}-floor-review-${publication.run}-r${attempts + 1}`,
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
  const report = await api.get<{ findings: unknown[] }>(
    `${base}/${publication.review}/report`,
  );
  expect(
    report.findings,
    "Review còn finding; không tự chấp nhận rủi ro để xuất bản.",
  ).toHaveLength(0);
}

async function decide(
  api: Api,
  state: Checkpoint,
  publication: Publication,
  action: "approve" | "publish",
) {
  const base = versionBase(context(state), publication);
  const body: Record<string, unknown> = {
    action,
    reason: "E2E TB điểm sàn 2026",
  };
  if (action === "approve") {
    const gate = await api.get<{
      review_id: string;
      report_sha256: string;
      findings: unknown[];
    }>(`${base}/review-gate`);
    expect(
      gate.findings,
      "Finding chưa xử lý; giữ nguyên chốt xuất bản.",
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
    `${state.runId}-floor-${publication.version}-${action}`,
  );
}

export async function publishAdmissionDraft(api: Api, state: Checkpoint) {
  const publication = state.admissions?.publication;
  if (!publication) throw new Error("BLOCKED: chưa biên soạn điểm sàn.");
  const base = collection(context(state));
  if (!publication.version) {
    const created = await api.post<{
      document: { id: string };
      version: { id: string };
    }>(
      base + "/compiled-documents",
      {
        document_key: `floor-${state.runId}`,
        title: "Ngưỡng đầu vào QNU 2026",
        compilation_run_id: publication.run,
      },
      `${state.runId}-floor-document`,
    );
    publication.document = created.document.id;
    publication.version = created.version.id;
    save(state);
  }
  let version = await api.get<{ status: string }>(
    versionBase(context(state), publication),
  );
  if (version.status === "draft")
    await decide(api, state, publication, "approve");
  version = await api.get<{ status: string }>(
    versionBase(context(state), publication),
  );
  if (version.status === "approved")
    await decide(api, state, publication, "publish");
  expect(
    (
      await api.get<{ status: string }>(
        versionBase(context(state), publication),
      )
    ).status,
  ).toBe("published");
  await indexAdmissionDraft(api, state, publication);
}

async function indexAdmissionDraft(
  api: Api,
  state: Checkpoint,
  publication: Publication,
) {
  const base = collection(context(state));
  if (!publication.index) {
    const created = await api.post<{ run: Run }>(
      `${base}/indexing-runs`,
      {
        provider_id: state.runtimeDefaults?.embedding,
      },
      `${state.runId}-floor-index`,
    );
    publication.index = created.run.id;
    save(state);
  }
  const run = await api.wait<Run>(
    `${base}/indexing-runs/${publication.index}`,
    900_000,
  );
  expect(run.is_active).toBe(true);
  expect(run.chunks_total).toBeGreaterThan(0);
  expect(run.provider_id).toBe(state.runtimeDefaults?.embedding);
  console.info(
    `Đã xuất bản và lập chỉ mục PDF ${benchmark.source.pages} trang.`,
  );
}
