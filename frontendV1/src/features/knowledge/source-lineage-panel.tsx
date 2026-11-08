import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ExternalLink,
  GitBranch,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTimeValue } from "@/lib/date-utils";
import { formatCompilationStatus } from "./compilation-schemas";
import { hasActiveSourceTask, useSourceSummaryQuery } from "./summary-queries";
import { READINESS_LABELS } from "./summary-schemas";
import type { SourceDerivation } from "./summary-types";

function DerivationRow({
  item,
  workspaceId,
  collectionId,
}: {
  item: SourceDerivation;
  workspaceId: string;
  collectionId: string;
}) {
  const statusInfo = formatCompilationStatus(item.compilation_status);
  return (
    <li className="flex flex-col gap-2 px-3 py-2.5 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 space-y-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-semibold text-foreground">
            Lần chuẩn bị #{item.compilation_generation}
          </span>
          <Badge variant={statusInfo.variant} className="text-[11px]">
            {statusInfo.label}
          </Badge>
          {item.is_serving ? (
            <Badge
              variant="outline"
              className="gap-1 text-[11px] border-success/40 text-success"
            >
              <CheckCircle2 className="size-3" />
              Đang phục vụ
            </Badge>
          ) : null}
        </div>

        {item.version ? (
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">
              v{item.version.version_no}
            </span>{" "}
            · {item.version.document_title}
            {item.readiness ? (
              <span className="text-muted-foreground/80">
                {" "}
                · {READINESS_LABELS[item.readiness.status]}
              </span>
            ) : null}
          </p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Chưa đăng ký thành phiên bản tài liệu xuất bản.
          </p>
        )}

        <p className="text-[11px] text-muted-foreground/80">
          Đọc nội dung lần #{item.ocr_generation}
          {item.text_version
            ? ` · bản văn bản v${item.text_version.version}`
            : ""}
        </p>
      </div>

      <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
          params={{
            workspaceId,
            collectionId,
            runId: item.compilation_run_id,
          }}
          className="inline-flex items-center gap-1 text-primary hover:underline"
        >
          <span>Mở bản biên soạn</span>
          <ExternalLink className="size-3" />
        </Link>
        {item.version ? (
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
            params={{
              workspaceId,
              collectionId,
              documentId: item.version.document_id,
              versionId: item.version.version_id,
            }}
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            <span>Xem phiên bản</span>
            <ExternalLink className="size-3" />
          </Link>
        ) : null}
      </div>
    </li>
  );
}

export function SourceLineagePanel({
  workspaceId,
  collectionId,
  sourceId,
  revisionId,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  revisionId: string;
}) {
  const [derivationsLimit, setDerivationsLimit] = useState(20);
  const [isOpen, setIsOpen] = useState(false);
  const summaryQuery = useSourceSummaryQuery(
    workspaceId,
    collectionId,
    sourceId,
    revisionId,
    { derivationsLimit },
  );
  const summary = summaryQuery.data;
  const serving = summary?.derivations.find((item) => item.is_serving);
  const isActive = hasActiveSourceTask(summary);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <section
        aria-label="Dẫn xuất và phục vụ của nguồn"
        className="rounded-lg border border-border/60 bg-card/60 shadow-2xs"
      >
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
          <CollapsibleTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="h-7 min-w-0 gap-2 px-1.5 text-xs font-semibold"
            >
              <GitBranch className="size-3.5 text-primary" />
              <span>Dẫn xuất & phục vụ</span>
              {summaryQuery.isLoading ? (
                <Loader2 className="size-3 animate-spin text-muted-foreground" />
              ) : null}
              {summary ? (
                <>
                  <Badge variant="outline" className="text-[11px]">
                    {summary.derivations.length} dẫn xuất
                  </Badge>
                  {serving?.version ? (
                    <Badge
                      variant="outline"
                      className="text-[11px] border-success/40 text-success"
                    >
                      Đang phục vụ v{serving.version.version_no}
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="text-[11px]">
                      Chưa có bản phục vụ
                    </Badge>
                  )}
                  {isActive ? (
                    <span className="inline-flex items-center gap-1 font-normal text-muted-foreground">
                      <Loader2 className="size-3 animate-spin" />
                      Tác vụ đang chạy
                    </span>
                  ) : null}
                </>
              ) : null}
              <ChevronDown
                className={
                  isOpen
                    ? "size-3 rotate-180 transition-transform"
                    : "size-3 transition-transform"
                }
              />
            </Button>
          </CollapsibleTrigger>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-[11px] text-muted-foreground"
            disabled={summaryQuery.isFetching}
            onClick={() => void summaryQuery.refetch()}
          >
            <RefreshCw
              className={
                summaryQuery.isFetching ? "size-3 animate-spin" : "size-3"
              }
            />
            <span>Làm mới</span>
          </Button>
        </div>

        <CollapsibleContent>
          {summaryQuery.isError ? (
            <div className="border-t border-border/60 p-3">
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  <p>Không đọc được lịch sử dẫn xuất của nguồn này.</p>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-2 h-7 text-xs"
                    onClick={() => void summaryQuery.refetch()}
                  >
                    Thử lại
                  </Button>
                </AlertDescription>
              </Alert>
            </div>
          ) : summaryQuery.isLoading ? (
            <div className="space-y-2 border-t border-border/60 p-3">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : summary && summary.derivations.length === 0 ? (
            <p className="border-t border-border/60 px-3 py-3 text-xs text-muted-foreground">
              Chưa có lần chuẩn bị nội dung nào dùng phiên bản nguồn này. Sau
              khi chuẩn bị và đăng ký, bản xuất bản cùng tình trạng phục vụ sẽ
              hiển thị tại đây.
            </p>
          ) : summary ? (
            <>
              <ul className="divide-y divide-border/60 border-t border-border/60">
                {summary.derivations.map((item) => (
                  <DerivationRow
                    key={`${item.compilation_run_id}:${item.version?.version_id ?? "none"}`}
                    item={item}
                    workspaceId={workspaceId}
                    collectionId={collectionId}
                  />
                ))}
              </ul>
              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 px-3 py-2 text-[11px] text-muted-foreground">
                <span>
                  Trạng thái tại {formatDateTimeValue(summary.observed_at)}
                </span>
                {summary.derivations_truncated ? (
                  derivationsLimit < 50 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-[11px]"
                      disabled={summaryQuery.isFetching}
                      onClick={() => setDerivationsLimit(50)}
                    >
                      Tải thêm
                    </Button>
                  ) : (
                    <span>Chỉ hiển thị 50 dẫn xuất gần nhất.</span>
                  )
                ) : null}
              </div>
            </>
          ) : null}
        </CollapsibleContent>
      </section>
    </Collapsible>
  );
}
