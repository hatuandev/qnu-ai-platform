import { z } from "zod";
import type {
  PageStatus,
  ProcessingRunStatus,
  Suggestion,
} from "@/features/knowledge/ocr-types";

// ============================================================================
// Unicode Code Point Utilities (Strict Python Parity)
// ============================================================================

/**
 * Splits a string into an array of Unicode code points.
 * Ensures parity with Python's string indexing for characters outside BMP (e.g. emoji, ancient scripts).
 */
export function getCodePoints(text: string): string[] {
  return Array.from(text);
}

/**
 * Returns the code point length of a string (equivalent to Python `len(text)`).
 */
export function getCodePointLength(text: string): number {
  return Array.from(text).length;
}

/**
 * Slices a string by Unicode code point boundaries (0-indexed, end exclusive).
 */
export function sliceByCodePoints(
  text: string,
  start: number,
  end: number,
): string {
  const points = Array.from(text);
  if (start < 0 || end < start || start > points.length) return "";
  return points.slice(start, end).join("");
}

/**
 * Replaces a span by Unicode code points.
 */
export function replaceSpanByCodePoints(
  text: string,
  start: number,
  end: number,
  replacement: string,
): string {
  const points = Array.from(text);
  if (start < 0 || end < start || start > points.length) return text;
  return (
    points.slice(0, start).join("") + replacement + points.slice(end).join("")
  );
}

/**
 * Validates whether a suggestion's start/end span matches its `original` string
 * in the target text using Unicode code points.
 */
export function validateSuggestionSpan(
  text: string,
  suggestion: Pick<Suggestion, "start" | "end" | "original">,
): boolean {
  const points = Array.from(text);
  if (
    suggestion.start < 0 ||
    suggestion.end <= suggestion.start ||
    suggestion.end > points.length
  ) {
    return false;
  }
  const extracted = points.slice(suggestion.start, suggestion.end).join("");
  return extracted === suggestion.original;
}

/**
 * Applies multiple non-overlapping suggestions to a text unit by sorting
 * in descending order of `start` offset, preserving code point coordinates.
 */
export function applySuggestionsToText(
  text: string,
  suggestions: Suggestion[],
): {
  updatedText: string;
  appliedCount: number;
  skippedCount: number;
  error?: string;
} {
  if (suggestions.length === 0) {
    return { updatedText: text, appliedCount: 0, skippedCount: 0 };
  }

  // 1. Filter suggestions that currently match the text
  const validSuggestions: Suggestion[] = [];
  let skipped = 0;

  for (const s of suggestions) {
    if (validateSuggestionSpan(text, s)) {
      validSuggestions.push(s);
    } else {
      skipped++;
    }
  }

  if (validSuggestions.length === 0) {
    return {
      updatedText: text,
      appliedCount: 0,
      skippedCount: skipped,
      error: "Không có gợi ý nào khớp với văn bản hiện hành.",
    };
  }

  // 2. Sort descending by start
  validSuggestions.sort((a, b) => b.start - a.start);

  // 3. Check for overlaps among valid suggestions
  for (let i = 0; i < validSuggestions.length - 1; i++) {
    const current = validSuggestions[i];
    const next = validSuggestions[i + 1];
    if (next.end > current.start) {
      return {
        updatedText: text,
        appliedCount: 0,
        skippedCount: suggestions.length,
        error: "Phát hiện gợi ý chồng lấn (overlapping spans).",
      };
    }
  }

  // 4. Apply replacements from end to beginning
  let currentText = text;
  let applied = 0;

  for (const s of validSuggestions) {
    currentText = replaceSpanByCodePoints(
      currentText,
      s.start,
      s.end,
      s.replacement,
    );
    applied++;
  }

  return {
    updatedText: currentText,
    appliedCount: applied,
    skippedCount: skipped,
  };
}

// ============================================================================
// Zod Schemas
// ============================================================================

export const processingRunRequestSchema = z.object({
  provider_id: z
    .string()
    .min(1, "Mã provider không được rỗng")
    .max(64, "Mã provider tối đa 64 ký tự")
    .nullable()
    .optional(),
  force: z.boolean().default(false),
});

export const textChangeSchema = z.object({
  evidence_id: z
    .string()
    .min(1, "Evidence ID không được để trống")
    .max(128, "Evidence ID tối đa 128 ký tự"),
  before: z.string().max(100000, "Văn bản trước sửa quá dài"),
  after: z
    .string()
    .max(100000, "Văn bản sau sửa quá dài")
    .refine((val) => val.trim().length > 0, {
      message: "Không được xóa hết nội dung của đoạn/ô văn bản.",
    }),
});

export const saveReviewSchema = z
  .object({
    expected_version: z
      .number()
      .int("Phiên bản phải là số nguyên")
      .min(0, "Phiên bản không hợp lệ"),
    expected_sha256: z
      .string()
      .regex(/^[0-9a-f]{64}$/, "SHA-256 phải là chuỗi hex 64 ký tự"),
    changes: z
      .array(textChangeSchema)
      .min(1, "Cần ít nhất một thay đổi để lưu")
      .max(1000, "Tối đa 1000 thay đổi trong một lần lưu"),
  })
  .refine(
    (data) => {
      const ids = new Set(data.changes.map((c) => c.evidence_id));
      return ids.size === data.changes.length;
    },
    {
      message: "Mỗi đoạn hoặc ô chỉ được sửa một lần trong yêu cầu lưu.",
      path: ["changes"],
    },
  );

export const detectRequestSchema = z
  .object({
    expected_version: z
      .number()
      .int("Phiên bản phải là số nguyên")
      .min(0, "Phiên bản không hợp lệ"),
    expected_sha256: z
      .string()
      .regex(/^[0-9a-f]{64}$/, "SHA-256 phải là chuỗi hex 64 ký tự"),
    evidence_ids: z
      .array(z.string().min(1))
      .min(1, "Chọn ít nhất 1 đoạn văn bản để kiểm tra")
      .max(100, "Tối đa 100 đoạn văn bản trong một lượt kiểm tra"),
    provider_id: z.string().min(1).max(64).nullable().optional(),
    max_output_tokens: z
      .number()
      .int()
      .positive("Budget token phải là số dương")
      .default(4096),
  })
  .refine(
    (data) => {
      const ids = new Set(data.evidence_ids);
      return ids.size === data.evidence_ids.length;
    },
    {
      message: "Danh sách đoạn kiểm tra không được chứa ID trùng lặp.",
      path: ["evidence_ids"],
    },
  );

// ============================================================================
// Helper Utilities
// ============================================================================

export { generateIdempotencyKey, isDocx } from "@/features/knowledge/schemas";

export function formatRunStatus(status: ProcessingRunStatus): {
  label: string;
  variant:
    | "default"
    | "secondary"
    | "success"
    | "destructive"
    | "warning"
    | "outline";
} {
  switch (status) {
    case "queued":
      return { label: "Đang chờ xử lý", variant: "secondary" };
    case "running":
      return { label: "Đang xử lý", variant: "default" };
    case "completed":
      return { label: "Hoàn tất", variant: "success" };
    case "failed":
      return { label: "Thất bại", variant: "destructive" };
    case "uncertain":
      return { label: "Không xác định (Hết hạn)", variant: "warning" };
    case "cancelled":
      return { label: "Đã hủy", variant: "outline" };
    default:
      return { label: status, variant: "outline" };
  }
}

export function formatPageStatus(status: PageStatus): {
  label: string;
  variant:
    | "default"
    | "secondary"
    | "success"
    | "destructive"
    | "warning"
    | "outline";
} {
  switch (status) {
    case "pending":
      return { label: "Chờ", variant: "outline" };
    case "in_flight":
      return { label: "Đang OCR", variant: "default" };
    case "completed":
      return { label: "Đạt", variant: "success" };
    case "blank":
      return { label: "Trang trắng", variant: "secondary" };
    case "failed":
      return { label: "Lỗi", variant: "destructive" };
    case "uncertain":
      return { label: "Timeout", variant: "warning" };
    default:
      return { label: status, variant: "outline" };
  }
}

export function formatOcrError(
  code?: string | null,
  detail?: string | null,
): string {
  if (!code && !detail) return "Đã xảy ra lỗi không xác định.";

  switch (code) {
    case "processing_run_active":
      return "Đang có một lượt xử lý OCR hoạt động cho phiên bản này. Vui lòng đợi hoặc tải lại.";
    case "run_not_completed":
      return "Lượt xử lý chưa hoàn tất nên chưa thể thực hiện hành động này.";
    case "run_not_ready":
      return "Lượt xử lý chưa sẵn sàng để đọc kết quả.";
    case "processing_unsupported_format":
      return detail || "Định dạng tệp này chưa được hỗ trợ xử lý OCR.";
    case "docx_layout_unsupported":
      return detail || "Không thể dựng layout cố định cho tệp DOCX này.";
    case "model_not_configured":
      return "Workspace chưa cấu hình model OCR hợp lệ trong ModelOps.";
    case "provider_not_found":
    case "provider_inactive":
      return "Nhà cung cấp AI được yêu cầu không tồn tại hoặc đã bị tắt.";
    case "ocr_provider_timeout":
      return "Quá thời gian phản hồi từ nhà cung cấp OCR (uncertain). Lượt xử lý đã dừng an toàn.";
    case "ocr_text_version_conflict":
      return "Đã có phiên bản sửa mới được lưu trên server. Vui lòng tải lại trước khi lưu.";
    case "ocr_text_source_changed":
      return "Bản sửa không khớp với OCR gốc của lượt chạy này.";
    case "ocr_text_derivative_mismatch":
      return "Tệp Markdown và JSON dẫn xuất không đồng bộ trên server.";
    case "idempotency_conflict":
      return "Mã Idempotency-Key này đã được dùng cho nội dung khác. Vui lòng không gửi lặp.";
    case "artifact_integrity_failed":
      return "Tệp dữ liệu không vượt qua kiểm tra toàn vẹn SHA-256.";
    case "storage_unavailable":
      return "Dịch vụ lưu trữ tạm thời không khả dụng.";
    case "ocr_spelling_invalid":
      return (
        detail ||
        "Gợi ý kiểm tra chính tả từ model không khớp văn bản hiện hành."
      );
    default:
      return detail || code || "Đã xảy ra lỗi trong quá trình xử lý OCR.";
  }
}
