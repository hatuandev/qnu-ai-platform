import { ApiProblemError } from "@/app/api/v1";
import type {
  DetectionResponse,
  DetectRequestInput,
  ReviewDocument,
} from "./ocr-types";

// Bound each request by structure and text size; server ModelOps still enforces tokens.
const GROUP_UNITS = 20;
const GROUP_CHARACTERS = 8000;
const SPLITTABLE_TOKEN_ERRORS = new Set([
  "chat_output_truncated",
  "model_input_limit_exceeded",
  "model_context_limit_exceeded",
]);

export type SpellingBatch = {
  page: number;
  evidenceIds: string[];
  key: string;
  status:
    | "pending"
    | "running"
    | "completed"
    | "failed"
    | "uncertain"
    | "not_run";
  check?: DetectionResponse;
  errorCode?: string;
  tokenDetail?: string;
};
export type DocumentSpellingReport = {
  version: number;
  sha256: string;
  batches: SpellingBatch[];
  splitAttempts?: SpellingBatch[];
  finished: boolean;
};
export type DetectCall = (request: {
  body: DetectRequestInput;
  idempotencyKey: string;
}) => Promise<DetectionResponse>;

export function selectableSpellingUnits(doc: ReviewDocument) {
  return doc.units.filter(
    (u) => u.kind !== "image" && u.kind !== "figure" && u.text.trim(),
  );
}

export function planSpellingBatches(
  doc: ReviewDocument,
  key: string,
): SpellingBatch[] {
  const batches: SpellingBatch[] = [];
  let chars = 0;
  for (const unit of [...selectableSpellingUnits(doc)].sort(
    (a, b) => a.page - b.page,
  )) {
    let last = batches.at(-1);
    if (
      !last ||
      last.page !== unit.page ||
      last.evidenceIds.length >= GROUP_UNITS ||
      chars + unit.text.length > GROUP_CHARACTERS
    ) {
      last = {
        page: unit.page,
        evidenceIds: [],
        key: `${key}:batch:${batches.length + 1}`,
        status: "pending",
      };
      batches.push(last);
      chars = 0;
    }
    // A long unit stays intact; never silently drop or truncate source evidence.
    last.evidenceIds.push(unit.evidence_id);
    chars += unit.text.length;
  }
  return batches;
}

export async function checkWholeDocument(options: {
  doc: ReviewDocument;
  key: string;
  providerId: string | null;
  sourceVersion: number | null;
  detect: DetectCall;
  shouldStop: () => boolean;
  onUpdate: (report: DocumentSpellingReport) => void;
  concurrency?: 1 | 2;
}) {
  const { doc, detect, shouldStop, onUpdate } = options;
  const report: DocumentSpellingReport = {
    version: doc.version,
    sha256: doc.canonical_sha256,
    batches: planSpellingBatches(doc, options.key),
    splitAttempts: [],
    finished: false,
  };
  const publish = () =>
    onUpdate({
      ...report,
      batches: report.batches.map((b) => ({ ...b })),
      splitAttempts: [...(report.splitAttempts ?? [])],
    });
  publish();
  const queue = [...report.batches];
  let next = 0;
  let halted = false;
  const worker = async () => {
    while (!halted && !shouldStop()) {
      const batch = queue[next];
      if (!batch) return;
      next++;
      batch.status = "running";
      publish();
      let stop = false;
      try {
        const result = await detect({
          body: {
            expected_version: doc.version,
            expected_sha256: doc.canonical_sha256,
            ...(options.sourceVersion !== null
              ? { source_version: options.sourceVersion }
              : {}),
            evidence_ids: batch.evidenceIds,
            provider_id: options.providerId,
          },
          idempotencyKey: batch.key,
        });
        batch.check = result;
        if (
          result.version !== doc.version ||
          result.canonical_sha256 !== doc.canonical_sha256 ||
          result.checked_evidence_ids.length !== batch.evidenceIds.length ||
          !batch.evidenceIds.every((id) =>
            result.checked_evidence_ids.includes(id),
          )
        ) {
          batch.status = "failed";
          batch.errorCode = "ocr_text_source_changed";
          stop = true;
        } else if (result.status === "completed") batch.status = "completed";
        else {
          batch.status = result.status === "failed" ? "failed" : "uncertain";
          batch.errorCode = result.error_code ?? "ocr_spelling_interrupted";
          stop =
            batch.status === "uncertain" ||
            /quota_|provider_|model_|permission|forbidden/.test(
              batch.errorCode,
            );
        }
      } catch (error) {
        batch.errorCode =
          error instanceof ApiProblemError
            ? error.code
            : "ocr_spelling_interrupted";
        if (
          error instanceof ApiProblemError &&
          SPLITTABLE_TOKEN_ERRORS.has(error.code)
        ) {
          batch.tokenDetail = error.problem?.detail;
        }
        batch.status =
          !(error instanceof ApiProblemError) ||
          error.status === 0 ||
          /uncertain|interrupted/.test(error.code)
            ? "uncertain"
            : "failed";
        stop =
          !(error instanceof ApiProblemError) ||
          batch.status === "uncertain" ||
          error.status >= 500 ||
          [401, 403, 409, 429].includes(error.status) ||
          /quota_|provider_|model_|version|source|forbidden|permission/.test(
            batch.errorCode ?? "",
          );
      }
      const tokenFailure =
        batch.status === "failed" &&
        SPLITTABLE_TOKEN_ERRORS.has(batch.errorCode ?? "");
      if (stop && !tokenFailure) halted = true;
      if (
        !halted &&
        !shouldStop() &&
        tokenFailure &&
        batch.evidenceIds.length > 1
      ) {
        const middle = Math.ceil(batch.evidenceIds.length / 2);
        const children: SpellingBatch[] = [
          batch.evidenceIds.slice(0, middle),
          batch.evidenceIds.slice(middle),
        ].map((evidenceIds, index) => ({
          page: batch.page,
          evidenceIds,
          key: `${batch.key}:${index + 1}`,
          status: "pending",
        }));
        report.splitAttempts?.push(batch);
        report.batches.splice(report.batches.indexOf(batch), 1, ...children);
        queue.push(...children);
      }
      publish();
    }
  };
  // Each slot claims its next group only after settling the active request.
  // A fatal result stops new claims; already sent requests are drained, never lost.
  await Promise.all(
    Array.from({ length: options.concurrency ?? 2 }, () => worker()),
  );
  for (const batch of report.batches)
    if (batch.status === "pending") batch.status = "not_run";
  report.finished = true;
  publish();
  return report;
}
