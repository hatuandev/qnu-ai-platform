import assert from "node:assert/strict";
import test from "node:test";
import {
  type DocumentTaskProgressInput,
  resolveDocumentTaskProgress,
} from "./document-task-progress.ts";

test("Case 1: OCR progress runs from unknown total -> known total -> all pages read", () => {
  // Step 1.1: OCR started but total pages not yet known (Gotenberg rendering)
  const step1 = resolveDocumentTaskProgress({
    status: "waiting_ocr",
    ocrProgress: {
      pages_done: 0,
      pages_total: null,
    },
  });
  assert.equal(step1.statusLabel, "Đang đọc tệp");
  assert.equal(step1.readingPhase.status, "running");
  assert.equal(step1.readingPhase.isIndeterminate, true);
  assert.equal(step1.readingPhase.percent, null);
  assert.equal(step1.readingPhase.detailText, "Đang phân tích tệp…");
  assert.equal(step1.unifiedPercent, null);
  assert.equal(step1.isIndeterminate, true);
  assert.equal(step1.isOverallComplete, false);

  // Step 1.2: Total pages established (14 pages), read 4 pages
  const step2 = resolveDocumentTaskProgress({
    status: "waiting_ocr",
    ocrProgress: {
      pages_done: 4,
      pages_total: 14,
      pagination: "page",
    },
  });
  assert.equal(step2.readingPhase.status, "running");
  assert.equal(step2.readingPhase.isIndeterminate, false);
  assert.equal(step2.readingPhase.completed, 4);
  assert.equal(step2.readingPhase.total, 14);
  assert.equal(step2.readingPhase.percent, 28);
  assert.equal(step2.readingPhase.detailText, "Đã đọc 4/14 trang");
  assert.equal(step2.unifiedPercent, 14); // 28% of 50% = 14%
  assert.equal(step2.stepLabel, "Đã đọc 4/14 trang");
  assert.equal(step2.isOverallComplete, false);

  // Step 1.3: All 14 pages read
  const step3 = resolveDocumentTaskProgress({
    status: "waiting_ocr",
    ocrProgress: {
      pages_done: 14,
      pages_total: 14,
      pagination: "page",
    },
  });
  assert.equal(step3.readingPhase.status, "running");
  assert.equal(step3.readingPhase.percent, 100);
  assert.equal(step3.readingPhase.detailText, "Đã đọc 14/14 trang");
  assert.equal(step3.unifiedPercent, 50); // 100% of Phase 1 = 50% of overall
  assert.equal(step3.stepLabel, "Đã đọc 14/14 trang");
  // Important: Overall task is NOT complete yet because compilation has not started
  assert.equal(step3.isOverallComplete, false);
});

test("Case 2: Transitioning to compilation does NOT roll overall progress or Phase 1 back to 0%", () => {
  // State before transition: OCR complete (14/14)
  const ocrDone = resolveDocumentTaskProgress({
    status: "waiting_ocr",
    ocrProgress: {
      pages_done: 14,
      pages_total: 14,
    },
  });
  assert.equal(ocrDone.readingPhase.percent, 100);

  // State right after transition: status becomes "compiling", compilation is at 0/3 parts
  const compilingStarted = resolveDocumentTaskProgress({
    status: "compiling",
    ocrProgress: {
      pages_done: 14,
      pages_total: 14,
    },
    compilationProgress: {
      completed: 0,
      total: 3,
      segmented: true,
    },
  });

  // Phase 1 (Đọc tệp) REMAINS 100% completed! It does NOT roll back to 0%!
  assert.equal(compilingStarted.readingPhase.status, "completed");
  assert.equal(compilingStarted.readingPhase.percent, 100);
  assert.equal(compilingStarted.readingPhase.detailText, "Đã đọc 14 trang");

  // Unified 1-line progress remains 50% across the boundary, NOT resetting to 0%!
  assert.equal(ocrDone.unifiedPercent, 50);
  assert.equal(compilingStarted.unifiedPercent, 50);
  assert.equal(compilingStarted.stepLabel, "Đã chuẩn bị 0/3 phần");

  // Phase 2 (Chuẩn bị) is running with 0/3 parts
  assert.equal(compilingStarted.compilingPhase.status, "running");
  assert.equal(compilingStarted.compilingPhase.completed, 0);
  assert.equal(compilingStarted.compilingPhase.total, 3);
  assert.equal(compilingStarted.compilingPhase.percent, 0);
  assert.equal(
    compilingStarted.compilingPhase.detailText,
    "Đã chuẩn bị 0/3 phần",
  );

  // Overall task is still in progress, not prematurely complete
  assert.equal(compilingStarted.isOverallComplete, false);
});

test("Case 3: Compilation completes immediately after OCR: reports ready accurately without fake delay", () => {
  const readyImmediately = resolveDocumentTaskProgress({
    status: "ready",
    ocrProgress: {
      pages_done: 1,
      pages_total: 1,
    },
    compilationProgress: {
      completed: 1,
      total: 1,
    },
  });

  assert.equal(readyImmediately.isOverallComplete, true);
  assert.equal(readyImmediately.statusLabel, "Đã chuẩn bị xong");
  assert.equal(readyImmediately.unifiedPercent, 100);
  assert.equal(readyImmediately.stepLabel, "Đã chuẩn bị xong");
  assert.equal(readyImmediately.readingPhase.status, "completed");
  assert.equal(readyImmediately.readingPhase.percent, 100);
  assert.equal(readyImmediately.compilingPhase.status, "completed");
  assert.equal(readyImmediately.compilingPhase.percent, 100);
  assert.equal(readyImmediately.isFailed, false);
  assert.equal(readyImmediately.isCancelled, false);
});

test("Case 4: Multi-part compiler splits and advances parts accurately", () => {
  // 4 parts total, 2 completed
  const progressMid = resolveDocumentTaskProgress({
    status: "compiling",
    compilationProgress: {
      completed: 2,
      total: 4,
      segmented: true,
    },
  });

  assert.equal(progressMid.compilingPhase.status, "running");
  assert.equal(progressMid.compilingPhase.completed, 2);
  assert.equal(progressMid.compilingPhase.total, 4);
  assert.equal(progressMid.compilingPhase.percent, 50);
  assert.equal(progressMid.compilingPhase.detailText, "Đã chuẩn bị 2/4 phần");
  // 50% base + 50% of 45% = 73%
  assert.equal(progressMid.unifiedPercent, 73);
  assert.equal(progressMid.stepLabel, "Đã chuẩn bị 2/4 phần");
  assert.equal(progressMid.isOverallComplete, false);
});

test("Case 5: Child segments completed but intent not yet ready: never reports overall completion", () => {
  // All compilation segments reported finished (4/4), but intent status is still "compiling"
  const allSegmentsDone = resolveDocumentTaskProgress({
    status: "compiling",
    compilationProgress: {
      completed: 4,
      total: 4,
      segmented: true,
    },
  });

  assert.equal(allSegmentsDone.compilingPhase.completed, 4);
  assert.equal(allSegmentsDone.compilingPhase.percent, 100);
  // Capped at 95% while waiting for intent ready
  assert.equal(allSegmentsDone.unifiedPercent, 95);
  // Overall task MUST NOT be reported complete until intent itself transitions to ready
  assert.equal(allSegmentsDone.isOverallComplete, false);
});

test("Case 6: Terminal states (cancelled, failed, uncertain) NEVER show 100% completion", () => {
  // 6.1 Cancelled
  const cancelledTask = resolveDocumentTaskProgress({
    status: "cancelled",
    ocrProgress: { pages_done: 5, pages_total: 10 },
  });
  assert.equal(cancelledTask.isOverallComplete, false);
  assert.equal(cancelledTask.isCancelled, true);
  assert.equal(cancelledTask.statusLabel, "Đã dừng xử lý");
  assert.equal(cancelledTask.unifiedPercent, null);

  // 6.2 Failed
  const failedTask = resolveDocumentTaskProgress({
    status: "failed",
    errorCode: "ocr_timeout",
  });
  assert.equal(failedTask.isOverallComplete, false);
  assert.equal(failedTask.isFailed, true);
  assert.equal(failedTask.statusLabel, "Xử lý gặp lỗi");
  assert.match(failedTask.detail, /ocr_timeout/);
  assert.equal(failedTask.unifiedPercent, null);

  // 6.3 Uncertain
  const uncertainTask = resolveDocumentTaskProgress({
    status: "uncertain",
  });
  assert.equal(uncertainTask.isOverallComplete, false);
  assert.equal(uncertainTask.isUncertain, true);
  assert.equal(uncertainTask.statusLabel, "Chưa xác định kết quả");
  assert.equal(uncertainTask.unifiedPercent, null);
});

test("Case 7: Two documents running simultaneously keep independent progress data", () => {
  const doc1Input: DocumentTaskProgressInput = {
    status: "waiting_ocr",
    ocrProgress: {
      pages_done: 3,
      pages_total: 10,
    },
  };

  const doc2Input: DocumentTaskProgressInput = {
    status: "compiling",
    compilationProgress: {
      completed: 1,
      total: 2,
      segmented: true,
    },
  };

  const doc1 = resolveDocumentTaskProgress(doc1Input);
  const doc2 = resolveDocumentTaskProgress(doc2Input);

  assert.equal(doc1.statusLabel, "Đang đọc tệp");
  assert.equal(doc1.readingPhase.percent, 30);
  assert.equal(doc1.unifiedPercent, 15); // 30% of 50%
  assert.equal(doc1.compilingPhase.status, "pending");

  assert.equal(doc2.statusLabel, "Đang chuẩn bị nội dung");
  assert.equal(doc2.readingPhase.status, "completed");
  assert.equal(doc2.compilingPhase.percent, 50);
  assert.equal(doc2.unifiedPercent, 73); // 50% + 50% of 45%
});
