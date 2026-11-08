import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookMarked,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  ExternalLink,
  History,
  Layers,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { ApiProblemError } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DocumentReplacement } from "@/features/lifecycle/document-replacement";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { isLifecycleAdmin } from "@/features/lifecycle/permissions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { cn } from "@/lib/utils";
import { ListPagination } from "./list-pagination";
import {
  canPublishCompiledVersion,
  canRegisterCompiledDocument,
} from "./permissions";
import {
  useCompiledDocumentHistoryQuery,
  useCompiledDocumentQuery,
  usePublishedCompiledDocumentQuery,
} from "./publication-queries";
import {
  formatDecisionAction,
  formatPublicationStatus,
} from "./publication-schemas";
import { useCollectionQuery } from "./queries";
import {
  SearchAvailability,
  useSearchAvailability,
} from "./search-availability";
import { ServingReferencesCard } from "./serving-references";
import { useCompiledDocumentSummaryQuery } from "./summary-queries";
import { READINESS_LABELS } from "./summary-schemas";

/**
 * Explains a failed published-version read without pretending the document has
 * no publication. The message names the actual boundary that failed.
 */
export function describePublishedReadError(error: unknown): string {
  if (error instanceof ApiProblemError) {
    switch (error.code) {
      case "resource_unavailable":
      case "storage_unavailable":
        return "Kho lưu trữ bản xuất bản đang không khả dụng. Đây là lỗi hệ thống, không phải tài liệu thiếu phiên bản.";
      case "workspace_access_denied":
      case "collection_access_denied":
      case "permission_denied":
        return "Bạn không có quyền đọc trạng thái xuất bản của tài liệu này.";
      case "compiled_document_not_found":
        return "Không tìm thấy tài liệu xuất bản trong kho này. Kiểm tra lại đường dẫn hoặc quyền truy cập.";
      case "network_unreachable":
      case "request_aborted":
        return "Không kết nối được máy chủ. Kiểm tra kết nối rồi thử lại; nếu vẫn lỗi, báo quản trị viên.";
      default:
        return error.message;
    }
  }
  return error instanceof Error
    ? error.message
    : "Không tải được thông tin phiên bản đang xuất bản.";
}

export function CompiledDocumentDetailPage({
  workspaceId,
  collectionId,
  documentId,
  page = 1,
  pageSize = 20,
  initialTab = "versions",
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  page?: number;
  pageSize?: number;
  initialTab?: "versions" | "history";
  onSearchChange?: (patch: {
    page?: number;
    pageSize?: number;
    tab?: "versions" | "history";
  }) => void;
}) {
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const [currentTab, setCurrentTab] = useState<"versions" | "history">(
    initialTab,
  );
  useEffect(() => setCurrentTab(initialTab), [initialTab]);

  const canRegister = !rolePending && canRegisterCompiledDocument(role);
  const canPublish = !rolePending && canPublishCompiledVersion(role);

  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const documentQuery = useCompiledDocumentQuery(
    workspaceId,
    collectionId,
    documentId,
  );
  const publishedQuery = usePublishedCompiledDocumentQuery(
    workspaceId,
    collectionId,
    documentId,
  );
  const historyQuery = useCompiledDocumentHistoryQuery(
    workspaceId,
    collectionId,
    documentId,
    pageSize,
    (page - 1) * pageSize,
    { lookahead: true },
  );

  const collection = collectionQuery.data;
  const doc = documentQuery.data;
  const published = publishedQuery.data;
  const history = (historyQuery.data ?? []).slice(0, pageSize);

  const availability = useSearchAvailability(
    workspaceId,
    collectionId,
    documentId,
    published?.version,
  );
  const summaryQuery = useCompiledDocumentSummaryQuery(
    workspaceId,
    collectionId,
    documentId,
    page,
    pageSize,
    { isActiveTask: availability.isUpdating },
  );
  const summary = summaryQuery.data;
  const versions = summary?.versions.items ?? [];
  const versionsTotal = summary?.versions.meta.total ?? 0;

  // The sync query is the only active-task signal; when it reaches a terminal
  // state, fetch the summary once more so readiness is not left mid-flight.
  const wasIndexTaskActive = useRef(false);
  const refetchSummary = summaryQuery.refetch;
  useEffect(() => {
    if (availability.isUpdating) {
      wasIndexTaskActive.current = true;
      return;
    }
    if (!wasIndexTaskActive.current) return;
    wasIndexTaskActive.current = false;
    void refetchSummary();
  }, [availability.isUpdating, refetchSummary]);

  if (documentQuery.isLoading || collectionQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (documentQuery.isError || !doc) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId"
            params={{ workspaceId, collectionId }}
            search={{ page: 1, pageSize: 20, tab: "documents" }}
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại kho tri thức</span>
          </Link>
        </Button>
        <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-5 text-xs space-y-2">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="size-4 shrink-0" />
            <span>Không tìm thấy tài liệu xuất bản</span>
          </div>
          <p className="text-muted-foreground">
            Tài liệu không tồn tại hoặc bạn không có quyền truy cập.
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
        <Link
          to="/workspaces/$workspaceId"
          params={{ workspaceId }}
          className="hover:text-foreground transition-colors"
        >
          Workspace
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections"
          params={{ workspaceId }}
          search={{ page: 1, pageSize: 20 }}
          className="hover:text-foreground transition-colors"
        >
          Kho tri thức
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId"
          params={{ workspaceId, collectionId }}
          search={{ page: 1, pageSize: 20, tab: "documents" }}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {collection?.name ?? "Kho tri thức"}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-medium text-foreground truncate max-w-[200px]">
          {doc.title}
        </span>
      </div>

      {/* Document Header Card */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <BookMarked className="size-5 text-primary shrink-0" />
                <h1 className="text-base sm:text-xl font-bold text-foreground">
                  {doc.title}
                </h1>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <LifecycleActions
                workspaceId={workspaceId}
                kind="document"
                resourceId={documentId}
                label={doc.title}
                role={role}
              />
              {canRegister && (
                <Button asChild size="sm" className="h-8 text-xs gap-1.5">
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId"
                    params={{ workspaceId, collectionId }}
                    search={{ page: 1, pageSize: 20, tab: "compilations" }}
                  >
                    <Plus className="size-3.5" />
                    <span>Thêm phiên bản mới</span>
                  </Link>
                </Button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 pt-2 border-t text-xs text-muted-foreground">
            <div>
              Lần thay đổi:{" "}
              <span className="font-semibold text-foreground">
                {doc.change_sequence}
              </span>
            </div>
            <div>
              Tạo bởi: <span className="text-foreground">{doc.created_by}</span>
            </div>
            <div>
              Ngày tạo:{" "}
              <span className="text-foreground">
                {formatDateTimeValue(doc.created_at)}
              </span>
            </div>
          </div>

          <Collapsible>
            <CollapsibleTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-[11px] text-muted-foreground gap-1"
              >
                <ChevronDown className="size-3" />
                <span>Chi tiết kỹ thuật</span>
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 pt-1 text-[11px] text-muted-foreground font-mono">
                <span>Mã tài liệu: {doc.document_key}</span>
                <span>ID: {doc.id}</span>
                {summary ? (
                  <span>
                    Trạng thái đọc lúc:{" "}
                    {formatDateTimeValue(summary.observed_at)}
                  </span>
                ) : null}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </CardContent>
      </Card>

      {/* Active Published Version Banner */}
      {publishedQuery.isLoading ? (
        <Skeleton className="h-24 w-full rounded-xl" />
      ) : publishedQuery.isError ? (
        // A failed read is not "no publication": the operator must not be told
        // to publish again while the real status is unknown.
        <Card className="rounded-xl border-destructive/30 bg-destructive/5 shadow-2xs">
          <CardContent className="p-4 sm:p-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <AlertCircle className="size-4 text-destructive shrink-0" />
                <span className="text-xs font-semibold text-foreground">
                  Không đọc được trạng thái xuất bản
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {describePublishedReadError(publishedQuery.error)}
              </p>
              <p className="text-[11px] text-muted-foreground/80">
                Chưa thể kết luận tài liệu có phiên bản đang xuất bản hay không.
                Không xuất bản lại trước khi trạng thái được đọc thành công.
              </p>
            </div>

            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 text-xs gap-1.5 shrink-0"
              disabled={publishedQuery.isFetching}
              onClick={() => void publishedQuery.refetch()}
            >
              <RefreshCw
                className={cn(
                  "size-3.5",
                  publishedQuery.isFetching && "animate-spin",
                )}
              />
              <span>Thử lại</span>
            </Button>
          </CardContent>
        </Card>
      ) : published ? (
        <Card className="rounded-xl border-success/30 bg-success/5 shadow-2xs">
          <CardContent className="p-4 sm:p-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <CheckCircle2 className="size-4 text-success shrink-0" />
                <span className="text-xs font-semibold text-foreground">
                  Phiên bản đang xuất bản
                </span>
                <Badge
                  variant="default"
                  className="text-xs bg-success text-success-foreground font-semibold"
                >
                  Đã xuất bản · v{published.version.version_no}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Được duyệt và xuất bản bởi{" "}
                <span className="text-foreground font-medium">
                  {published.decision.actor_ref}
                </span>{" "}
                vào {formatDateTimeValue(published.decision.created_at)}.
              </p>
              <SearchAvailability state={availability} canRetry={canPublish} />
            </div>

            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <Button
                asChild
                size="sm"
                variant="outline"
                className="h-8 text-xs gap-1.5 shrink-0"
              >
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
                  params={{
                    workspaceId,
                    collectionId,
                    documentId,
                    versionId: published.version.id,
                  }}
                >
                  <span>Xem bản xuất bản</span>
                  <ArrowRight className="size-3.5" />
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="rounded-xl border-border bg-muted/20 shadow-2xs">
          <CardContent className="p-4 text-xs flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Clock className="size-4 shrink-0" />
              <span>
                Tài liệu chưa có phiên bản nào đang xuất bản. Hãy duyệt và xuất
                bản một phiên bản từ danh sách dưới đây.
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      <ServingReferencesCard
        summary={summary}
        workspaceId={workspaceId}
        collectionId={collectionId}
        documentId={documentId}
      />

      {isLifecycleAdmin(role) ? (
        <DocumentReplacement
          workspaceId={workspaceId}
          collectionId={collectionId}
          documentId={documentId}
          title={doc.title}
        />
      ) : null}

      {/* Main Tabs: Versions vs History */}
      <Tabs
        value={currentTab}
        onValueChange={(val) => {
          setCurrentTab(val as "versions" | "history");
          onSearchChange?.({ tab: val as "versions" | "history", page: 1 });
        }}
        className="space-y-4"
      >
        <div className="flex items-center justify-between border-b pb-1">
          <TabsList className="h-9">
            <TabsTrigger value="versions" className="gap-1.5 text-xs">
              <Layers className="size-3.5" />
              <span>Danh sách phiên bản</span>
            </TabsTrigger>
            <TabsTrigger value="history" className="gap-1.5 text-xs">
              <History className="size-3.5" />
              <span>Lịch sử quyết định</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Versions List */}
        <TabsContent value="versions" className="space-y-3 m-0">
          {summaryQuery.isLoading ? (
            <Skeleton className="h-48 w-full rounded-xl" />
          ) : summaryQuery.isError ? (
            <ErrorState
              error={summaryQuery.error}
              onRetry={() => void summaryQuery.refetch()}
            />
          ) : versions.length === 0 ? (
            <Card className="rounded-xl p-8 text-center text-xs text-muted-foreground">
              Chưa có phiên bản nào cho tài liệu này.
            </Card>
          ) : (
            <Card className="rounded-xl shadow-2xs overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="text-xs font-semibold w-24">
                      Phiên bản
                    </TableHead>
                    <TableHead className="text-xs font-semibold w-36">
                      Trạng thái
                    </TableHead>
                    <TableHead className="text-xs font-semibold">
                      Nguồn dẫn xuất
                    </TableHead>
                    <TableHead className="text-xs font-semibold">
                      Lần chuẩn bị nội dung
                    </TableHead>
                    <TableHead className="text-xs font-semibold text-right w-44">
                      Thời điểm tạo
                    </TableHead>
                    <TableHead className="w-20 text-right" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {versions.map((ver) => {
                    const statusInfo = formatPublicationStatus(ver.status);
                    const isPublished =
                      ver.id === summary?.published_version?.id;
                    return (
                      <TableRow
                        key={ver.id}
                        className="hover:bg-muted/40 transition-colors"
                      >
                        <TableCell className="py-3 font-semibold text-xs">
                          <Badge
                            variant="outline"
                            className="font-mono text-xs"
                          >
                            v{ver.version_no}
                          </Badge>
                        </TableCell>

                        <TableCell className="py-3">
                          <Badge
                            variant="outline"
                            className={`text-xs ${statusInfo.badgeClass}`}
                          >
                            {statusInfo.label}
                          </Badge>
                          {isPublished && summary ? (
                            <div className="mt-1 flex flex-wrap items-center gap-1">
                              <Badge
                                variant="outline"
                                className="text-[10px] font-normal"
                              >
                                {READINESS_LABELS[summary.readiness.status]}
                              </Badge>
                              {summary.served_version?.id === ver.id ? (
                                <Badge
                                  variant="outline"
                                  className="text-[10px] font-normal border-success/40 text-success"
                                >
                                  Đang phục vụ
                                </Badge>
                              ) : null}
                            </div>
                          ) : null}
                        </TableCell>

                        <TableCell className="py-3 text-xs">
                          {ver.origins.length === 0 ? (
                            <span className="text-muted-foreground">
                              Không còn nguồn hiển thị
                            </span>
                          ) : (
                            <div
                              className="flex flex-wrap items-center gap-1"
                              title={ver.origins
                                .map(
                                  (origin) =>
                                    `${origin.source_title} · v${origin.revision_no}`,
                                )
                                .join("\n")}
                            >
                              {ver.origins.slice(0, 2).map((origin) => (
                                <Badge
                                  key={origin.revision_id}
                                  variant="secondary"
                                  className="max-w-[180px] truncate text-[11px] font-normal"
                                >
                                  {origin.source_title} · v{origin.revision_no}
                                </Badge>
                              ))}
                              {ver.origins.length > 2 ? (
                                <Badge
                                  variant="outline"
                                  className="text-[11px] font-normal"
                                >
                                  +{ver.origins.length - 2} nguồn
                                </Badge>
                              ) : null}
                            </div>
                          )}
                        </TableCell>

                        <TableCell className="py-3 text-xs">
                          <Link
                            to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                            params={{
                              workspaceId,
                              collectionId,
                              runId: ver.compilation_run_id,
                            }}
                            className="text-primary hover:underline inline-flex items-center gap-1"
                          >
                            <span>Xem lần chuẩn bị nội dung</span>
                            <ExternalLink className="size-2.5" />
                          </Link>
                        </TableCell>

                        <TableCell className="py-3 text-right text-xs text-muted-foreground">
                          <div>{formatDateTimeValue(ver.created_at)}</div>
                          <div className="text-[11px] text-muted-foreground/70 truncate">
                            bởi {ver.created_by}
                          </div>
                        </TableCell>

                        <TableCell className="py-3 text-right">
                          <Button
                            asChild
                            size="sm"
                            variant="ghost"
                            className="h-8 px-2 text-xs"
                          >
                            <Link
                              to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId"
                              params={{
                                workspaceId,
                                collectionId,
                                documentId,
                                versionId: ver.id,
                              }}
                              title="Xem chi tiết phiên bản"
                            >
                              <ArrowRight className="size-4" />
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          )}
          <ListPagination
            page={page}
            pageSize={pageSize}
            onPageChange={
              onSearchChange ? (page) => onSearchChange({ page }) : undefined
            }
            onPageSizeChange={
              onSearchChange
                ? (pageSize) => onSearchChange({ pageSize, page: 1 })
                : undefined
            }
            hasNext={!summaryQuery.isError && page * pageSize < versionsTotal}
            disabled={summaryQuery.isFetching}
            label="phiên bản"
          />
        </TabsContent>

        {/* Tab 2: Decision History */}
        <TabsContent value="history" className="space-y-3 m-0">
          {historyQuery.isLoading ? (
            <Skeleton className="h-48 w-full rounded-xl" />
          ) : historyQuery.isError ? (
            <ErrorState
              error={historyQuery.error}
              onRetry={() => void historyQuery.refetch()}
            />
          ) : history.length === 0 ? (
            <Card className="rounded-xl p-8 text-center text-xs text-muted-foreground">
              Chưa có quyết định phê duyệt, xuất bản hoặc thu hồi nào được ghi
              nhận.
            </Card>
          ) : (
            <Card className="rounded-xl shadow-2xs overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/30">
                    <TableHead className="text-xs font-semibold w-24">
                      Lần
                    </TableHead>
                    <TableHead className="text-xs font-semibold w-36">
                      Quyết định
                    </TableHead>
                    <TableHead className="text-xs font-semibold">
                      Lý do & Chi tiết
                    </TableHead>
                    <TableHead className="text-xs font-semibold text-right w-44">
                      Thời điểm
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {history.map((dec) => {
                    const actionInfo = formatDecisionAction(dec.action);
                    return (
                      <TableRow
                        key={dec.id}
                        className="hover:bg-muted/40 transition-colors"
                      >
                        <TableCell className="py-3 font-mono text-xs">
                          <Badge
                            variant="secondary"
                            className="font-mono text-xs"
                          >
                            #{dec.document_sequence}
                          </Badge>
                        </TableCell>

                        <TableCell className="py-3">
                          <Badge
                            variant={actionInfo.variant}
                            className="text-xs font-semibold"
                          >
                            {actionInfo.label}
                          </Badge>
                        </TableCell>

                        <TableCell className="py-3 text-xs space-y-1">
                          <p className="font-medium text-foreground whitespace-pre-wrap">
                            {dec.reason}
                          </p>
                          <div
                            className="text-[11px] text-muted-foreground"
                            title={`version_id: ${dec.version_id}\ndecision_id: ${dec.id}`}
                          >
                            Người thực hiện: {dec.actor_ref}
                          </div>
                        </TableCell>

                        <TableCell className="py-3 text-right text-xs text-muted-foreground">
                          {formatDateTimeValue(dec.created_at)}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </Card>
          )}
          <ListPagination
            page={page}
            pageSize={pageSize}
            onPageChange={
              onSearchChange ? (page) => onSearchChange({ page }) : undefined
            }
            onPageSizeChange={
              onSearchChange
                ? (pageSize) => onSearchChange({ pageSize, page: 1 })
                : undefined
            }
            hasNext={
              !historyQuery.isError &&
              (historyQuery.data?.length ?? 0) > pageSize
            }
            disabled={historyQuery.isFetching}
            label="quyết định"
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
