// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type {
  DetectionResponse,
  ReviewDocument,
  Suggestion,
} from "@/features/knowledge/ocr-types";
import { SpellingResultView } from "@/features/knowledge/spelling-result-panel";

afterEach(cleanup);
const suggestion: Suggestion = {
  evidence_id: "target",
  start: 13,
  end: 16,
  original: "bán",
  replacement: "bản",
  reason: "Kiểm tra cụm từ.",
  context_before: "bệnh viện cơ bán",
  context_after: "bệnh viện cơ bản",
};
const doc: ReviewDocument = {
  run_id: "run",
  version: 29,
  version_id: "version",
  canonical_sha256: "a".repeat(64),
  original_sha256: "b".repeat(64),
  markdown_sha256: "c".repeat(64),
  saved_at: null,
  units: [
    {
      evidence_id: "target",
      page: 15,
      kind: "text",
      text: "bệnh viện cơ bán",
      original_text: "bệnh viện cơ bán",
      bbox: {},
      row: null,
      column: null,
    },
  ],
};
const check: DetectionResponse = {
  id: "check",
  status: "completed",
  version: 29,
  canonical_sha256: doc.canonical_sha256,
  suggestions: [],
  checked_evidence_ids: ["target"],
  error_code: null,
  usage_id: null,
  created_at: "2026-11-01T00:00:00Z",
};
function show(result: DetectionResponse) {
  const onApply = vi.fn();
  render(
    <SpellingResultView
      check={result}
      doc={doc}
      draftChanges={new Map()}
      canManage
      onApply={onApply}
    />,
  );
  return onApply;
}
test("lexical guesses require source review and offer no apply action", () => {
  const apply = show({
    ...check,
    withheld_suggestions: [
      {
        ...suggestion,
        replacement: "huyên",
        review_reason: "source_image_required",
      },
    ],
  });
  expect(
    screen.getByRole("note", { name: "Cần đối chiếu ảnh gốc" }),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Áp dụng vào nháp" })).toBeNull();
  expect(screen.queryByText(/Không có đề xuất trong lần kiểm tra/)).toBeNull();
  expect(apply).not.toHaveBeenCalled();
});
test("a contextual proposal displays the complete phrase after correction", () => {
  show({ ...check, suggestions: [suggestion] });
  expect(screen.getByText("bệnh viện cơ bản", { exact: false })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Áp dụng vào nháp" })).toBeTruthy();
});
test("old stored checks remain readable without claiming context or image verification", () => {
  show(check);
  expect(screen.getByText(/Không có đề xuất trong lần kiểm tra/)).toBeTruthy();
  expect(screen.getByText(/chưa đối chiếu ảnh gốc/)).toBeTruthy();
});
