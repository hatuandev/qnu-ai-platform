import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  Cpu,
  Download,
  Eye,
  FilePlus2,
  FileText,
  Info,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/app/api/v1";
import { ErrorState } from "@/components/admin/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { canManageKnowledge } from "@/features/knowledge/permissions";
import {
  downloadSourceRevision,
  useCollectionQuery,
  useRevisionsQuery,
  useSourceQuery,
} from "@/features/knowledge/queries";
import { RevisionUploadDialog } from "@/features/knowledge/revision-upload-dialog";
import {
  formatBytes,
  formatSourceStatus,
  isDocx,
  isPdf,
} from "@/features/knowledge/schemas";
import type { KBRevision } from "@/features/knowledge/types";
import { LifecycleActions } from "@/features/lifecycle/lifecycle-actions";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";

export interface SourceDetailSearchParams {
  revisionId?: string;
  runId?: string;
  checkId?: string;
  page?: number;
  tab?: "preview" | "ocr";
  subTab?: "runs" | "comparison" | "review" | "artifacts";
}

export function SourceDetailPage({
  workspaceId,
  collectionId,
  sourceId,
  search,
  onSearchChange,
}: {
  workspaceId: string;
  collectionId: string;
  sourceId: string;
  search?: SourceDetailSearchParams;
  onSearchChange?: (params: Partial<SourceDetailSearchParams>) => void;
}) {
  const navigate = useNavigate();
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const sourceQuery = useSourceQuery(workspaceId, collectionId, sourceId);
  const revisionsQuery = useRevisionsQuery(workspaceId, collectionId, sourceId);

  const [uploadRevisionOpen, setUploadRevisionOpen] = useState(false);
  const [selectedRevisionId, setSelectedRevisionId] = useState<string | null>(
    search?.revisionId ?? null,
  );
  const [copiedHash, setCopiedHash] = useState<string | null>(null);

  // PDF Preview Blob state
  const [previewBlobUrl, setPreviewBlobUrl] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [downloadingRevisionId, setDownloadingRevisionId] = useState<
    string | null
  >(null);

  const canManage = !rolePending && canManageKnowledge(role);
  const collection = collectionQuery.data;
  const source = sourceQuery.data;
  const revisions = revisionsQuery.data ?? [];

  // Deep-link migration: if old URL accessed ?tab=ocr, redirect immediately to dedicated OCR page
  useEffect(() => {
    if (search?.tab === "ocr") {
      void navigate({
        to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr",
        params: { workspaceId, collectionId, sourceId },
        search: {
          revisionId: search.revisionId,
          runId: search.runId,
          checkId: search.checkId,
          page: search.page,
          subTab: search.subTab,
        },
        replace: true,
      });
    }
  }, [search, navigate, workspaceId, collectionId, sourceId]);

  // Determine active revision for preview (defaults to selected or latest in list)
  const activeRevision: KBRevision | undefined =
    revisions.find((r) => r.id === selectedRevisionId) ?? revisions[0];

  const activeRevisionId = activeRevision?.id;
  const activeRevisionContentType = activeRevision?.content_type;
  const activeRevisionFileName = activeRevision?.file_name;

  // Load PDF Blob preview when active revision changes (if PDF)
  useEffect(() => {
    if (!activeRevisionId) return;

    if (!isPdf(activeRevisionContentType, activeRevisionFileName)) {
      setPreviewBlobUrl(null);
      setPreviewLoading(false);
      setPreviewError(null);
      return;
    }

    let isSubscribed = true;
    setPreviewLoading(true);
    setPreviewError(null);

    downloadSourceRevision(
      workspaceId,
      collectionId,
      sourceId,
      activeRevisionId,
    )
      .then((response) => {
        if (!isSubscribed) return;
        const objectUrl = URL.createObjectURL(response.blob);
        setPreviewBlobUrl(objectUrl);
        setPreviewLoading(false);
      })
      .catch((error) => {
        if (!isSubscribed) return;
        setPreviewLoading(false);
        setPreviewError(
          error instanceof ApiProblemError
            ? error.message
            : "Không tải được bản xem trước của tệp PDF này.",
        );
      });

    return () => {
      isSubscribed = false;
      setPreviewBlobUrl((previousUrl) => {
        if (previousUrl) URL.revokeObjectURL(previousUrl);
        return null;
      });
    };
  }, [
    workspaceId,
    collectionId,
    sourceId,
    activeRevisionId,
    activeRevisionContentType,
    activeRevisionFileName,
  ]);

  const handleCopyHash = async (hash: string) => {
    try {
      await navigator.clipboard.writeText(hash);
      setCopiedHash(hash);
      toast.success("Đã sao chép SHA-256.");
      setTimeout(() => setCopiedHash(null), 2000);
    } catch {
      toast.error("Không thể sao chép vào bộ nhớ tạm.");
    }
  };

  const handleDownload = async (revision: KBRevision) => {
    setDownloadingRevisionId(revision.id);
    try {
      const response = await downloadSourceRevision(
        workspaceId,
        collectionId,
        sourceId,
        revision.id,
      );

      const downloadUrl = URL.createObjectURL(response.blob);
      const anchor = document.createElement("a");
      anchor.href = downloadUrl;
      anchor.download = response.fileName || revision.file_name;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);

      setTimeout(() => URL.revokeObjectURL(downloadUrl), 5000);
      toast.success(`Đã tải xuống ${revision.file_name}.`);
    } catch (error) {
      toast.error(
        error instanceof ApiProblemError
          ? error.message
          : "Không tải được tệp tài liệu.",
      );
    } finally {
      setDownloadingRevisionId(null);
    }
  };

  if (sourceQuery.isLoading || collectionQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (sourceQuery.isError || !source) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId"
            params={{ workspaceId, collectionId }}
            search={{ page: 1, pageSize: 20 }}
          >
            <ArrowLeft className="size-3.5" />
            Về kho tri thức
          </Link>
        </Button>
        <ErrorState
          error={sourceQuery.error}
          onRetry={() => void sourceQuery.refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-wrap">
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
          search={{ page: 1, pageSize: 20 }}
          className="hover:text-foreground transition-colors truncate max-w-[150px] sm:max-w-xs"
        >
          {collection?.name || collectionId}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-semibold text-foreground truncate max-w-[200px] sm:max-w-md">
          {source.title}
        </span>
      </div>

      {/* Source Overview & Action Card */}
      <Card className="rounded-xl shadow-2xs border-border/80">
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-2 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <FileText className="size-5 text-primary shrink-0" />
                <h1 className="type-page-title m-0 text-lg sm:text-xl font-bold truncate">
                  {source.title}
                </h1>
                <Badge variant="success" className="text-xs">
                  {formatSourceStatus(source.status)}
                </Badge>
              </div>

              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground font-mono">
                <span>{source.file_name}</span>
                <span>·</span>
                <span>{formatBytes(source.size_bytes)}</span>
                <span>·</span>
                {isPdf(source.content_type, source.file_name) ? (
                  <Badge variant="info" className="text-[10px] py-0">
                    PDF
                  </Badge>
                ) : isDocx(source.content_type, source.file_name) ? (
                  <Badge variant="secondary" className="text-[10px] py-0">
                    DOCX
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px] py-0">
                    Khác
                  </Badge>
                )}
                <span>·</span>
                <span>
                  Bản mới nhất: v{source.current_revision_no} ({source.revision_count} phiên bản)
                </span>
                <span>·</span>
                <span>
                  Bản đang phục vụ:{" "}
                  {source.serving_revision_no == null
                    ? "Chưa xuất bản"
                    : `v${source.serving_revision_no}`}
                </span>
                {source.serving_revision_no != null &&
                source.current_revision_no !== source.serving_revision_no ? (
                  <Badge variant="warning">Có bản mới đang chuẩn bị</Badge>
                ) : null}
              </div>
            </div>

            {/* Prominent Next Action & Secondary CTAs */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              <LifecycleActions
                workspaceId={workspaceId}
                kind="source"
                resourceId={sourceId}
                label={source.title}
                role={role}
              />

              <Button
                size="sm"
                variant="outline"
                className="gap-1.5 text-xs h-9"
                disabled={!canManage}
                onClick={() => setUploadRevisionOpen(true)}
                title={
                  canManage
                    ? undefined
                    : "Cần quyền admin hoặc editor để tải lên phiên bản mới"
                }
              >
                <FilePlus2 className="size-3.5" />
                <span>Tải phiên bản mới</span>
              </Button>

              {/* PRIMARY PROMINENT ACTION */}
              <Button
                asChild
                size="sm"
                className="gap-1.5 text-xs h-9 font-semibold shadow-xs"
              >
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                  params={{ workspaceId, collectionId, sourceId }}
                  search={{ revisionId: activeRevisionId }}
                >
                  <Cpu className="size-4" />
                  <span>Xử lý OCR & Hiệu đính</span>
                  <ArrowRight className="size-3.5 ml-0.5" />
                </Link>
              </Button>
            </div>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-3 border-t text-xs">
            <div>
              <p className="text-muted-foreground">Người tải lên</p>
              <p className="font-mono font-medium text-foreground truncate mt-0.5">
                {source.created_by}
              </p>
            </div>

            <div>
              <p className="text-muted-foreground">Ngày tải lên</p>
              <p className="font-medium text-foreground mt-0.5">
                {formatDateTimeValue(source.created_at)}
              </p>
            </div>

            <div>
              <p className="text-muted-foreground">Cập nhật gần nhất</p>
              <p className="font-medium text-foreground mt-0.5">
                {formatDateTimeValue(source.updated_at)}
              </p>
            </div>

            <div>
              <p className="text-muted-foreground">SHA-256 (bản hiện tại)</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span
                  className="font-mono text-foreground truncate text-[11px]"
                  title={source.sha256}
                >
                  {source.sha256.slice(0, 16)}...
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  className="size-6 p-0 text-muted-foreground hover:text-foreground"
                  onClick={() => handleCopyHash(source.sha256)}
                  title="Sao chép toàn bộ SHA-256"
                >
                  {copiedHash === source.sha256 ? (
                    <Check className="size-3 text-success" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                  <span className="sr-only">Copy</span>
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Workflow Next-Steps Guidance */}
      <Card className="rounded-xl border-primary/20 bg-primary/5 p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-xs">
          <div className="flex items-start sm:items-center gap-2.5">
            <span className="flex size-7 shrink-0 items-center justify-center rounded bg-primary text-primary-foreground font-bold">
              1
            </span>
            <div>
              <p className="font-semibold text-foreground">
                Tài liệu đã được tải lên và lưu trữ an toàn
              </p>
              <p className="text-muted-foreground">
                Bước tiếp theo: Thực hiện nhận dạng OCR (tiếng Việt), đối chiếu văn bản và rà soát lỗi chính tả trước khi biên soạn.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
            <Button asChild size="sm" className="h-8 gap-1.5 text-xs">
              <Link
                to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                params={{ workspaceId, collectionId, sourceId }}
                search={{ revisionId: activeRevisionId }}
              >
                <Cpu className="size-3.5" />
                <span>Mở OCR & Hiệu đính</span>
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="h-8 gap-1.5 text-xs">
              <Link
                to="/workspaces/$workspaceId/collections/$collectionId/compilations"
                params={{ workspaceId, collectionId }}
                search={{ page: 1, pageSize: 20 }}
              >
                <BookOpen className="size-3.5" />
                <span>Biên soạn</span>
              </Link>
            </Button>
          </div>
        </div>
      </Card>

      {/* Original Document Preview Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Bản xem trước tệp gốc: Phiên bản v{activeRevision?.revision_no ?? 1}{" "}
              ({activeRevision?.file_name})
            </h2>
            <p className="text-xs text-muted-foreground">
              Xem tệp tài liệu gốc trực tiếp trên trình duyệt hoặc tải về máy tính để mở bằng ứng dụng chuyên dụng.
            </p>
          </div>

          {activeRevision ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 text-xs h-8"
              disabled={downloadingRevisionId === activeRevision.id}
              onClick={() => handleDownload(activeRevision)}
            >
              {downloadingRevisionId === activeRevision.id ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Download className="size-3.5" />
              )}
              <span>Tải bản gốc ({activeRevision.file_name})</span>
            </Button>
          ) : null}
        </div>

        {activeRevision &&
        isPdf(activeRevision.content_type, activeRevision.file_name) ? (
          <Card className="rounded-xl shadow-2xs overflow-hidden">
            {previewLoading ? (
              <div className="p-8 space-y-4 flex flex-col items-center justify-center min-h-[400px]">
                <Loader2 className="size-8 animate-spin text-primary" />
                <p className="text-xs text-muted-foreground">
                  Đang tải nội dung bản xem trước PDF...
                </p>
              </div>
            ) : previewError ? (
              <div className="p-6">
                <Alert variant="destructive">
                  <AlertTitle>Không tải được bản xem trước</AlertTitle>
                  <AlertDescription className="text-xs mt-1">
                    {previewError}
                  </AlertDescription>
                </Alert>
                <div className="mt-4 flex justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownload(activeRevision)}
                  >
                    <Download className="size-3.5 mr-1.5" />
                    Tải tệp PDF về máy
                  </Button>
                </div>
              </div>
            ) : previewBlobUrl ? (
              <div className="flex flex-col">
                <iframe
                  src={previewBlobUrl}
                  className="w-full h-[650px] border-0 bg-muted/20"
                  title={`Xem trước ${activeRevision.file_name}`}
                />
                <div className="p-3 bg-muted/20 border-t flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    Nếu trình duyệt không hiển thị được PDF, vui lòng dùng nút tải xuống bản gốc.
                  </span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-7 text-xs"
                    onClick={() => handleDownload(activeRevision)}
                  >
                    <Download className="size-3 mr-1" />
                    Tải về máy
                  </Button>
                </div>
              </div>
            ) : null}
          </Card>
        ) : activeRevision &&
          isDocx(activeRevision.content_type, activeRevision.file_name) ? (
          <Card className="rounded-xl shadow-2xs p-6">
            <Alert className="border-info/30 bg-info/5 text-info">
              <Info className="size-4" />
              <AlertTitle className="text-sm font-semibold">
                Định dạng Microsoft Word (.docx)
              </AlertTitle>
              <AlertDescription className="text-xs mt-1 text-muted-foreground">
                Tệp tài liệu này ở định dạng Microsoft Word (.docx). Trình
                duyệt không hỗ trợ kết xuất tệp Word trực tiếp. Vui lòng tải
                xuống bản gốc để xem bằng Microsoft Word hoặc chuyển sang trang OCR để trích xuất nội dung văn bản.
              </AlertDescription>
            </Alert>

            <div className="mt-6 flex flex-col items-center justify-center p-8 border rounded-lg bg-muted/10 space-y-3">
              <FileText className="size-12 text-muted-foreground" />
              <div className="text-center">
                <p className="font-mono text-sm font-semibold text-foreground">
                  {activeRevision.file_name}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Dung lượng: {formatBytes(activeRevision.size_bytes)} · Phiên
                  bản: v{activeRevision.revision_no}
                </p>
              </div>
              <div className="flex items-center gap-2 mt-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1.5"
                  disabled={downloadingRevisionId === activeRevision.id}
                  onClick={() => handleDownload(activeRevision)}
                >
                  {downloadingRevisionId === activeRevision.id ? (
                    <Loader2 className="size-3.5 animate-spin" />
                  ) : (
                    <Download className="size-3.5" />
                  )}
                  <span>Tải tệp DOCX gốc</span>
                </Button>
                <Button asChild size="sm" className="gap-1.5">
                  <Link
                    to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                    params={{ workspaceId, collectionId, sourceId }}
                    search={{ revisionId: activeRevision.id }}
                  >
                    <Cpu className="size-3.5" />
                    <span>Trích xuất nội dung bằng OCR</span>
                  </Link>
                </Button>
              </div>
            </div>
          </Card>
        ) : (
          <Card className="rounded-xl shadow-2xs p-6">
            <div className="flex flex-col items-center justify-center p-8 space-y-3">
              <FileText className="size-10 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">
                Định dạng tệp này không hỗ trợ xem trước trên trình duyệt.
              </p>
              {activeRevision ? (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleDownload(activeRevision)}
                >
                  <Download className="size-3.5 mr-1.5" />
                  Tải tệp gốc
                </Button>
              ) : null}
            </div>
          </Card>
        )}
      </div>

      {/* Revision History Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Lịch sử phiên bản ({revisions.length})
            </h2>
            <p className="text-xs text-muted-foreground">
              Tất cả các phiên bản tệp gốc được lưu trữ bất biến. Nhấn vào một phiên bản để xem hoặc xử lý OCR.
            </p>
          </div>
        </div>

        {revisionsQuery.isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : revisionsQuery.isError ? (
          <ErrorState
            error={revisionsQuery.error}
            onRetry={() => void revisionsQuery.refetch()}
          />
        ) : (
          <Card className="rounded-xl shadow-2xs overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[12%]">Phiên bản</TableHead>
                    <TableHead className="w-[28%]">Tên tệp</TableHead>
                    <TableHead className="w-[12%]">Dung lượng</TableHead>
                    <TableHead className="w-[20%]">SHA-256</TableHead>
                    <TableHead className="w-[14%]">Người tải</TableHead>
                    <TableHead className="w-[14%]">Thời điểm</TableHead>
                    <TableHead className="w-[180px] text-right">
                      Thao tác
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {revisions.map((rev) => {
                    const isActive = activeRevision?.id === rev.id;
                    const isDownloading = downloadingRevisionId === rev.id;

                    return (
                      <TableRow
                        key={rev.id}
                        className={isActive ? "bg-muted/40 font-medium" : ""}
                      >
                        <TableCell>
                          <div className="flex items-center gap-1.5">
                            <Badge
                              variant={isActive ? "default" : "outline"}
                              className="font-mono text-xs"
                            >
                              v{rev.revision_no}
                            </Badge>
                            {rev.revision_no === source.current_revision_no ? (
                              <span className="text-[10px] text-primary font-medium">
                                (Mới nhất)
                              </span>
                            ) : null}
                          </div>
                        </TableCell>

                        <TableCell
                          className="font-mono text-xs truncate max-w-[200px]"
                          title={rev.file_name}
                        >
                          {rev.file_name}
                        </TableCell>

                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {formatBytes(rev.size_bytes)}
                        </TableCell>

                        <TableCell>
                          <div className="flex items-center gap-1">
                            <span
                              className="font-mono text-[11px] text-muted-foreground truncate max-w-[110px]"
                              title={rev.sha256}
                            >
                              {rev.sha256.slice(0, 12)}...
                            </span>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="size-6 p-0 text-muted-foreground hover:text-foreground"
                              onClick={() => handleCopyHash(rev.sha256)}
                              title="Sao chép SHA-256"
                            >
                              {copiedHash === rev.sha256 ? (
                                <Check className="size-3 text-success" />
                              ) : (
                                <Copy className="size-3" />
                              )}
                            </Button>
                          </div>
                        </TableCell>

                        <TableCell className="font-mono text-xs text-muted-foreground truncate">
                          {rev.created_by}
                        </TableCell>

                        <TableCell className="text-xs text-muted-foreground">
                          {formatDateTimeValue(rev.created_at)}
                        </TableCell>

                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              size="sm"
                              variant={isActive ? "secondary" : "ghost"}
                              className="h-7 px-2 text-xs gap-1"
                              onClick={() => {
                                setSelectedRevisionId(rev.id);
                                onSearchChange?.({
                                  revisionId: rev.id,
                                });
                              }}
                              title="Chọn phiên bản này để xem trước"
                            >
                              <Eye className="size-3 text-muted-foreground" />
                              <span className="hidden sm:inline">
                                {isActive ? "Đang xem" : "Xem"}
                              </span>
                            </Button>

                            <Button
                              asChild
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-xs gap-1 text-primary hover:text-primary"
                              title="Mở OCR với phiên bản này"
                            >
                              <Link
                                to="/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId/ocr"
                                params={{ workspaceId, collectionId, sourceId }}
                                search={{ revisionId: rev.id }}
                              >
                                <Cpu className="size-3" />
                                <span className="hidden sm:inline">OCR</span>
                              </Link>
                            </Button>

                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 px-2 text-xs gap-1"
                              disabled={isDownloading}
                              onClick={() => handleDownload(rev)}
                              title="Tải tệp gốc về máy tính"
                            >
                              {isDownloading ? (
                                <Loader2 className="size-3 animate-spin" />
                              ) : (
                                <Download className="size-3" />
                              )}
                              <span className="hidden sm:inline">Tải</span>
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </Card>
        )}
      </div>

      {/* Upload New Revision Dialog */}
      <RevisionUploadDialog
        open={uploadRevisionOpen}
        onOpenChange={setUploadRevisionOpen}
        workspaceId={workspaceId}
        collectionId={collectionId}
        sourceId={sourceId}
        sourceTitle={source.title}
      />
    </div>
  );
}
