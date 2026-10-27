import { Link } from "@tanstack/react-router";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Eye,
  HelpCircle,
  Layers,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Tag,
} from "lucide-react";
import { useState } from "react";
import { ApiProblemError } from "@/app/api/v1";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useCallerWorkspaceRole } from "@/features/workspaces/queries";
import { formatDateTimeValue } from "@/lib/date-utils";
import { CitationDrawer } from "./citation-drawer";
import type { CitationDetail } from "./compilation-types";
import { DecisionConfirmDialog } from "./decision-confirm-dialog";
import {
  canApproveCompiledVersion,
  canPublishCompiledVersion,
  canWithdrawCompiledVersion,
} from "./permissions";
import {
  useCompiledDocumentQuery,
  useCompiledVersionDraftQuery,
  useCompiledVersionQuery,
  useDecisionPreviewMutation,
} from "./publication-queries";
import {
  formatPublicationError,
  formatPublicationStatus,
} from "./publication-schemas";
import type { DecisionPreviewResponse } from "./publication-types";
import { useCollectionQuery } from "./queries";
import { RetrievalMetadataView } from "./retrieval-metadata-view";
import { ReviewGateDialog } from "./review-gate-dialog";
import { SourceTablesView } from "./source-tables-view";

export function CompiledVersionDetailPage({
  workspaceId,
  collectionId,
  documentId,
  versionId,
}: {
  workspaceId: string;
  collectionId: string;
  documentId: string;
  versionId: string;
}) {
  const { role, isPending: rolePending } = useCallerWorkspaceRole(workspaceId);

  const canApprove = !rolePending && canApproveCompiledVersion(role);
  const canPublish = !rolePending && canPublishCompiledVersion(role);
  const canWithdraw = !rolePending && canWithdrawCompiledVersion(role);

  // Queries
  const collectionQuery = useCollectionQuery(workspaceId, collectionId);
  const documentQuery = useCompiledDocumentQuery(
    workspaceId,
    collectionId,
    documentId,
  );
  const versionQuery = useCompiledVersionQuery(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );
  const draftQuery = useCompiledVersionDraftQuery(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );

  const previewMutation = useDecisionPreviewMutation(
    workspaceId,
    collectionId,
    documentId,
    versionId,
  );

  // Dialog states
  const [isReviewGateOpen, setIsReviewGateOpen] = useState(false);
  const [activePreview, setActivePreview] =
    useState<DecisionPreviewResponse | null>(null);
  const [isConfirmDialogOpen, setIsConfirmDialogOpen] = useState(false);

  // Quick Action Dialog (for Publish / Withdraw)
  const [quickAction, setQuickAction] = useState<"publish" | "withdraw" | null>(
    null,
  );
  const [quickReason, setQuickReason] = useState("");
  const [quickActionError, setQuickActionError] = useState<string | null>(null);

  // Citation Drawer
  const [selectedCitation, setSelectedCitation] = useState<{
    id: string;
    detail: CitationDetail | null;
  } | null>(null);
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);

  // Tab
  const [activeTab, setActiveTab] = useState<"draft" | "tables">("draft");

  const collection = collectionQuery.data;
  const doc = documentQuery.data;
  const ver = versionQuery.data;
  const draft = draftQuery.data;

  if (
    documentQuery.isLoading ||
    versionQuery.isLoading ||
    collectionQuery.isLoading
  ) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (documentQuery.isError || versionQuery.isError || !doc || !ver) {
    return (
      <div className="space-y-4">
        <Button asChild variant="ghost" size="sm" className="gap-1.5 text-xs">
          <Link
            to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId"
            params={{ workspaceId, collectionId, documentId }}
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại tài liệu biên soạn</span>
          </Link>
        </Button>
        <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-5 text-xs space-y-2">
          <div className="flex items-center gap-2 text-destructive font-semibold">
            <AlertCircle className="size-4 shrink-0" />
            <span>Không tìm thấy phiên bản biên soạn</span>
          </div>
          <p className="text-muted-foreground">
            Phiên bản không tồn tại hoặc bạn không có quyền truy cập.
          </p>
        </Card>
      </div>
    );
  }

  const statusInfo = formatPublicationStatus(ver.status);

  // Permissions & Transitions
  const canPerformApprove =
    canApprove &&
    (ver.status === "draft" ||
      ver.status === "superseded" ||
      ver.status === "withdrawn");

  const canPerformPublish = canPublish && ver.status === "approved";

  const canPerformWithdraw =
    canWithdraw && (ver.status === "approved" || ver.status === "published");

  const handleOpenCitation = (citationId: string) => {
    const detail = draft?.citations?.[citationId] ?? null;
    setSelectedCitation({ id: citationId, detail });
    setIsCitationDrawerOpen(true);
  };

  const handleOpenQuickAction = (action: "publish" | "withdraw") => {
    setQuickAction(action);
    setQuickReason("");
    setQuickActionError(null);
  };

  const handleQuickActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickAction) return;

    if (!quickReason.trim()) {
      setQuickActionError("Vui lòng nhập lý do thực hiện quyết định.");
      return;
    }

    try {
      const preview = await previewMutation.mutateAsync({
        input: {
          action: quickAction,
          reason: quickReason.trim(),
        },
      });

      setQuickAction(null);
      setActivePreview(preview);
      setIsConfirmDialogOpen(true);
    } catch (err: unknown) {
      if (err instanceof ApiProblemError) {
        setQuickActionError(formatPublicationError(err.code, err.message));
      } else {
        setQuickActionError("Không thể tạo bản xem trước. Vui lòng thử lại.");
      }
    }
  };

  const handleReviewGatePreviewSuccess = (preview: DecisionPreviewResponse) => {
    setActivePreview(preview);
    setIsConfirmDialogOpen(true);
  };

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
        <Link
          to="/workspaces/$workspaceId/collections/$collectionId/documents/$documentId"
          params={{ workspaceId, collectionId, documentId }}
          className="hover:text-foreground transition-colors truncate max-w-[150px]"
        >
          {doc.title}
        </Link>
        <ChevronRight className="size-3 text-muted-foreground/60" />
        <span className="font-medium text-foreground">
          Phiên bản v{ver.version_no}
        </span>
      </div>

      {/* Version Header Card */}
      <Card className="rounded-xl shadow-2xs">
        <CardContent className="p-4 sm:p-6 space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1.5 min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap">
                <Badge
                  variant="outline"
                  className="font-mono text-sm px-2.5 py-0.5 font-bold"
                >
                  v{ver.version_no}
                </Badge>
                <h1 className="text-base sm:text-xl font-bold text-foreground">
                  {doc.title}
                </h1>
                <Badge
                  variant="outline"
                  className={`text-xs ${statusInfo.badgeClass}`}
                >
                  {statusInfo.label}
                </Badge>
              </div>

              <div className="flex items-center gap-3 text-xs text-muted-foreground font-mono flex-wrap">
                <span>ID: {ver.id}</span>
                <span>•</span>
                <Link
                  to="/workspaces/$workspaceId/collections/$collectionId/compilations/$runId"
                  params={{
                    workspaceId,
                    collectionId,
                    runId: ver.compilation_run_id,
                  }}
                  className="text-primary hover:underline inline-flex items-center gap-1"
                >
                  <span>Compiler Run: {ver.compilation_run_id}</span>
                  <ExternalLink className="size-3" />
                </Link>
              </div>
            </div>

            {/* Lifecycle Action Buttons */}
            <div className="flex flex-wrap items-center gap-2 shrink-0">
              {canPerformApprove && (
                <Button
                  size="sm"
                  variant="secondary"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => setIsReviewGateOpen(true)}
                >
                  <ShieldCheck className="size-3.5" />
                  <span>Duyệt phiên bản (Approve)</span>
                </Button>
              )}

              {canPerformPublish && (
                <Button
                  size="sm"
                  variant="default"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => handleOpenQuickAction("publish")}
                >
                  <CheckCircle2 className="size-3.5" />
                  <span>Xuất bản (Publish)</span>
                </Button>
              )}

              {canPerformWithdraw && (
                <Button
                  size="sm"
                  variant="destructive"
                  className="h-8 text-xs gap-1.5"
                  onClick={() => handleOpenQuickAction("withdraw")}
                >
                  <ShieldAlert className="size-3.5" />
                  <span>Thu hồi (Withdraw)</span>
                </Button>
              )}
            </div>
          </div>

          {/* Hashes & Metadata Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-3 border-t text-[11px] text-muted-foreground font-mono">
            <div>
              <span className="text-muted-foreground/80 font-sans">
                State version:
              </span>{" "}
              <span className="font-semibold text-foreground">
                #{ver.state_version}
              </span>
            </div>
            <div
              className="truncate"
              title={`bundle_sha256: ${ver.bundle_sha256}`}
            >
              <span className="font-sans">Bundle:</span>{" "}
              {ver.bundle_sha256.slice(0, 16)}...
            </div>
            <div
              className="truncate"
              title={`draft_sha256: ${ver.draft_sha256}`}
            >
              <span className="font-sans">Draft:</span>{" "}
              {ver.draft_sha256.slice(0, 16)}...
            </div>
            <div className="text-right truncate font-sans">
              Tạo bởi{" "}
              <span className="font-mono text-foreground">
                {ver.created_by}
              </span>{" "}
              vào {formatDateTimeValue(ver.created_at)}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Declared retrieval metadata with its evidence — reviewed before approval */}
      <RetrievalMetadataView
        annotations={ver.retrieval_metadata ?? []}
        sha256={ver.retrieval_metadata_sha256}
      />

      {/* Main Content Viewer: Draft vs Tables */}
      <Tabs
        value={activeTab}
        onValueChange={(val) => setActiveTab(val as "draft" | "tables")}
        className="space-y-4"
      >
        <div className="flex items-center justify-between border-b pb-1">
          <TabsList className="h-9">
            <TabsTrigger value="draft" className="gap-1.5 text-xs">
              <BookOpen className="size-3.5" />
              <span>Nội dung bất biến & Dẫn chứng</span>
            </TabsTrigger>
            <TabsTrigger value="tables" className="gap-1.5 text-xs">
              <Layers className="size-3.5" />
              <span>
                Bảng số liệu gốc ({draft?.source_tables?.length ?? 0})
              </span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Draft Content */}
        <TabsContent value="draft" className="space-y-4 m-0">
          {draftQuery.isLoading ? (
            <Card className="rounded-xl p-6 space-y-4">
              <Skeleton className="h-8 w-64" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-40 w-full" />
            </Card>
          ) : draftQuery.isError || !draft ? (
            <Card className="rounded-xl border-destructive/20 bg-destructive/5 p-4 text-xs">
              <p className="text-destructive font-semibold">
                Không thể tải nội dung bản nháp của phiên bản này.
              </p>
            </Card>
          ) : (
            <div className="space-y-6">
              <Card className="rounded-xl shadow-2xs">
                <CardHeader className="p-4 sm:p-6 border-b bg-muted/10">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <CardTitle className="text-base sm:text-lg font-bold text-foreground">
                      {draft.title}
                    </CardTitle>
                    <Badge
                      variant="outline"
                      className="text-[11px] self-start sm:self-auto font-mono"
                    >
                      schema: {draft.schema_version}
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
                                    className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono bg-primary/10 text-primary hover:bg-primary/20 transition-colors border border-primary/20 cursor-pointer"
                                    title="Xem chi tiết bằng chứng nguồn"
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
            </div>
          )}
        </TabsContent>

        {/* Tab 2: Literal Tables */}
        <TabsContent value="tables" className="space-y-4 m-0">
          <SourceTablesView tables={draft?.source_tables ?? []} />
        </TabsContent>
      </Tabs>

      {/* Review Gate Dialog */}
      <ReviewGateDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        documentId={documentId}
        versionId={versionId}
        versionNo={ver.version_no}
        retrievalMetadata={ver.retrieval_metadata ?? []}
        retrievalMetadataSha256={ver.retrieval_metadata_sha256 ?? ""}
        isOpen={isReviewGateOpen}
        onClose={() => setIsReviewGateOpen(false)}
        onPreviewSuccess={handleReviewGatePreviewSuccess}
      />

      {/* Quick Action Preview Dialog (for Publish / Withdraw) */}
      <Dialog
        open={Boolean(quickAction)}
        onOpenChange={(open) =>
          !previewMutation.isPending && !open && setQuickAction(null)
        }
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <div
                className={`size-8 rounded-lg flex items-center justify-center shrink-0 ${
                  quickAction === "withdraw"
                    ? "bg-destructive/10 text-destructive"
                    : "bg-primary/10 text-primary"
                }`}
              >
                {quickAction === "withdraw" ? (
                  <ShieldAlert className="size-4" />
                ) : (
                  <CheckCircle2 className="size-4" />
                )}
              </div>
              <div>
                <DialogTitle className="text-base font-semibold">
                  {quickAction === "withdraw"
                    ? `Thu hồi phiên bản v${ver.version_no}`
                    : `Xuất bản phiên bản v${ver.version_no}`}
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  {quickAction === "withdraw"
                    ? "Nhập lý do thu hồi để chuẩn bị bản xem trước quyết định."
                    : "Nhập lý do xuất bản để chuẩn bị bản xem trước quyết định."}
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>

          <form onSubmit={handleQuickActionSubmit} className="space-y-4 pt-2">
            {quickActionError && (
              <Alert variant="destructive" className="py-2.5">
                <AlertCircle className="size-4" />
                <AlertDescription className="text-xs">
                  {quickActionError}
                </AlertDescription>
              </Alert>
            )}

            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <Label
                  htmlFor="quick-reason"
                  className="font-semibold text-foreground"
                >
                  Lý do quyết định <span className="text-destructive">*</span>
                </Label>
                <span className="text-[11px] text-muted-foreground">
                  {quickReason.trim().length}/1000
                </span>
              </div>
              <Textarea
                id="quick-reason"
                value={quickReason}
                onChange={(e) => setQuickReason(e.target.value)}
                placeholder={
                  quickAction === "withdraw"
                    ? "Nêu rõ nguyên nhân thu hồi (ví dụ: phát hiện số liệu sai sót sau kiểm toán)..."
                    : "Nêu căn cứ phê chuẩn xuất bản làm nguồn tri thức chính thức..."
                }
                rows={3}
                maxLength={1000}
                className="text-xs resize-none"
                disabled={previewMutation.isPending}
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setQuickAction(null)}
                disabled={previewMutation.isPending}
                className="text-xs"
              >
                Hủy
              </Button>
              <Button
                type="submit"
                variant={quickAction === "withdraw" ? "destructive" : "default"}
                size="sm"
                disabled={previewMutation.isPending || !quickReason.trim()}
                className="text-xs gap-1.5"
              >
                {previewMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>Đang tạo bản xem trước...</span>
                  </>
                ) : (
                  <>
                    <Eye className="size-3.5" />
                    <span>Xem trước quyết định</span>
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Decision Confirm Dialog */}
      <DecisionConfirmDialog
        workspaceId={workspaceId}
        collectionId={collectionId}
        documentId={documentId}
        versionId={versionId}
        preview={activePreview}
        isOpen={isConfirmDialogOpen}
        onClose={() => {
          setIsConfirmDialogOpen(false);
          setActivePreview(null);
        }}
        onCommitSuccess={() => {
          setIsConfirmDialogOpen(false);
          setActivePreview(null);
          void versionQuery.refetch();
          void documentQuery.refetch();
        }}
      />

      {/* Citation Drawer */}
      <CitationDrawer
        citationId={selectedCitation?.id ?? null}
        detail={selectedCitation?.detail ?? null}
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
      />
    </div>
  );
}
