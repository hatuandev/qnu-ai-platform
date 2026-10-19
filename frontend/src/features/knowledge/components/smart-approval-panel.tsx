import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { SmartApprovalResult } from "@/types/knowledge";

export function SmartApprovalPanel({
  disabled,
  onApprove,
  onError,
  onBusyChange,
}: {
  disabled: boolean;
  onApprove: () => Promise<SmartApprovalResult>;
  onError: (error: unknown) => void;
  onBusyChange?: (isBusy: boolean) => void;
}) {
  const inFlight = useRef(false);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<SmartApprovalResult | null>(null);
  const handleApprove = async () => {
    if (disabled || inFlight.current) return;
    inFlight.current = true;
    setIsRunning(true);
    onBusyChange?.(true);
    setResult(null);
    try {
      setResult(await onApprove());
    } catch (error: unknown) {
      onError(error);
    } finally {
      inFlight.current = false;
      setIsRunning(false);
      onBusyChange?.(false);
    }
  };
  return (
    <section
      className="space-y-3 rounded-xl border p-3 shadow-2xs"
      aria-label="Chấp thuận tài liệu"
    >
      <p>
        Kiểm tra tự động và ghi một quyết định chấp thuận nếu đủ điều kiện. Bạn
        không cần xác nhận riêng từng mục đã được kiểm chứng theo chính sách.
      </p>
      <Button
        type="button"
        disabled={disabled || isRunning}
        onClick={handleApprove}
      >
        {isRunning
          ? "Đang kiểm tra tài liệu và các quan hệ ngữ nghĩa..."
          : "Chấp thuận (Approve)"}
      </Button>
      {isRunning && (
        <p role="status">Đang kiểm tra tài liệu và các quan hệ ngữ nghĩa...</p>
      )}
      {result && (
        <div role={result.approved ? "status" : "alert"} className="space-y-2">
          <p className="font-medium">{result.message}</p>
          <p>
            {result.validation.auto_verified_count} mục được tự xác minh;{" "}
            {result.validation.source_limitation_count} giới hạn nguồn được nhận
            diện.{" "}
            {result.approved
              ? "Đã lưu quyết định."
              : "Chưa ghi quyết định chấp thuận."}
          </p>
          {result.blockers.length > 0 && (
            <details>
              <summary className="cursor-pointer">Xem vấn đề cần xử lý</summary>
              <ul className="list-disc space-y-1 pl-5">
                {result.blockers.map((item, index) => (
                  <li key={`${item.reason_code}:${item.issue_id ?? index}`}>
                    {item.message}{" "}
                    <span className="text-muted-foreground">
                      ({item.reason_code})
                    </span>
                  </li>
                ))}
              </ul>
            </details>
          )}
          <details>
            <summary className="cursor-pointer">
              Kết quả kiểm tra và giới hạn nguồn
            </summary>
            <p>
              Chính sách: {result.validation.policy_id} /{" "}
              {result.validation.policy_version}
            </p>
            {result.validation.cells.map((cell) => (
              <p key={`${cell.row_unit_id}:${cell.column_id}`}>
                {cell.message} · Giá trị gốc: “{cell.raw}”
              </p>
            ))}
            {result.validation.issues.map((issue) => (
              <p className="break-all" key={issue.issue_id}>
                {issue.issue_id}: {issue.result} · {issue.reason_code}
              </p>
            ))}
          </details>
        </div>
      )}
    </section>
  );
}
