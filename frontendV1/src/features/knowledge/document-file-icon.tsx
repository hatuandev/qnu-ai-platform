import { FileSpreadsheet, FileText, Folder, FolderOpen } from "lucide-react";
import { isDocx, isPdf } from "@/features/knowledge/schemas";
import { cn } from "@/lib/utils";

/**
 * Biểu tượng tài liệu Word (.docx / .doc) với chữ W đặc trưng và màu xanh Word.
 */
export function DocxFileIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(
        "size-4 text-blue-600 dark:text-blue-400 shrink-0",
        className,
      )}
      aria-label="Tệp Word (.docx)"
      role="img"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <path d="m9 12.5 1.2 5 1.8-4.5 1.8 4.5 1.2-5" strokeWidth="2.2" />
    </svg>
  );
}

/**
 * Biểu tượng tài liệu PDF với chữ P đặc trưng và màu đỏ Acrobat.
 */
export function PdfFileIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(
        "size-4 text-rose-600 dark:text-rose-400 shrink-0",
        className,
      )}
      aria-label="Tệp PDF"
      role="img"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <path d="M10 12h2a1.5 1.5 0 0 1 0 3h-2v3.5" strokeWidth="2.2" />
    </svg>
  );
}

/**
 * Biểu tượng bảng tính Excel (.xlsx / .csv) với màu xanh lá đặc trưng.
 */
export function ExcelFileIcon({ className }: { className?: string }) {
  return (
    <FileSpreadsheet
      className={cn(
        "size-4 text-emerald-600 dark:text-emerald-400 shrink-0",
        className,
      )}
      aria-label="Bảng tính Excel"
    />
  );
}

/**
 * Biểu tượng thư mục với màu vàng hổ phách (amber) ấm áp và nắp mở / đóng.
 */
export function FolderItemIcon({
  className,
  open = false,
}: {
  className?: string;
  open?: boolean;
}) {
  if (open) {
    return (
      <FolderOpen
        className={cn(
          "size-4 text-amber-500 fill-amber-500/20 shrink-0",
          className,
        )}
        aria-label="Thư mục đang mở"
      />
    );
  }
  return (
    <Folder
      className={cn(
        "size-4 text-amber-500 fill-amber-500/20 shrink-0",
        className,
      )}
      aria-label="Thư mục"
    />
  );
}

/**
 * Component tự động phân giải icon tài liệu theo content_type hoặc tên tệp.
 */
export function DocumentTypeIcon({
  contentType,
  fileName,
  className,
}: {
  contentType?: string;
  fileName?: string;
  className?: string;
}) {
  const isDocxFile = isDocx(contentType, fileName);
  const isPdfFile = isPdf(contentType, fileName);
  const isExcel =
    (fileName?.toLowerCase().endsWith(".xlsx") ||
      fileName?.toLowerCase().endsWith(".xls") ||
      fileName?.toLowerCase().endsWith(".csv") ||
      contentType?.includes("spreadsheet") ||
      contentType?.includes("excel")) ??
    false;

  if (isDocxFile) {
    return <DocxFileIcon className={className} />;
  }
  if (isPdfFile) {
    return <PdfFileIcon className={className} />;
  }
  if (isExcel) {
    return <ExcelFileIcon className={className} />;
  }
  return (
    <FileText
      className={cn("size-4 text-primary shrink-0", className)}
      aria-label="Tệp tài liệu"
    />
  );
}

/**
 * Lấy nhãn, lớp màu nền badge và lớp hộp chứa icon để hiển thị đồng bộ.
 */
export function getDocumentFormatInfo(
  contentType?: string,
  fileName?: string,
) {
  const isDocxFile = isDocx(contentType, fileName);
  const isPdfFile = isPdf(contentType, fileName);
  const isExcel =
    (fileName?.toLowerCase().endsWith(".xlsx") ||
      fileName?.toLowerCase().endsWith(".xls") ||
      fileName?.toLowerCase().endsWith(".csv") ||
      contentType?.includes("spreadsheet") ||
      contentType?.includes("excel")) ??
    false;

  if (isDocxFile) {
    return {
      type: "docx" as const,
      label: "DOCX",
      badgeClass:
        "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/25",
      containerClass:
        "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-950/40 dark:border-blue-800",
    };
  }

  if (isPdfFile) {
    return {
      type: "pdf" as const,
      label: "PDF",
      badgeClass:
        "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/25",
      containerClass:
        "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950/40 dark:border-rose-800",
    };
  }

  if (isExcel) {
    return {
      type: "excel" as const,
      label: "XLSX",
      badgeClass:
        "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25",
      containerClass:
        "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800",
    };
  }

  return {
    type: "generic" as const,
    label: "FILE",
    badgeClass: "bg-muted text-muted-foreground border-border",
    containerClass: "bg-muted/40 text-primary border-border",
  };
}

