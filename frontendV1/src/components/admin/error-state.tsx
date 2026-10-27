import { AlertCircle, RefreshCw, ShieldAlert } from "lucide-react";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const KIND_TITLES: Record<string, string> = {
  unauthorized: "Phiên đã hết hạn",
  forbidden: "Không đủ quyền",
  not_found: "Không tìm thấy",
  conflict: "Xung đột dữ liệu",
  invalid: "Dữ liệu không hợp lệ",
  server: "Lỗi máy chủ",
  network: "Không kết nối được",
  unexpected: "Yêu cầu thất bại",
};

/**
 * Honest failure surface for v1 screens.
 *
 * A 403/404 is never rendered as an empty list and never replaced with sample
 * data; the backend code and correlation id stay visible so a failure can be
 * traced in backendV1 logs.
 */
export function ErrorState({
  error,
  title,
  description,
  onRetry,
  className,
}: {
  error: unknown;
  title?: string;
  description?: string;
  onRetry?: () => void;
  className?: string;
}) {
  const problem = error instanceof ApiProblemError ? error : null;
  const heading =
    title ?? KIND_TITLES[problem?.kind ?? "unexpected"] ?? "Yêu cầu thất bại";
  const message =
    description ??
    (error instanceof Error ? error.message : "Đã xảy ra lỗi không xác định.");
  const isPermission = problem?.kind === "forbidden";

  return (
    <Alert
      variant={isPermission ? "warning" : "destructive"}
      className={cn("items-start", className)}
    >
      {isPermission ? (
        <ShieldAlert className="size-4" />
      ) : (
        <AlertCircle className="size-4" />
      )}
      <AlertTitle>{heading}</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        {problem ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-current/80">
            <span>HTTP {problem.status || "—"}</span>
            <span>code: {problem.code}</span>
            {problem.correlationId ? (
              <span>correlation: {problem.correlationId}</span>
            ) : null}
          </div>
        ) : null}
        {onRetry ? (
          <Button
            size="sm"
            variant="outline"
            className="mt-3 gap-1.5 text-xs"
            onClick={onRetry}
          >
            <RefreshCw className="size-3.5" />
            <span>Thử lại</span>
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
