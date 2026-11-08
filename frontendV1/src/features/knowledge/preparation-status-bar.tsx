import { Link } from "@tanstack/react-router";
import { AlertCircle, CheckCircle2, Loader2, X } from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { usePreparationIntentsQuery } from "./preparation-queries";
import {
  formatPreparationError,
  isPreparationActive,
  preparationStatusHint,
  preparationStatusLabel,
} from "./preparation-schemas";

export function PreparationStatusBar({
  workspaceId,
  collectionId,
  sourceId,
  onOpen,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  onOpen: () => void;
}) {
  const query = usePreparationIntentsQuery(workspaceId, collectionId, sourceId);
  const [dismissedId, setDismissedId] = useState<string | null>(null);
  const latest = query.data?.[0] ?? null;
  if (!latest || latest.id === dismissedId || latest.status === "cancelled") {
    return null;
  }

  const dismissButton = (
    <Button
      type="button"
      size="sm"
      variant="ghost"
      className="size-7 shrink-0 p-0 text-muted-foreground hover:text-foreground"
      onClick={() => setDismissedId(latest.id)}
      aria-label="Ẩn thông báo chuẩn bị nội dung"
    >
      <X className="size-3.5" />
    </Button>
  );

  if (latest.status === "ready") {
    return (
      <Alert variant="success" className="py-2.5">
        <CheckCircle2 className="size-4" />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <AlertTitle className="text-xs">Bản nháp đã sẵn sàng</AlertTitle>
            <AlertDescription className="mt-0.5 text-[11px]">
              Tạo từ tệp v{latest.revision_no}. Xem và quyết định đăng ký ở bước
              tiếp theo.
            </AlertDescription>
          </div>
          <div className="flex items-center gap-1.5">
            {latest.compilation_run_id ? (
              <Button
                asChild
                size="sm"
                variant="outline"
                className="h-7 text-xs"
              >
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                  params={{
                    workspaceId,
                    collectionId,
                    runId: latest.compilation_run_id,
                  }}
                >
                  Mở bản nháp
                </Link>
              </Button>
            ) : null}
            {dismissButton}
          </div>
        </div>
      </Alert>
    );
  }

  if (latest.status === "failed" || latest.status === "uncertain") {
    return (
      <Alert variant="destructive" className="py-2.5">
        <AlertCircle className="size-4" />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <AlertTitle className="text-xs">
              {`${preparationStatusLabel(latest.status)} · Tệp v${latest.revision_no}`}
            </AlertTitle>
            <AlertDescription className="mt-0.5 text-[11px]">
              {formatPreparationError(latest.error_code)}
            </AlertDescription>
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={onOpen}
            >
              Xem
            </Button>
            {dismissButton}
          </div>
        </div>
      </Alert>
    );
  }

  if (!isPreparationActive(latest)) return null;

  return (
    <Alert variant="info" className="py-2.5">
      <Loader2 className="size-4 animate-spin" />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <AlertTitle className="text-xs">
            {preparationStatusLabel(latest.status)} · Tệp v{latest.revision_no}
          </AlertTitle>
          <AlertDescription className="mt-0.5 text-[11px]">
            {preparationStatusHint(latest.status)}
          </AlertDescription>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-7 text-xs"
          onClick={onOpen}
        >
          Xem tiến độ
        </Button>
      </div>
    </Alert>
  );
}
