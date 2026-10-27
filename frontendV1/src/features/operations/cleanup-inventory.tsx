import { Badge } from "@/components/ui/badge";
import { formatBytes } from "@/features/knowledge/schemas";
import { formatDateTimeValue } from "@/lib/date-utils";
import type { CleanupAction } from "./maintenance-types";
import { statusLabel } from "./types";

export function CleanupInventory({ action }: { action: CleanupAction }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap gap-2">
        <Badge variant="outline">
          {action.status === "pending"
            ? "Đã xác nhận, chưa hoàn tất"
            : statusLabel(action.status)}
        </Badge>
        <span>
          {action.files.length} tệp · {formatBytes(action.total_bytes)}
        </span>
      </div>
      <p className="text-muted-foreground">
        Tệp gốc, raw OCR và tệp còn tham chiếu được giữ lại. Mã tệp được ẩn danh
        bởi server.
      </p>
      <ul
        className="max-h-64 overflow-y-auto divide-y rounded-lg border"
        aria-label="Tệp trong bản xem trước"
      >
        {action.files.map((file) => (
          <li key={file.id} className="p-3 space-y-1">
            <p className="font-mono text-xs break-all">{file.id}</p>
            <p>
              {formatBytes(file.bytes)} ·{" "}
              {formatDateTimeValue(file.modified_at)}
            </p>
          </li>
        ))}
      </ul>
      {action.files.length === 0 ? (
        <p>Không có tệp đủ điều kiện để dọn.</p>
      ) : null}
      {action.result ? (
        <div role="status" className="space-y-1">
          <p>
            Đã xóa:{" "}
            {action.result.files.filter((f) => f.outcome === "deleted").length}{" "}
            · Đã vắng trước đó:{" "}
            {action.result.files.filter((f) => f.outcome === "absent").length}
          </p>
          {action.result.originals_and_raw_retained ? (
            <p>Tệp gốc và raw OCR được giữ lại.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
