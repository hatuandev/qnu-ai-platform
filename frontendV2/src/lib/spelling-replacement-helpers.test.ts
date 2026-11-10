import assert from "node:assert/strict";
import test from "node:test";
import type { Suggestion, TextUnit } from "../api/ocr/requests.ts";
import {
  applySuggestionsToText,
  buildTextChanges,
  type SuggestionDecision,
} from "./spelling-replacement-helpers.ts";

test("applySuggestionsToText: single replacement applies accurately", () => {
  const original = "Học sinh được miễm học phí học kỳ 1.";
  const replacements = [
    {
      start: original.indexOf("miễm"),
      end: original.indexOf("miễm") + 4,
      original: "miễm",
      replacement: "miễn",
    },
  ];

  const result = applySuggestionsToText(original, replacements);
  assert.equal(result.resultText, "Học sinh được miễn học phí học kỳ 1.");
  assert.equal(result.appliedCount, 1);
  assert.equal(result.errors.length, 0);
});

test("applySuggestionsToText: multiple replacements on same string apply right-to-left without offset drift", () => {
  const original =
    "Trường Đai hoc Quy Nhơn tuyển sinh năm 2026 tai tinh Bình Định.";
  // Suggestion A: "Đai hoc" -> "Đại học" (index 7)
  // Suggestion B: "tai tinh" -> "tại tỉnh" (index 43)
  const repA = {
    start: original.indexOf("Đai hoc"),
    end: original.indexOf("Đai hoc") + "Đai hoc".length,
    original: "Đai hoc",
    replacement: "Đại học",
  };
  const repB = {
    start: original.indexOf("tai tinh"),
    end: original.indexOf("tai tinh") + "tai tinh".length,
    original: "tai tinh",
    replacement: "tại tỉnh",
  };

  // Provide them in ascending or mixed order; algorithm MUST sort descending
  const result = applySuggestionsToText(original, [repA, repB]);
  assert.equal(
    result.resultText,
    "Trường Đại học Quy Nhơn tuyển sinh năm 2026 tại tỉnh Bình Định.",
  );
  assert.equal(result.appliedCount, 2);
  assert.equal(result.errors.length, 0);
});

test("applySuggestionsToText: detects mismatch if original snippet was changed", () => {
  const original = "Văn bản mẫu đã được chuẩn hóa.";
  const invalidRep = {
    start: 0,
    end: 7,
    original: "Tài liệu", // does not match "Văn bản"
    replacement: "Hồ sơ",
  };

  const result = applySuggestionsToText(original, [invalidRep]);
  assert.equal(result.resultText, original); // unchanged
  assert.equal(result.appliedCount, 0);
  assert.equal(result.errors.length, 1);
});

test("spelling offsets count Unicode code points like the backend", () => {
  const result = applySuggestionsToText("📌 bạ", [
    { start: 2, end: 4, original: "bạ", replacement: "bạn" },
  ]);
  assert.equal(result.resultText, "📌 bạn");
  assert.equal(result.appliedCount, 1);
  assert.deepEqual(result.errors, []);
});

test("buildTextChanges: converts user decisions into durable TextChange array", () => {
  const units: TextUnit[] = [
    {
      evidence_id: "ev_1",
      page: 1,
      kind: "text",
      text: "Đai hoc Quy Nhon là cơ sở công lập.",
      original_text: "Đai hoc Quy Nhon là cơ sở công lập.",
      bbox: {},
    },
    {
      evidence_id: "ev_2",
      page: 1,
      kind: "text",
      text: "Học phí theo quy định 2026.",
      original_text: "Học phí theo quy định 2026.",
      bbox: {},
    },
  ];

  const suggestions: Suggestion[] = [
    {
      evidence_id: "ev_1",
      start: 0,
      end: 7,
      original: "Đai hoc",
      replacement: "Đại học",
      reason: "Thiếu dấu thanh.",
    },
    {
      evidence_id: "ev_1",
      start: 8,
      end: 16,
      original: "Quy Nhon",
      replacement: "Quy Nhơn",
      reason: "Thiếu dấu thanh.",
    },
    {
      evidence_id: "ev_2",
      start: 0,
      end: 7,
      original: "Học phí",
      replacement: "Học phi",
      reason: "Sai từ điển.",
    },
  ];

  const decisions = new Map<string, SuggestionDecision>([
    ["ev_1:0:7", { status: "applied" }],
    ["ev_1:8:16", { status: "applied" }],
    ["ev_2:0:7", { status: "ignored" }], // ignored!
  ]);

  const { changes, totalApplied, errors } = buildTextChanges(
    units,
    suggestions,
    decisions,
  );

  assert.equal(totalApplied, 2);
  assert.equal(errors.length, 0);
  assert.equal(changes.length, 1); // only ev_1 changed
  assert.equal(changes[0].evidence_id, "ev_1");
  assert.equal(changes[0].before, "Đai hoc Quy Nhon là cơ sở công lập.");
  assert.equal(changes[0].after, "Đại học Quy Nhơn là cơ sở công lập.");
});
