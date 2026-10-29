import { z } from "zod";
import type { ProcessingRunResponse } from "./ocr-types";

/** Default upload ceiling in backendV1 (Settings.MAX_UPLOAD_BYTES). */
export const MAX_UPLOAD_BYTES = 60 * 1024 * 1024; // 60 MiB

export const ALLOWED_EXTENSIONS = [".pdf", ".docx"] as const;
export const ACCEPT_UPLOAD =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export const collectionNameSchema = z
  .string()
  .trim()
  .min(1, "Tên bộ sưu tập không được để trống.")
  .max(255, "Tên bộ sưu tập tối đa 255 ký tự.");

export const collectionDescriptionSchema = z
  .string()
  .trim()
  .max(2000, "Mô tả tối đa 2000 ký tự.");

export const collectionCreateSchema = z.object({
  name: collectionNameSchema,
  description: collectionDescriptionSchema,
});

export type CollectionCreateFormValues = z.infer<typeof collectionCreateSchema>;

export const collectionUpdateSchema = z.object({
  name: collectionNameSchema,
  description: collectionDescriptionSchema,
});

export type CollectionUpdateFormValues = z.infer<typeof collectionUpdateSchema>;

export const sourceUploadSchema = z.object({
  title: z
    .string()
    .trim()
    .max(255, "Tiêu đề tối đa 255 ký tự.")
    .optional()
    .or(z.literal("")),
});

export type SourceUploadFormValues = z.infer<typeof sourceUploadSchema>;

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function formatSourceStatus(status: string): string {
  if (status === "stored") return "Đã lưu tệp";
  return status;
}

export type ProcessingStatusDescriptor = {
  label: string;
  variant:
    | "default"
    | "secondary"
    | "outline"
    | "destructive"
    | "warning"
    | "success";
  status:
    | "unprocessed"
    | "queued"
    | "running"
    | "completed"
    | "failed"
    | "uncertain";
};

export function formatProcessingStatus(
  processing?: ProcessingRunResponse | null,
): ProcessingStatusDescriptor {
  if (!processing) {
    return {
      label: "Đã lưu · Chưa bóc tách",
      variant: "secondary",
      status: "unprocessed",
    };
  }

  if (processing.status === "queued" || processing.dispatch_pending) {
    return {
      label: "Chờ xử lý",
      variant: "outline",
      status: "queued",
    };
  }

  if (processing.status === "running") {
    const pagesTotal = processing.pages_total;
    const pagesDone = processing.pages_done ?? 0;
    const label =
      pagesTotal && pagesTotal > 0
        ? `Đang bóc tách (${pagesDone}/${pagesTotal} trang)`
        : "Đang bóc tách…";
    return {
      label,
      variant: "default",
      status: "running",
    };
  }

  if (processing.status === "completed") {
    return {
      label: "Đã bóc tách",
      variant: "success",
      status: "completed",
    };
  }

  if (processing.status === "failed") {
    return {
      label: "Xử lý lỗi",
      variant: "destructive",
      status: "failed",
    };
  }

  if (processing.status === "uncertain") {
    return {
      label: "Chưa xác định kết quả",
      variant: "warning",
      status: "uncertain",
    };
  }

  return {
    label: "Đã lưu · Chưa bóc tách",
    variant: "secondary",
    status: "unprocessed",
  };
}

export function isPdf(contentType?: string, fileName?: string): boolean {
  if (contentType?.toLowerCase().includes("application/pdf")) return true;
  if (fileName?.toLowerCase().endsWith(".pdf")) return true;
  return false;
}

export function isDocx(contentType?: string, fileName?: string): boolean {
  if (
    contentType
      ?.toLowerCase()
      .includes(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      )
  ) {
    return true;
  }
  if (fileName?.toLowerCase().endsWith(".docx")) return true;
  return false;
}

export function validateUploadFile(
  file: File | undefined | null,
): string | null {
  if (!file) return "Vui lòng chọn một tệp.";
  if (file.size === 0) return "Tệp rỗng không được chấp nhận.";
  if (file.size > MAX_UPLOAD_BYTES) {
    return `Kích thước tệp vượt quá giới hạn ${formatBytes(MAX_UPLOAD_BYTES)}.`;
  }
  const name = file.name.toLowerCase();
  const validExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
  if (!validExt) {
    return "Chỉ hỗ trợ tệp định dạng PDF (.pdf) hoặc Word (.docx).";
  }
  return null;
}

/** Generate a compliant Idempotency-Key (8-128 chars). */
export function generateIdempotencyKey(prefix = "qnu-up"): string {
  const ts = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${ts}-${rand}`;
}
