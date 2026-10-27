import assert from "node:assert/strict";
import { describe, it } from "vitest";
import { ocrQueryKeys } from "../src/features/knowledge/ocr-queries.ts";
import {
  applySuggestionsToText,
  detectRequestSchema,
  formatOcrError,
  formatPageStatus,
  formatRunStatus,
  getCodePointLength,
  getCodePoints,
  replaceSpanByCodePoints,
  saveReviewSchema,
  sliceByCodePoints,
  validateSuggestionSpan,
} from "../src/features/knowledge/ocr-schemas.ts";
import type { Suggestion } from "../src/features/knowledge/ocr-types.ts";

describe("OCR & Post-OCR Text Review Tests", () => {
  describe("1. Python Unicode Code Point Parity (BMP and non-BMP)", () => {
    it("handles non-BMP characters without UTF-16 offset distortion", () => {
      // In JS, "🔍".length is 2 (UTF-16 surrogate pair), but Python len("🔍") is 1
      const text = "Tài liệu 🔍 QNU AI Platform 🎉";

      // UTF-16 length in JS:
      assert.strictEqual(text.length, 30);
      // Code point length in Python parity:
      assert.strictEqual(getCodePointLength(text), 28);

      const points = getCodePoints(text);
      assert.strictEqual(points[9], "🔍");
      assert.strictEqual(points[27], "🎉");

      // Slice span [9, 10] matches the single emoji character
      assert.strictEqual(sliceByCodePoints(text, 9, 10), "🔍");

      // Slice span [0, 8] matches "Tài liệu"
      assert.strictEqual(sliceByCodePoints(text, 0, 8), "Tài liệu");
    });

    it("replaces spans accurately using Unicode code points", () => {
      const text = "Dự án 𝕏 chuyển sang 🚀 vệ tinh";
      // Code points:
      // "Dự án " (6 points: 0..5)
      // "𝕏" (1 point: 6)
      // " chuyển sang " (13 points: 7..19)
      // "🚀" (1 point: 20)
      // " vệ tinh" (8 points: 21..28)
      assert.strictEqual(sliceByCodePoints(text, 6, 7), "𝕏");
      assert.strictEqual(sliceByCodePoints(text, 20, 21), "🚀");

      const replaced = replaceSpanByCodePoints(text, 6, 7, "QNU");
      assert.strictEqual(replaced, "Dự án QNU chuyển sang 🚀 vệ tinh");
      assert.strictEqual(sliceByCodePoints(replaced, 22, 23), "🚀");
    });

    it("validates suggestion span against original string with code points", () => {
      const text = "Trường Đại học Quy Nhơn, năm 2026 🎉.";
      const validSuggestion: Pick<Suggestion, "start" | "end" | "original"> = {
        start: 7,
        end: 14,
        original: "Đại học",
      };
      assert.strictEqual(validateSuggestionSpan(text, validSuggestion), true);

      const invalidSpan: Pick<Suggestion, "start" | "end" | "original"> = {
        start: 7,
        end: 15,
        original: "Đại học",
      };
      assert.strictEqual(validateSuggestionSpan(text, invalidSpan), false);
    });
  });

  describe("2. Multiple AI Suggestions & Overlap Protection", () => {
    it("applies multiple non-overlapping suggestions in descending order of start offset", () => {
      const text = "Trường Dai hoc Quy Nhon, nam 2026";
      const suggestions: Suggestion[] = [
        {
          evidence_id: "ev_1",
          start: 7,
          end: 14,
          original: "Dai hoc",
          replacement: "Đại học",
          reason: "Thiếu dấu tiếng Việt",
        },
        {
          evidence_id: "ev_1",
          start: 15,
          end: 23,
          original: "Quy Nhon",
          replacement: "Quy Nhơn",
          reason: "Thiếu dấu tiếng Việt",
        },
        {
          evidence_id: "ev_1",
          start: 25,
          end: 28,
          original: "nam",
          replacement: "năm",
          reason: "Thiếu dấu tiếng Việt",
        },
      ];

      const outcome = applySuggestionsToText(text, suggestions);
      assert.strictEqual(outcome.appliedCount, 3);
      assert.strictEqual(outcome.skippedCount, 0);
      assert.strictEqual(
        outcome.updatedText,
        "Trường Đại học Quy Nhơn, năm 2026",
      );
    });

    it("detects and rejects overlapping suggestions safely", () => {
      const text = "Trường Đại học Quy Nhơn";
      const suggestions: Suggestion[] = [
        {
          evidence_id: "ev_1",
          start: 0,
          end: 14,
          original: "Trường Đại học",
          replacement: "Trường ĐH",
          reason: "Rút gọn",
        },
        {
          evidence_id: "ev_1",
          start: 7,
          end: 14,
          original: "Đại học",
          replacement: "ĐH",
          reason: "Rút gọn",
        },
      ];

      const outcome = applySuggestionsToText(text, suggestions);
      assert.strictEqual(outcome.appliedCount, 0);
      assert.ok(outcome.error?.includes("chồng lấn"));
      assert.strictEqual(outcome.updatedText, text);
    });

    it("skips stale suggestions when text has already changed", () => {
      const modifiedDraft = "Trường ĐH Quy Nhơn";

      const suggestion: Suggestion = {
        evidence_id: "ev_1",
        start: 7,
        end: 14,
        original: "Dai hoc",
        replacement: "Đại học",
        reason: "Sửa dấu",
      };

      const outcome = applySuggestionsToText(modifiedDraft, [suggestion]);
      assert.strictEqual(outcome.appliedCount, 0);
      assert.strictEqual(outcome.skippedCount, 1);
      assert.strictEqual(outcome.updatedText, modifiedDraft);
    });
  });

  describe("3. Zod Schemas Validation", () => {
    it("validates SaveReview schema strictly", () => {
      const valid = {
        expected_version: 0,
        expected_sha256: "a".repeat(64),
        changes: [
          {
            evidence_id: "ev_unit_1",
            before: "chua sua",
            after: "da sua",
          },
        ],
      };
      assert.doesNotThrow(() => saveReviewSchema.parse(valid));

      // Rejects empty changes
      assert.throws(() =>
        saveReviewSchema.parse({
          ...valid,
          changes: [],
        }),
      );

      // Rejects duplicate evidence_id
      assert.throws(() =>
        saveReviewSchema.parse({
          ...valid,
          changes: [
            { evidence_id: "ev_1", before: "A", after: "B" },
            { evidence_id: "ev_1", before: "A", after: "C" },
          ],
        }),
      );

      // Rejects whitespace-only after (cannot clear entire unit text)
      assert.throws(() =>
        saveReviewSchema.parse({
          ...valid,
          changes: [{ evidence_id: "ev_1", before: "A", after: "   " }],
        }),
      );

      // Rejects invalid sha256
      assert.throws(() =>
        saveReviewSchema.parse({
          ...valid,
          expected_sha256: "invalid-sha",
        }),
      );
    });

    it("validates DetectRequest schema strictly", () => {
      const valid = {
        expected_version: 1,
        expected_sha256: "b".repeat(64),
        evidence_ids: ["ev_1", "ev_2"],
        provider_id: "prov_gpt",
        max_output_tokens: 4096,
      };
      assert.doesNotThrow(() => detectRequestSchema.parse(valid));

      // Rejects empty evidence_ids
      assert.throws(() =>
        detectRequestSchema.parse({ ...valid, evidence_ids: [] }),
      );

      // Rejects duplicate evidence_ids
      assert.throws(() =>
        detectRequestSchema.parse({
          ...valid,
          evidence_ids: ["ev_1", "ev_1"],
        }),
      );

      // Rejects > 100 units
      const over100 = Array.from({ length: 101 }, (_, i) => `ev_${i}`);
      assert.throws(() =>
        detectRequestSchema.parse({ ...valid, evidence_ids: over100 }),
      );
    });
  });

  describe("4. Status & Error Formatting", () => {
    it("formats processing run statuses honestly without fabricating completion", () => {
      assert.strictEqual(formatRunStatus("queued").label, "Đang chờ xử lý");
      assert.strictEqual(formatRunStatus("running").label, "Đang xử lý");
      assert.strictEqual(formatRunStatus("completed").label, "Hoàn tất");
      assert.strictEqual(formatRunStatus("failed").label, "Thất bại");
      assert.strictEqual(
        formatRunStatus("uncertain").label,
        "Không xác định (Hết hạn)",
      );
      assert.strictEqual(formatRunStatus("cancelled").label, "Đã hủy");
    });

    it("formats page statuses preserving blank page meaning", () => {
      // Blank is a valid empty page, not an error!
      const blankInfo = formatPageStatus("blank");
      assert.strictEqual(blankInfo.label, "Trang trắng");
      assert.strictEqual(blankInfo.variant, "secondary");

      const inFlightInfo = formatPageStatus("in_flight");
      assert.strictEqual(inFlightInfo.label, "Đang OCR");

      const failInfo = formatPageStatus("failed");
      assert.strictEqual(failInfo.label, "Lỗi");
    });

    it("formats RFC 7807 error codes accurately", () => {
      assert.ok(formatOcrError("processing_run_active").includes("hoạt động"));
      assert.ok(
        formatOcrError("ocr_text_version_conflict").includes(
          "phiên bản sửa mới",
        ),
      );
      assert.ok(
        formatOcrError("idempotency_conflict").includes(
          "dùng cho nội dung khác",
        ),
      );
      assert.ok(formatOcrError("ocr_provider_timeout").includes("uncertain"));
    });
  });

  describe("5. Query Key Factory Scoping", () => {
    it("scopes all query keys with sessionId, workspaceId, and revisionId", () => {
      const keys = ocrQueryKeys.runs(
        42,
        "ws_alpha",
        "coll_beta",
        "src_gamma",
        "rev_delta",
        1,
        20,
      );

      assert.deepStrictEqual(keys, [
        "v1",
        42,
        "workspaces",
        "ws_alpha",
        "collections",
        "coll_beta",
        "sources",
        "src_gamma",
        "revisions",
        "rev_delta",
        "ocr",
        "runs",
        { page: 1, pageSize: 20 },
      ]);
    });
  });
});
