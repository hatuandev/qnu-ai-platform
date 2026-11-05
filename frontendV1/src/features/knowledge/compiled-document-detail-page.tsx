import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookMarked,
  CheckCircle2,
  ChevronRight,
  Clock,
  ExternalLink,
  History,
  Layers,
  Plus,
  RefreshCw,
} from "lucide-react";
import { useEffect, useState } from "react";
import { ApiProblemError } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
  useCompiledVersionsQuery,
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
        return "Không tìm thấy tài liệu biên soạn trong bộ sưu tập này. Kiểm tra lại đường dẫn hoặc quyền truy cập.";
      case "network_unreachable":
      case "request_aborted":
        return "Không kết nối được backendV1. Kiểm tra dịch vụ đang chạy ở cổng 8002.";
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
  const versionsQuery = useCompiledVersionsQuery(
    workspaceId,
    collectionId,
    documentId,
    pageSize,
    (page - 1) * pageSize,
    { lookahead: true },
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
  const versions = (versionsQuery.data ?? []).slice(0, pageSize);
  const history = (historyQuery.data ?? []).slice(0, pageSize);

  const availability = useSearchAvailability(
    workspaceId,
    collectionId,
    documentId,
    published?.version,
  );

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
            <span>Không tìm thấy tài liệu biên soạn</span>
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
                <Badge
                  variant="outline"
                  className="font-mono text-xs bg-muted/40 text-muted-foreground"
                >
                  key: {doc.document_key}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                ID: {doc.id}
              </p>
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
                    <span>Thêm phiên bản từ Compiler</span>
                  </Link>
                </Button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 pt-2 border-t text-xs text-muted-foreground">
            <div>
              Thứ tự thay đổi:{" "}
              <span className="font-mono font-semibold text-foreground">
                seq #{doc.change_sequence}
              </span>
            </div>
            <div>
              Tạo bởi:{" "}
              <span className="font-mono text-foreground">
                {doc.created_by}
              </span>
            </div>
            <div>
              Ngày tạo:{" "}
              <span className="text-foreground">
                {formatDateTimeValue(doc.created_at)}
              </span>
            </div>
          </div>
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
                  Phiên bản đang phát hành hiện hành
                </span>
                <Badge
                  variant="default"
                  className="text-xs bg-success text-success-foreground font-semibold"
                >
                  Đã phát hành · v{published.version.version_no}
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                Được phê duyệt và phát hành bởi{" "}
                <span className="font-mono text-foreground font-medium">
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
                  <span>Xem bản phát hành</span>
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
          {versionsQuery.isLoading ? (
            <Skeleton className="h-48 w-full rounded-xl" />
          ) : versionsQuery.isError ? (
            <ErrorState
              error={versionsQuery.error}
              onRetry={() => void versionsQuery.refetch()}
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
                    <TableHead className="text-xs font-semibold w-32">
                      Trạng thái
                    </TableHead>
                    <TableHead className="text-xs font-semibold">
                      Compiler Run & Hashes
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
                        </TableCell>

                        <TableCell className="py-3 text-xs">
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <Link
                                to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                                params={{
                                  workspaceId,
                                  collectionId,
                                  runId: ver.compilation_run_id,
                                }}
                                className="font-mono text-primary hover:underline inline-flex items-center gap-1"
                              >
                                <span>{ver.compilation_run_id}</span>
                                <ExternalLink className="size-2.5" />
                              </Link>
                            </div>
                            <div className="text-[11px] font-mono text-muted-foreground truncate max-w-xs sm:max-w-md">
                              bundle: {ver.bundle_sha256}
                            </div>
                          </div>
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
            hasNext={
              !versionsQuery.isError &&
              (versionsQuery.data?.length ?? 0) > pageSize
            }
            disabled={versionsQuery.isFetching}
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
                      Seq (#)
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
                          <div className="flex items-center gap-3 text-[11px] text-muted-foreground font-mono flex-wrap">
                            <span>Actor: {dec.actor_ref}</span>
                            <span>Version: {dec.version_id}</span>
                            <span>Decision: {dec.id}</span>
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
