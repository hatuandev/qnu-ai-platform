import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";

export function isDocx(fileName: string): boolean {
  return (
    fileName.toLowerCase().endsWith(".docx") ||
    fileName.toLowerCase().endsWith(".doc")
  );
}

export function isPdf(fileName: string): boolean {
  return fileName.toLowerCase().endsWith(".pdf");
}

export function isExcel(fileName: string): boolean {
  return (
    fileName.toLowerCase().endsWith(".xlsx") ||
    fileName.toLowerCase().endsWith(".xls") ||
    fileName.toLowerCase().endsWith(".csv")
  );
}

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

export function ExcelFileIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn(
        "size-4 text-emerald-600 dark:text-emerald-400 shrink-0",
        className,
      )}
      aria-label="Bảng tính Excel (.xlsx)"
      role="img"
    >
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <path d="M9 12.5l6 6" strokeWidth="2.2" />
      <path d="M15 12.5l-6 6" strokeWidth="2.2" />
    </svg>
  );
}

export function DocumentTypeIcon({
  fileName,
  className,
}: {
  fileName: string;
  className?: string;
}) {
  if (isDocx(fileName)) return <DocxFileIcon className={className} />;
  if (isPdf(fileName)) return <PdfFileIcon className={className} />;
  if (isExcel(fileName)) return <ExcelFileIcon className={className} />;
  return (
    <FileText
      className={cn("size-4 text-muted-foreground shrink-0", className)}
    />
  );
}
