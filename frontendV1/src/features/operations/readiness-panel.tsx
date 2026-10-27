import { RefreshCw } from "lucide-react";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useReadiness } from "./queries";

const NAMES: Record<string, string> = {
  database: "Cơ sở dữ liệu",
  quota: "Ngân sách token",
  queue: "Hàng đợi xử lý",
  vector: "Kho tìm kiếm",
  worker: "Tiến trình xử lý",
  ocr: "Model OCR",
  chat: "Model hội thoại",
  embedding: "Model embedding",
  storage: "Kho tệp",
};
export function ReadinessPanel({ workspaceId }: { workspaceId: string }) {
  const query = useReadiness(workspaceId, true);
  return (
    <Card className="rounded-xl shadow-2xs">
      <CardHeader className="flex flex-wrap flex-row items-center justify-between gap-2">
        <CardTitle className="text-sm">Hệ thống sẵn sàng</CardTitle>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void query.refetch()}
          disabled={query.isFetching}
        >
          <RefreshCw className="size-3.5" />
          Kiểm tra lại
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {query.isPending ? (
          <p role="status">Đang kiểm tra cấu hình và kết nối…</p>
        ) : query.isError ? (
          <ErrorState
            error={query.error}
            onRetry={() => void query.refetch()}
          />
        ) : (
          <>
            <Badge variant={query.data.ready ? "success" : "warning"}>
              {query.data.ready
                ? "Cấu hình và kết nối đạt"
                : "Có thành phần chưa sẵn sàng"}
            </Badge>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(query.data.checks).map(([key, check]) => (
                <div key={key} className="rounded-lg border p-3 text-sm">
                  <div className="flex justify-between gap-2">
                    <span className="font-medium">{NAMES[key] ?? key}</span>
                    <span
                      className={check.ok ? "text-success" : "text-warning"}
                    >
                      {check.ok ? "Đạt" : "Cần xử lý"}
                    </span>
                  </div>
                  {check.code ? (
                    <p className="mt-1 break-all text-xs text-muted-foreground">
                      {check.code === "no_source_to_probe"
                        ? "Chưa có nguồn để kiểm tra đọc tệp."
                        : check.code}
                    </p>
                  ) : null}
                  {check.model ? (
                    <p className="mt-1 break-all text-xs text-muted-foreground">
                      {check.model}
                    </p>
                  ) : null}
                  {key === "quota" ? (
                    <p className="mt-1 text-xs text-muted-foreground">
                      Còn lại:{" "}
                      {check.configured === false
                        ? "Chưa cấu hình"
                        : check.remaining_tokens === null
                          ? "Không giới hạn theo cấu hình"
                          : (check.remaining_tokens ?? "Chưa xác định")}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Kiểm tra này không gọi model suy luận thật. Xác thực production:{" "}
              {query.data.production_auth_configured
                ? "Đã cấu hình"
                : "Chưa đạt"}
              . Tự giao lại tác vụ:{" "}
              {query.data.reconcile_enabled ? "Đang bật" : "Đang tắt"}.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
