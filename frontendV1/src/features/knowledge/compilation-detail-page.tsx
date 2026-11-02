import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  BookPlus,
  ChevronRight,
  Download,
  FileCheck2,
  FileCode,
  FileEdit,
  GitBranch,
  HelpCircle,
  Layers,
  Loader2,
  Sparkles,
  Tag,
} from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { v1Client } from "@/app/api/v1";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { CitationDrawer } from "./citation-drawer";
import { CompilationEditorTab } from "./compilation-editor-tab";
import {
  useCompilationDraftQuery,
  useCompilationRunQuery,
} from "./compilation-queries";
import {
  downloadCompilationMarkdownBlob,
  getCompilationRaw,
} from "./compilation-requests";
import { CompilationReviewTab } from "./compilation-review-tab";
import {
  formatCompilationOrigin,
  formatCompilationStatus,
} from "./compilation-schemas";
import type { CitationDetail } from "./compilation-types";
import {
  canCreateOrEditCompilation,
  canRegisterCompiledDocument,
  canReviewCompilation,
} from "./permissions";
import { useCollectionQuery } from "./queries";
import { RegisterDocumentDialog } from "./register-document-dialog";
import { SourceTablesView } from "./source-tables-view";

export function CompilationDetailPage({
  workspaceId,
  collectionId,
  runId,
  initialTab = "draft",
  reviewPage = 1,
  reviewPageSize = 20,
  reviewId,
  onReviewSearch,
}: {
  workspaceId: string;
  collectionId: string;
  runId: string;
  initialTab?: "draft" | "review" | "edit";
  reviewPage?: number;
  reviewPageSize?: number;
  reviewId?: string;
  onReviewSearch?: (patch: {
    reviewPage?: number;
    reviewPageSize?: number;
    reviewId?: string;
    tab?: "draft" | "review" | "edit";
  }) => void;
}) {
  const navigate = useNavigate();
  const [currentTab, setCurrentTab] = useState<"draft" | "review" | "edit">(
    initialTab,
  );

  useEffect(() => setCurrentTab(initialTab), [initialTab]);

  // Citation Drawer state
  const [selectedCitationId, setSelectedCitationId] = useState<string | null>(
    null,
  );
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);

  // Workspace role and permissions
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);
  const canEdit = !rolePending && canCreateOrEditCompilation(role);
  const canReview = !rolePending && canReviewCompilation(role);
  const canRegister = !rolePending && canRegisterCompiledDocument(role);

  // Register Dialog state
  const [isRegisterDialogOpen, setIsRegisterDialogOpen] = useState(false);

  // Queries
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const runQuery = useCompilationRunQuery(workspaceId, collectionId, runId);
  const run = runQuery.data;

  const isCompleted = run?.status === "completed";
  const draftQuery = useCompilationDraftQuery(
    workspaceId,
    collectionId,
    runId,
    { enabled: Boolean(isCompleted) },
  );

  const draft = draftQuery.data;

  // Selected citation detail
  const activeCitationDetail: CitationDetail | null =
    selectedCitationId && draft?.citations
      ? (draft.citations[selectedCitationId] ?? null)
      : null;

  const handleOpenCitation = (citationId: string) => {
    setSelectedCitationId(citationId);
    setIsCitationDrawerOpen(true);
  };

  const handleDownloadMarkdown = async () => {
    try {
      const resp = await downloadCompilationMarkdownBlob(
        v1Client,
        workspaceId,
        collectionId,
        runId,
      );
      const url = URL.createObjectURL(resp.blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `compilation-${runId.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      toast.error("Không thể tải tập tin Markdown.");
    }
  };

  const handleDownloadDraftJson = () => {
    if (!draft) return;
    const blob = new Blob([JSON.stringify(draft, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `draft-${runId.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleViewRawLlm = async () => {
    try {
      const resp = await getCompilationRaw(
        v1Client,
        workspaceId,
        collectionId,
        runId,
      );
      const text = await resp.blob.text();
      // Open in clean new tab safely without eval
      const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } catch {
      toast.error("Không thể tải phản hồi raw LLM.");
    }
  };

  const handleNavigateToOcr = (args: {
    sourceId: string;
    revisionId: string;
    runId: string;
    page?: number;
  }) => {
    setIsCitationDrawerOpen(false);
    void navigate({
      to: "/workspaces/$workspaceId/collections/$collectionId/sources/$sourceId",
      params: {
        workspaceId,
        collectionId,
        sourceId: args.sourceId,
      },
      search: {
        tab: "ocr",
        revisionId: args.revisionId,
        runId: args.runId,
        page: args.page ?? 1,
        subTab: "comparison",
      },
    });
  };

  if (runQuery.isLoading || collectionQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (runQuery.isError || !run) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId"
            params={{ workspaceId, collectionId }}
            search={{ page: 1, pageSize: 20, tab: "compilations" }}
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại bộ sưu tập</span>
          </Link>
        </Button>
        <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-5 text-xs space-y-2">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="size-4 shrink-0" />
            <span>Không tìm thấy lượt biên soạn</span>
          </div>
          <p className="text-muted-foreground">
            Lượt biên soạn không tồn tại hoặc bạn không có quyền truy cập.
          </p>
        </Card>
      </div>
    );
  }

  const collection = collectionQuery.data;
  const statusInfo = formatCompilationStatus(run.status);
  const originInfo = formatCompilationOrigin(run.origin);

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
          search={{ page: 1, pageSize: 20, tab: "compilations" }}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {collection?.name ?? "Bộ sưu tập"}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-medium text-foreground">
          Biên soạn Gen #{run.generation}
        </span>
      </div>

      {/* Header Summary Card */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-5 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="space-y-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <BookOpen className="size-5 text-primary shrink-0" />
                <h1 className="text-base sm:text-lg font-bold text-foreground">
                  {draft?.title || run.topic}
                </h1>
                <Badge variant="outline" className="font-mono text-xs">
                  Gen #{run.generation}
                </Badge>
                <Badge
                  variant={statusInfo.variant}
                  className="text-xs font-normal"
                >
                  {statusInfo.label}
                </Badge>
                {run.status === "running" && (
                  <Loader2 className="size-3.5 animate-spin text-primary" />
                )}
              </div>

              {draft?.title && run.topic !== draft.title && (
                <p className="text-xs text-muted-foreground line-clamp-2">
                  <span className="font-semibold text-foreground/80">
                    Chủ đề:
                  </span>{" "}
                  {run.topic}
                </p>
              )}
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2 shrink-0">
              {isCompleted && (
                <>
                  {canRegister && (
                    <Button
                      size="sm"
                      className="h-8 text-xs gap-1.5"
                      onClick={() => setIsRegisterDialogOpen(true)}
                    >
                      <BookPlus className="size-3.5" />
                      <span>Đăng ký thành tài liệu biên soạn</span>
                    </Button>
                  )}

                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs gap-1.5"
                    onClick={handleDownloadMarkdown}
                  >
                    <Download className="size-3.5" />
                    <span className="hidden sm:inline">Tải Markdown</span>
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 text-xs gap-1.5"
                    onClick={handleDownloadDraftJson}
                  >
                    <FileCode className="size-3.5" />
                    <span className="hidden sm:inline">Tải JSON</span>
                  </Button>
                </>
              )}
            </div>
          </div>

          {/* Điều kiện chuyển bước rõ ràng */}
          <div className="rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
            <span>
              <strong className="text-foreground">
                Điều kiện chuyển bước:
              </strong>{" "}
              {isCompleted
                ? "1. Xem nội dung, dẫn chứng và báo cáo AI nếu có → 2. Chỉnh sửa nếu cần, xem trước và xác nhận lưu bản mới → 3. Đăng ký đúng bản đã kiểm tra để Duyệt & Phát hành."
                : run.status === "running" || run.status === "queued"
                  ? "Đang chờ tiến trình biên soạn hoàn tất sinh bản thảo có trích dẫn…"
                  : "Lượt biên soạn chưa hoàn tất. Hãy kiểm tra thông báo lỗi hoặc tạo lượt biên soạn mới."}
            </span>
          </div>

          {/* Metadata Row */}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 pt-2 border-t text-xs text-muted-foreground">
            <div>
              Nguồn gốc:{" "}
              {originInfo.isEdit ? (
                <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                  <GitBranch className="size-3" />
                  Bản sửa người dùng
                  {run.parent_run_id && (
                    <Link
                      to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                      params={{
                        workspaceId,
                        collectionId,
                        runId: run.parent_run_id,
                      }}
                      className="ml-1 font-mono text-[11px] underline hover:text-foreground"
                    >
                      (Bản gốc: {run.parent_run_id.slice(0, 8)}...)
                    </Link>
                  )}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 font-semibold text-primary">
                  <Sparkles className="size-3" />
                  AI Compiler
                </span>
              )}
            </div>

            <div>
              Mô hình:{" "}
              <span className="font-mono text-foreground">
                {run.provider_id || "Mặc định workspace"}
              </span>
            </div>

            <div>
              Tokens:{" "}
              <span className="font-mono text-foreground font-semibold">
                {run.usage_tokens !== null
                  ? run.usage_tokens.toLocaleString()
                  : "Chưa xác định"}
              </span>
            </div>

            <div>
              Thời điểm:{" "}
              <span className="text-foreground">
                {formatDateTimeValue(run.requested_at)}
              </span>
            </div>

            {run.finished_at && (
              <div>
                Hoàn tất:{" "}
                <span className="text-foreground">
                  {formatDateTimeValue(run.finished_at)}
                </span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Running / Queued Polling Banner */}
      {(run.status === "running" || run.status === "queued") && (
        <Alert className="rounded-xl border-primary/30 bg-primary/5 text-xs py-3">
          <Loader2 className="size-4 animate-spin text-primary shrink-0" />
          <AlertTitle className="text-xs font-semibold text-foreground">
            {run.status === "queued"
              ? "Lượt biên soạn đang chờ xếp lịch xử lý..."
              : "Mô hình AI đang tổng hợp và trích xuất bản biên soạn..."}
          </AlertTitle>
          <AlertDescription className="text-muted-foreground text-[11px] mt-1">
            Giao diện sẽ tự động cập nhật ngay khi quá trình hoàn tất. Bạn có
            thể giữ trang này hoặc chuyển tab khác.
          </AlertDescription>
        </Alert>
      )}

      {/* Main Tabs */}
      <Tabs
        value={currentTab}
        onValueChange={(val) => {
          const tab = val as "draft" | "review" | "edit";
          setCurrentTab(tab);
          onReviewSearch?.({ tab });
        }}
      >
        <TabsList className="h-9 p-0.5 bg-muted/40 text-xs">
          <TabsTrigger value="draft" className="text-xs h-8 px-4 gap-1.5">
            <BookOpen className="size-3.5" />
            <span>Bản biên soạn & Dẫn chứng</span>
          </TabsTrigger>

          <TabsTrigger value="review" className="text-xs h-8 px-4 gap-1.5">
            <FileCheck2 className="size-3.5" />
            <span>Rà soát & Đánh giá</span>
          </TabsTrigger>

          {canEdit && (
            <TabsTrigger value="edit" className="text-xs h-8 px-4 gap-1.5">
              <FileEdit className="size-3.5" />
              <span>Chỉnh sửa bản biên soạn</span>
            </TabsTrigger>
          )}
        </TabsList>

        {/* Tab 1: Draft Content & Evidence */}
        <TabsContent value="draft" className="space-y-6 pt-4">
          {!isCompleted ? (
            <Card className="rounded-xl p-10 text-center text-xs text-muted-foreground">
              <p>
                Chưa có bản nháp biên soạn cho lượt này (trạng thái:{" "}
                {statusInfo.label}).
              </p>
            </Card>
          ) : draftQuery.isLoading ? (
            <Card className="rounded-xl p-5 space-y-4">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-48 w-full" />
            </Card>
          ) : draftQuery.isError || !draft ? (
            <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
              <p className="text-destructive font-semibold">
                Không thể tải nội dung bản nháp.
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              {/* Draft Document View */}
              <Card className="rounded-xl shadow-2xs">
                <CardHeader className="p-4 sm:p-5 border-b bg-muted/10">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <CardTitle className="text-base font-bold text-foreground">
                      {draft.title}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      className="text-[11px] self-start sm:self-auto"
                    >
                      Bản nháp chưa duyệt (Draft)
                    </Badge>
                  </div>
                </CardHeader>

                <CardContent className="p-4 sm:p-6 space-y-6 text-sm">
                  {draft.sections.map((sec, sIdx) => (
                    <div
                      // biome-ignore lint/suspicious/noArrayIndexKey: ordered document structure
                      key={sIdx}
                      className="space-y-3"
                    >
                      <h2 className="text-sm sm:text-base font-bold text-foreground border-b pb-1.5">
                        {sec.heading}
                      </h2>
                      <div className="space-y-3">
                        {sec.paragraphs.map((p, pIdx) => (
                          <div
                            // biome-ignore lint/suspicious/noArrayIndexKey: ordered document structure
                            key={pIdx}
                            className="text-xs sm:text-sm text-foreground/90 leading-relaxed font-sans"
                          >
                            <span>{p.text}</span>
                            {p.citations && p.citations.length > 0 && (
                              <span className="inline-flex flex-wrap gap-1 ml-1.5 align-baseline">
                                {p.citations.map((cId) => (
                                  <button
                                    key={cId}
                                    type="button"
                                    onClick={() => handleOpenCitation(cId)}
                                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono bg-primary/10 text-primary hover:bg-primary/20 transition-colors border border-primary/20"
                                    title="Xem bằng chứng nguồn đối chiếu"
                                  >
                                    <Tag className="size-2.5" />
                                    <span>[{cId}]</span>
                                  </button>
                                ))}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Unknowns Callout */}
              {draft.unknowns && draft.unknowns.length > 0 && (
                <Card className="rounded-xl shadow-2xs border-warning/30 bg-warning/5">
                  <CardHeader className="p-3 sm:p-4 border-b border-warning/20">
                    <div className="flex items-center gap-2">
                      <HelpCircle className="size-4 text-warning" />
                      <CardTitle className="text-xs font-semibold text-foreground">
                        Các nội dung chưa xác định (Unknowns)
                      </CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent className="p-3 sm:p-4 text-xs space-y-1.5">
                    <p className="text-[11px] text-muted-foreground">
                      Mô hình ghi nhận các điểm thiếu căn cứ hoặc có mâu thuẫn
                      trong bằng chứng nguồn:
                    </p>
                    <ul className="list-disc pl-4 space-y-1 text-foreground/90 font-sans">
                      {draft.unknowns.map((u, i) => (
                        <li
                          // biome-ignore lint/suspicious/noArrayIndexKey: immutable list
                          key={i}
                        >
                          {u}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )}

              {/* Source Tables (Read-Only) */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                    <Layers className="size-4 text-primary" />
                    <span>
                      Các bảng nguồn đính kèm (
                      {draft.source_tables?.length ?? 0})
                    </span>
                  </h3>
                  <span className="text-[11px] text-muted-foreground">
                    Bảo toàn nguyên cấu trúc hàng, cột, ô trống và số liệu gốc.
                  </span>
                </div>
                <SourceTablesView
                  tables={draft.source_tables ?? []}
                  onSelectCitation={handleOpenCitation}
                />
              </div>

              {/* Sources Metadata Summary */}
              {draft.sources && draft.sources.length > 0 && (
                <Card className="rounded-xl shadow-2xs text-xs">
                  <CardHeader className="p-3 sm:p-4 bg-muted/20 border-b">
                    <CardTitle className="text-xs font-semibold">
                      Danh mục tài liệu nguồn đã sử dụng ({draft.sources.length}
                      )
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-3 sm:p-4 space-y-2">
                    {draft.sources.map((s) => (
                      <div
                        key={s.ocr_run_id}
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 p-2 rounded bg-card border text-[11px]"
                      >
                        <div className="space-y-0.5">
                          <span className="font-semibold text-foreground">
                            {s.identity.filename}
                          </span>
                          <div className="text-muted-foreground font-mono text-[10px]">
                            OCR Run: {s.ocr_run_id} · Rev:{" "}
                            {s.identity.revision_id}
                          </div>
                        </div>
                        {s.text_version ? (
                          <Badge
                            variant="secondary"
                            className="font-mono text-[10px] self-start sm:self-auto"
                          >
                            Hậu OCR #{s.text_version.version}
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="font-mono text-[10px] self-start sm:self-auto"
                          >
                            v0 (OCR gốc)
                          </Badge>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* LLM Raw Response On-Demand */}
              {run.origin !== "user_edit" && (
                <div className="pt-2 text-right">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-xs text-muted-foreground gap-1 h-7"
                    onClick={handleViewRawLlm}
                  >
                    <FileCode className="size-3" />
                    <span>Xem phản hồi LLM thô</span>
                  </Button>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Review Content */}
        <TabsContent value="review" className="pt-4">
          <CompilationReviewTab
            key={`${workspaceId}:${collectionId}:${runId}`}
            workspaceId={workspaceId}
            collectionId={collectionId}
            runId={runId}
            canReview={canReview}
            onEdit={
              canEdit && isCompleted
                ? () => {
                    setCurrentTab("edit");
                    onReviewSearch?.({ tab: "edit" });
                  }
                : undefined
            }
            page={reviewPage}
            pageSize={reviewPageSize}
            reviewId={reviewId}
            onSearchChange={
              onReviewSearch
                ? (patch) => onReviewSearch({ ...patch, tab: "review" })
                : undefined
            }
          />
        </TabsContent>

        {/* Tab 3: Structured Editor Content */}
        {canEdit && (
          <TabsContent value="edit" className="pt-4">
            <CompilationEditorTab
              workspaceId={workspaceId}
              collectionId={collectionId}
              runId={runId}
              canEdit={canEdit}
              onNavigateToChild={(childId) => {
                void navigate({
                  to: "/workspaces/$workspaceId/collections/$collectionId/compilations/$runId",
                  params: {
                    workspaceId,
                    collectionId,
                    runId: childId,
                  },
                });
              }}
            />
          </TabsContent>
        )}
      </Tabs>

      {/* Citation Inspector Side Drawer */}
      <CitationDrawer
        citationId={selectedCitationId}
        detail={activeCitationDetail}
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
        onNavigateToOcr={handleNavigateToOcr}
      />

      {/* Register as Compiled Document Dialog */}
      <RegisterDocumentDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        compilationRunId={run.id}
        defaultTitle={draft?.title || run.topic}
        isOpen={isRegisterDialogOpen}
        onClose={() => setIsRegisterDialogOpen(false)}
        onSuccess={(docId, verId) => {
          void navigate({
            to: "/workspaces/$workspaceId/collections/$collectionId/documents/$documentId/versions/$versionId",
            params: {
              workspaceId,
              collectionId,
              documentId: docId,
              versionId: verId,
            },
          });
        }}
      />
    </div>
  );
}
