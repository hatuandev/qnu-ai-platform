import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import type { IngestionReadiness } from "@/types/knowledge";

export function IngestionReadinessPanel({
  readiness,
  isReady,
  isProcessing,
  onViewMarkdown,
  onAdvanced,
  vectorAction,
}: {
  readiness?: IngestionReadiness | null;
  isReady: boolean;
  isProcessing: boolean;
  onViewMarkdown: () => void;
  onAdvanced?: () => void;
  vectorAction: ReactNode;
}) {
  const label = isProcessing
    ? "Đang xử lý tài liệu"
    : readiness?.status === "READY_WITH_LIMITATIONS"
      ? "Sẵn sàng, có giới hạn dữ liệu"
      : isReady
        ? "Sẵn sàng nạp vector"
        : "Nội dung cần kiểm tra";
  return (
    <section
      className="space-y-3 rounded-xl border bg-card p-4 text-sm shadow-2xs"
      aria-label="Trạng thái tài liệu"
    >
      <p className="font-semibold" role="status">
        {label}
      </p>
      <p className="text-muted-foreground">
        {readiness?.message ??
          (isProcessing
            ? "Hệ thống đang bóc tách, chuẩn hóa và kiểm tra nội dung."
            : isReady
              ? "Đã có nội dung để nạp vector. Chatbot chỉ sử dụng sau khi xuất bản đúng quyền."
              : "Cần kiểm tra nội dung nguồn; chi tiết đối chiếu dành cho quản trị ở phần nâng cao.")}
      </p>
      {readiness?.limitations.length ? (
        <p>
          {readiness.limitations.length} ô giữ nguyên ký hiệu và chưa dùng để
          tính toán hay kết luận giá trị.
        </p>
      ) : null}
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" variant="outline" onClick={onViewMarkdown}>
          Xem Markdown
        </Button>
        {vectorAction}
        {onAdvanced && (
          <Button type="button" variant="ghost" onClick={onAdvanced}>
            Đối chiếu nâng cao
          </Button>
        )}
      </div>
      {readiness?.blockers.length ? (
        <details>
          <summary className="cursor-pointer">
            Nội dung cần xử lý ({readiness.blockers.length})
          </summary>
          <ul className="list-disc space-y-1 pl-5">
            {Array.from(
              new Map(
                readiness.blockers.map((b) => [JSON.stringify(b), b]),
              ).values(),
            ).map((b) => (
              <li key={JSON.stringify(b)}>{b.message}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
