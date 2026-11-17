import type { BackgroundTaskStatus } from "./background-tasks-store.ts";

export type StepState = "pending" | "running" | "completed" | "failed";

export type StepProgressInfo = {
  status: StepState;
  completed: number;
  total: number | null;
  unit: string;
  percent: number | null; // ONLY integer 0-100 when total is valid
  isIndeterminate: boolean; // true when running but total not yet known
  detailText: string;
};

export type DocumentTaskProgressPresentation = {
  status: BackgroundTaskStatus;
  statusLabel: string;
  detail: string;
  isOverallComplete: boolean; // ONLY true when status === "ready"
  isFailed: boolean;
  isCancelled: boolean;
  isUncertain: boolean;
  unifiedPercent: number | null; // 0-100 continuous line across the entire job
  isIndeterminate: boolean; // true when running but metrics cannot determine percent yet
  stepLabel: string; // clear label of current active step
  readingPhase: StepProgressInfo;
  compilingPhase: StepProgressInfo;
};

export type DocumentTaskProgressInput = {
  status: BackgroundTaskStatus;
  step?: string | null;
  errorCode?: string | null;
  ocrProgress?: {
    pages_done: number;
    pages_total: number | null;
    pagination?: "page" | "document";
  } | null;
  compilationProgress?: {
    completed: number;
    total: number;
    segmented?: boolean;
    elapsedSeconds?: number | null;
  } | null;
};

/**
 * Pure calculation of document background task progress across two distinct phases:
 * Phase 1: Reading / OCR (Đọc tệp)
 * Phase 2: Compilation / Preparation (Chuẩn bị nội dung)
 *
 * Invariants:
 * 1. Step progress is strictly separated; moving from OCR to Compilation does NOT roll overall progress back to 0%.
 * 2. When Phase 1 completes, it remains completed (100%) while Phase 2 begins.
 * 3. No arbitrary percentage guesses (no fake 30%, 70%, 95%). If total is unknown, step is indeterminate.
 * 4. Only marks overall task complete when status is strictly "ready".
 * 5. Failed, cancelled, or uncertain tasks NEVER display 100% completion.
 */
export function resolveDocumentTaskProgress(
  input: DocumentTaskProgressInput,
): DocumentTaskProgressPresentation {
  const { status, errorCode, ocrProgress, compilationProgress } = input;

  const isFailed = status === "failed";
  const isCancelled = status === "cancelled";
  const isUncertain = status === "uncertain";
  const isReady = status === "ready";

  // 1. Phase 1: Reading / OCR (Đọc tệp)
  let readingPhase: StepProgressInfo;
  const ocrUnit = ocrProgress?.pagination === "document" ? "đơn vị" : "trang";

  if (status === "queued") {
    readingPhase = {
      status: "pending",
      completed: 0,
      total: null,
      unit: ocrUnit,
      percent: null,
      isIndeterminate: false,
      detailText: "Chờ đọc tệp",
    };
  } else if (status === "waiting_ocr") {
    const pagesDone = Math.max(0, ocrProgress?.pages_done ?? 0);
    const pagesTotal = ocrProgress?.pages_total ?? null;

    if (
      pagesTotal !== null &&
      Number.isInteger(pagesTotal) &&
      pagesTotal > 0 &&
      pagesDone <= pagesTotal
    ) {
      const pct = Math.floor((pagesDone / pagesTotal) * 100);
      readingPhase = {
        status: "running",
        completed: pagesDone,
        total: pagesTotal,
        unit: ocrUnit,
        percent: pct,
        isIndeterminate: false,
        detailText: `Đã đọc ${pagesDone}/${pagesTotal} ${ocrUnit}`,
      };
    } else {
      // Total pages not yet established by Gotenberg / renderer
      readingPhase = {
        status: "running",
        completed: pagesDone,
        total: null,
        unit: ocrUnit,
        percent: null,
        isIndeterminate: true,
        detailText:
          pagesDone > 0
            ? `Đã đọc ${pagesDone} ${ocrUnit}`
            : "Đang phân tích tệp…",
      };
    }
  } else if (status === "compiling" || isReady) {
    // OCR is durable and complete
    const totalPages = ocrProgress?.pages_total ?? ocrProgress?.pages_done;
    readingPhase = {
      status: "completed",
      completed: totalPages ?? 0,
      total: totalPages ?? null,
      unit: ocrUnit,
      percent: 100,
      isIndeterminate: false,
      detailText:
        totalPages && totalPages > 0
          ? `Đã đọc ${totalPages} ${ocrUnit}`
          : "Đã đọc tệp xong",
    };
  } else {
    // cancelled, failed, uncertain
    readingPhase = {
      status: isFailed ? "failed" : "pending",
      completed: ocrProgress?.pages_done ?? 0,
      total: ocrProgress?.pages_total ?? null,
      unit: ocrUnit,
      percent: null,
      isIndeterminate: false,
      detailText: isCancelled
        ? "Đã dừng xử lý"
        : isFailed
          ? "Đọc tệp gặp lỗi"
          : "Chưa xác định",
    };
  }

  // 2. Phase 2: Compilation / Preparation (Chuẩn bị nội dung)
  let compilingPhase: StepProgressInfo;

  if (status === "queued" || status === "waiting_ocr") {
    compilingPhase = {
      status: "pending",
      completed: 0,
      total: null,
      unit: "phần",
      percent: null,
      isIndeterminate: false,
      detailText: "Chờ chuẩn bị nội dung",
    };
  } else if (status === "compiling") {
    const compDone = Math.max(0, compilationProgress?.completed ?? 0);
    const compTotal = compilationProgress?.total ?? null;

    if (
      compTotal !== null &&
      Number.isInteger(compTotal) &&
      compTotal > 0 &&
      compDone <= compTotal
    ) {
      // Segmented / multi-part compilation
      const pct = Math.floor((compDone / compTotal) * 100);
      compilingPhase = {
        status: "running",
        completed: compDone,
        total: compTotal,
        unit: "phần",
        percent: pct,
        isIndeterminate: false,
        detailText: `${(compilationProgress?.elapsedSeconds ?? 0) >= 25 * 60 ? "Đang mất nhiều thời gian · " : ""}Đã chuẩn bị ${compDone}/${compTotal} phần`,
      };
    } else {
      // Single-part compilation or total not established
      compilingPhase = {
        status: "running",
        completed: compDone,
        total: compTotal,
        unit: "phần",
        percent: null,
        isIndeterminate: true,
        detailText: "Đang biên soạn nội dung…",
      };
    }
  } else if (isReady) {
    compilingPhase = {
      status: "completed",
      completed: compilationProgress?.total ?? 1,
      total: compilationProgress?.total ?? 1,
      unit: "phần",
      percent: 100,
      isIndeterminate: false,
      detailText: "Đã chuẩn bị xong",
    };
  } else {
    // cancelled, failed, uncertain
    compilingPhase = {
      status: isFailed ? "failed" : "pending",
      completed: 0,
      total: null,
      unit: "phần",
      percent: null,
      isIndeterminate: false,
      detailText: isCancelled
        ? "Đã dừng xử lý"
        : isFailed
          ? "Chuẩn bị gặp lỗi"
          : "Chưa xác định",
    };
  }

  // 3. Unified 1-Line Progress Across Whole Process (0% -> 100%)
  let unifiedPercent: number | null = null;
  let isIndeterminate = false;
  let stepLabel = "";

  if (status === "queued") {
    unifiedPercent = 0;
    isIndeterminate = false;
    stepLabel = "Chờ đọc tệp";
  } else if (status === "waiting_ocr") {
    // OCR is Phase 1 (0% -> 50%)
    if (readingPhase.percent !== null) {
      unifiedPercent = Math.min(
        50,
        Math.round((readingPhase.percent / 100) * 50),
      );
      isIndeterminate = false;
    } else {
      unifiedPercent = null;
      isIndeterminate = true;
    }
    stepLabel = readingPhase.detailText;
  } else if (status === "compiling") {
    // Compilation is Phase 2 (50% -> 95%, 100% strictly on ready)
    if (compilingPhase.percent !== null) {
      unifiedPercent =
        50 + Math.min(45, Math.round((compilingPhase.percent / 100) * 45));
      isIndeterminate = false;
    } else {
      unifiedPercent = 50; // Smooth entry into compilation without regression
      isIndeterminate = false;
    }
    stepLabel = compilingPhase.detailText;
  } else if (isReady) {
    unifiedPercent = 100;
    isIndeterminate = false;
    stepLabel = "Đã chuẩn bị xong";
  } else if (isCancelled) {
    unifiedPercent = null;
    isIndeterminate = false;
    stepLabel = "Đã dừng xử lý";
  } else if (isFailed) {
    unifiedPercent = null;
    isIndeterminate = false;
    stepLabel = "Xử lý gặp lỗi";
  } else if (isUncertain) {
    unifiedPercent = null;
    isIndeterminate = false;
    stepLabel = "Chưa xác định kết quả";
  } else {
    unifiedPercent = null;
    isIndeterminate = true;
    stepLabel = "Đang xử lý…";
  }

  // 4. Overall Labels & Subtitle
  let statusLabel: string;
  let detail: string;

  switch (status) {
    case "queued":
      statusLabel = "Đã nhận yêu cầu";
      detail = "Đang xếp hàng chờ xử lý…";
      break;
    case "waiting_ocr":
      statusLabel = "Đang đọc tệp";
      detail = readingPhase.detailText;
      break;
    case "compiling":
      statusLabel = "Đang chuẩn bị nội dung";
      detail = compilingPhase.detailText;
      break;
    case "ready":
      statusLabel = "Đã chuẩn bị xong";
      detail = "Bản nháp đã sẵn sàng để kiểm tra và duyệt.";
      break;
    case "cancelled":
      statusLabel = "Đã dừng xử lý";
      detail = "Tác vụ đã được dừng theo yêu cầu.";
      break;
    case "failed":
      statusLabel = "Xử lý gặp lỗi";
      detail = errorCode
        ? `Mã lỗi: ${errorCode}`
        : "Quá trình xử lý gặp lỗi. Vui lòng thử lại.";
      break;
    case "uncertain":
      statusLabel = "Chưa xác định kết quả";
      detail = "Không thể xác định kết quả. Vui lòng thử lại.";
      break;
    default:
      statusLabel = "Đang xử lý";
      detail = "Hệ thống đang xử lý trong nền…";
      break;
  }

  return {
    status,
    statusLabel,
    detail,
    isOverallComplete: isReady,
    isFailed,
    isCancelled,
    isUncertain,
    unifiedPercent,
    isIndeterminate,
    stepLabel,
    readingPhase,
    compilingPhase,
  };
}
