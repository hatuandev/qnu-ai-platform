import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  FileText,
  History,
  Layers,
  Pencil,
  RefreshCw,
  Save,
  Scan,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { BackButton } from "@/components/admin/back-button";
import { EmptyState } from "@/components/admin/empty-state";
import { DocumentStudioWorkspace } from "@/components/knowledge/ocr/document-studio-workspace";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { useRbac } from "@/rbac/context";
import { extractErrorMessage, knowledgeApi } from "@/services/knowledge-api";
import type {
  ContextIssueDecision,
  KnowledgeChunkSetResponse,
  KnowledgeSourceDetailResponse,
} from "@/types/knowledge";
import { DeleteSourceButton } from "./components/delete-source-button";
import { IngestionReadinessPanel } from "./components/ingestion-readiness-panel";
import { KnowledgeWikiPanel } from "./components/knowledge-wiki-panel";
import { QnuStandardEditor } from "./components/qnu-standard-editor";
import { SemanticCheckpointImport } from "./components/semantic-checkpoint-import";
import { SemanticReviewPreview } from "./components/semantic-review-preview";
import { SmartApprovalPanel } from "./components/smart-approval-panel";
import { SourceContextEditor } from "./components/source-context-editor";
import { VectorLoadControls } from "./components/vector-load-controls";
import { refreshSourceQueries } from "./utils/source-query-cache";

interface SourceDetailPageProps {
  collectionId: string;
  sourceId: string;
  isStudioMode: boolean;
  onStudioModeChange: (isOpen: boolean) => void;
  revisionId?: string;
  onRevisionChange: (revisionId: string) => void;
  activeTab: "content" | "quality" | "chunks" | "revisions";
  onTabChange: (tab: "content" | "quality" | "chunks" | "revisions") => void;
}

export const SourceDetailPage: React.FC<SourceDetailPageProps> = ({
  collectionId,
  sourceId,
  isStudioMode,
  onStudioModeChange,
  revisionId,
  onRevisionChange: setSelectedRevisionId,
  activeTab,
  onTabChange: setActiveTab,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const rbac = useRbac();
  const canReviewSemantics =
    rbac.isAccessVerified &&
    !rbac.isDemoMode &&
    rbac.can("ai.knowledge.update");

  // Editing state
  const [isEditingMarkdown, setIsEditingMarkdown] = useState(false);
  const [isMarkdownVisible, setIsMarkdownVisible] = useState(false);
  const [editedMarkdown, setEditedMarkdown] = useState("");
  const [editReason, setEditReason] = useState("");

  // Review modal state
  const [isReviewDialogOpen, setIsReviewDialogOpen] = useState(false);
  const [reviewDecision, setReviewDecision] = useState<"approved" | "rejected">(
    "approved",
  );
  const [reviewComment, setReviewComment] = useState("");
  const [isSmartApprovalPending, setIsSmartApprovalPending] = useState(false);
  const [reviewedSemanticKey, setReviewedSemanticKey] = useState<string | null>(
    null,
  );

  // 1. Fetch Collection Info
  const { data: collection } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 2. Fetch Source Detail (V3)
  const {
    data: source,
    isLoading: isSourceLoading,
    isError: isSourceError,
    error: sourceError,
  } = useQuery<KnowledgeSourceDetailResponse>({
    queryKey: ["knowledge-source", collectionId, sourceId],
    queryFn: () => knowledgeApi.getKnowledgeSource(collectionId, sourceId),
    enabled: !!sourceId,
    refetchInterval: (query) =>
      query.state.data?.revisions?.some((r) =>
        ["queued", "extracting", "normalizing", "validating"].includes(
          r.status,
        ),
      )
        ? 1500
        : false,
  });

  // Active Revision
  const activeRev =
    source?.revisions.find((r) => r.id === revisionId) ||
    source?.revisions?.[0] ||
    source?.active_source_revision;

  const semanticReview = useQuery({
    queryKey: ["source-semantic-review", collectionId, sourceId, activeRev?.id],
    queryFn: () =>
      knowledgeApi.getSourceStudioView(
        collectionId,
        sourceId,
        activeRev?.id ?? "",
      ),
    enabled: isReviewDialogOpen && !!activeRev?.id,
  });
  const semanticProposal =
    semanticReview.data?.structured_artifact?.semantic_annotations;
  const semanticReviewKey = `${activeRev?.id}:${semanticProposal?.proposal_hash}`;
  const hasReviewedSemantics = reviewedSemanticKey === semanticReviewKey;
  const [contextSelection, setContextSelection] = useState<{
    key: string;
    decisions: ContextIssueDecision[];
  }>({ key: "", decisions: [] });
  const contextDecisions =
    contextSelection.key === semanticReviewKey
      ? contextSelection.decisions
      : [];
  const openContextIds =
    semanticReview.data?.structured_artifact?.source_policy
      ?.context_blocker_ids ?? [];
  const contextApplyBlocked =
    semanticProposal?.context_review?.coverage_complete === false ||
    semanticProposal?.context_review?.packets_complete === false ||
    openContextIds.some(
      (id) => !contextDecisions.some((item) => item.issue_id === id),
    );
  const semanticIsPending =
    semanticProposal?.status === "proposed" ||
    (semanticProposal?.status === "empty" && contextApplyBlocked);

  // Sync markdown content when revision loads
  useEffect(() => {
    setEditedMarkdown(activeRev?.canonical_markdown ?? "");
  }, [activeRev?.canonical_markdown]);

  // 3. Fetch Chunk Sets (V3)
  const { data: chunkSets = [], isLoading: isChunkSetsLoading } = useQuery<
    KnowledgeChunkSetResponse[]
  >({
    queryKey: ["knowledge-source-chunk-sets", collectionId, sourceId],
    queryFn: () => knowledgeApi.listSourceChunkSets(collectionId, sourceId),
    enabled: !!sourceId,
  });

  // 4. Mutation Update Markdown
  const updateContentMutation = useMutation({
    mutationFn: () => {
      if (!activeRev?.id) throw new Error("Chưa có bản sửa đổi để cập nhật.");
      if (!editReason.trim())
        throw new Error("Hãy ghi lý do hiệu đính trước khi lưu.");
      return knowledgeApi.updateSourceRevisionContent(
        collectionId,
        sourceId,
        activeRev.id,
        editedMarkdown,
        {
          change_reason: editReason.trim(),
          expected_canonical_hash: activeRev.canonical_hash ?? undefined,
        },
      );
    },
    onSuccess: async (revision) => {
      toast.success("Đã lưu hiệu đính nội dung Markdown chuẩn thành công.");
      setIsEditingMarkdown(false);
      setEditReason("");
      await refreshSourceQueries(queryClient, collectionId, sourceId);
      setSelectedRevisionId(revision.id);
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Cập nhật nội dung thất bại."));
    },
  });

  // 5. Mutation Review Revision
  const proposalMutation = useMutation({
    mutationFn: () => {
      if (!activeRev?.id) throw new Error("Chưa có bản nháp để đối chiếu.");
      return knowledgeApi.generateSemanticProposals(
        collectionId,
        sourceId,
        activeRev.id,
      );
    },
    onSuccess: async () => {
      await refreshSourceQueries(queryClient, collectionId, sourceId);
      await queryClient.invalidateQueries({
        queryKey: ["source-semantic-review", collectionId, sourceId],
      });
      toast.success(
        "Đã nhận kết quả phân tích. Hãy xem trạng thái ngữ cảnh và từng vấn đề trước khi áp dụng.",
      );
    },
    onError: (error: unknown) =>
      toast.error(extractErrorMessage(error, "Tạo đề xuất thất bại.")),
  });
  const semanticMutation = useMutation({
    mutationFn: (
      decision:
        | "approved"
        | "acknowledged_limits"
        | "rejected"
        | "changes_requested",
    ) => {
      if (
        !canReviewSemantics ||
        !activeRev?.id ||
        !semanticProposal?.proposal_hash ||
        !hasReviewedSemantics ||
        reviewComment.trim().length < 3
      )
        throw new Error(
          "Hãy đối chiếu đề xuất và ghi chú trước khi áp dụng vào bản nháp.",
        );
      if (
        (decision === "approved" || decision === "acknowledged_limits") &&
        contextApplyBlocked
      )
        throw new Error("Còn vấn đề ngữ cảnh hoặc phạm vi chưa được xử lý.");
      return knowledgeApi.reviewSemanticProposals(
        collectionId,
        sourceId,
        activeRev.id,
        semanticProposal.proposal_hash,
        reviewComment.trim(),
        decision,
        decision === "acknowledged_limits" ? "acknowledged_limits" : "strict",
        decision === "approved" || decision === "acknowledged_limits"
          ? contextDecisions
          : [],
      );
    },
    onSuccess: async (_revision, decision) => {
      await refreshSourceQueries(queryClient, collectionId, sourceId);
      await queryClient.invalidateQueries({
        queryKey: ["source-semantic-review", collectionId, sourceId],
      });
      toast.success(
        decision === "acknowledged_limits"
          ? "Đã ghi nhận giới hạn nguồn. Dữ liệu chưa rõ vẫn giữ nguyên; xuất bản vẫn bị chặn."
          : decision === "changes_requested"
            ? "Đã ghi nhận yêu cầu kiểm tra tiếp."
            : decision === "approved"
              ? "Đã áp dụng đề xuất đã duyệt vào bản nháp. Tài liệu chưa được xuất bản."
              : "Đã bỏ đề xuất. Dữ liệu trong bản nháp được giữ nguyên.",
      );
    },
    onError: (error: unknown) =>
      toast.error(extractErrorMessage(error, "Đối chiếu đề xuất thất bại.")),
  });
  const reviewMutation = useMutation({
    mutationFn: (decision: "approved" | "rejected") => {
      if (!activeRev?.id) throw new Error("Chưa có bản sửa đổi để duyệt.");
      if (
        decision === "approved" &&
        (semanticReview.isFetching ||
          semanticReview.isPending ||
          semanticReview.isError)
      )
        throw new Error("Cần tải đầy đủ nội dung đối chiếu trước khi duyệt.");
      if (
        decision === "approved" &&
        semanticProposal?.status === "proposed" &&
        !hasReviewedSemantics
      )
        throw new Error(
          "Hãy đối chiếu và xác nhận đề xuất ngữ nghĩa trước khi duyệt.",
        );
      return knowledgeApi.reviewSourceRevision(
        collectionId,
        sourceId,
        activeRev.id,
        decision,
        reviewComment.trim() || undefined,
        semanticProposal?.status === "proposed"
          ? semanticProposal.proposal_hash
          : undefined,
      );
    },
    onSuccess: async (_revision, decision) => {
      await refreshSourceQueries(queryClient, collectionId, sourceId);
      toast.success(
        decision === "approved"
          ? "Đã phê duyệt bản sửa đổi thành công."
          : "Đã từ chối bản sửa đổi.",
      );
      setIsReviewDialogOpen(false);
      setReviewComment("");
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Phê duyệt thất bại."));
    },
  });

  // Studio & Reparse States
  const [isReparseDialogOpen, setIsReparseDialogOpen] = useState(false);
  const [reparseProfile, setReparseProfile] = useState<
    "vision_ocr" | "standard" | "layout_analysis"
  >("vision_ocr");
  const [reparseEngine, setReparseEngine] = useState<string>("auto");

  // 6. Mutation Reparse Source (chống chạy trùng qua Backend)
  const reparseMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.reparseSource(collectionId, sourceId, {
        parser_profile: reparseProfile,
        ocr_engine: reparseEngine === "auto" ? undefined : reparseEngine,
      }),
    onSuccess: async (revision) => {
      toast.success("Đã xếp hàng bóc tách lại. Trạng thái sẽ tự cập nhật.");
      setIsReparseDialogOpen(false);
      await refreshSourceQueries(queryClient, collectionId, sourceId);
      setSelectedRevisionId(revision.id);
    },
    onError: (err: unknown) => {
      toast.error(extractErrorMessage(err, "Bóc tách lại thất bại."));
    },
  });

  if (isSourceLoading) {
    return (
      <div className="py-24 text-center text-xs text-muted-foreground flex flex-col items-center justify-center gap-2">
        <RefreshCw className="size-5 animate-spin text-primary" />
        <span>Đang tải thông tin nguồn tri thức...</span>
      </div>
    );
  }

  if (isSourceError || !source) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState
          icon={AlertCircle}
          title="Không tìm thấy nguồn tri thức"
          description={extractErrorMessage(
            sourceError,
            "Nguồn tri thức không tồn tại hoặc đã bị gỡ bỏ.",
          )}
          action={{
            label: "Quay lại Kho tri thức",
            onClick: () =>
              navigate({
                to: "/knowledge/$collectionId",
                params: { collectionId },
              }),
          }}
        />
      </div>
    );
  }

  const qualityReport = activeRev?.quality_report || {};
  const violations = qualityReport.violations || [];
  const qualityScore = qualityReport.quality_score;

  if (
    revisionId &&
    !source.revisions.some((revision) => revision.id === revisionId)
  ) {
    return (
      <EmptyState
        title="Không tìm thấy bản nguồn"
        description="Bản trong đường dẫn không thuộc nguồn này. Hãy mở bản hiện tại."
        action={{
          label: "Bản hiện tại",
          onClick: () => setSelectedRevisionId(""),
        }}
      />
    );
  }

  if (isStudioMode && collection) {
    return (
      <>
        {activeRev && (
          <div className="mb-3 flex justify-end">
            <SourceContextEditor
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={activeRev.id}
              onSaved={setSelectedRevisionId}
            />
          </div>
        )}
        <DocumentStudioWorkspace
          collection={collection}
          documentId={sourceId}
          revisionId={activeRev?.id}
          backLabel="Chi tiết nguồn"
          onBack={() => onStudioModeChange(false)}
          onApproveSuccess={(savedRevisionId) => {
            if (savedRevisionId) setSelectedRevisionId(savedRevisionId);
          }}
        />
      </>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      <div className="flex flex-wrap gap-3 items-center justify-between">
        {activeRev && (
          <SourceContextEditor
            collectionId={collectionId}
            sourceId={sourceId}
            revisionId={activeRev.id}
            onSaved={setSelectedRevisionId}
          />
        )}
        <Select
          value={activeRev?.id || ""}
          onValueChange={setSelectedRevisionId}
          disabled={
            isEditingMarkdown ||
            updateContentMutation.isPending ||
            reviewMutation.isPending ||
            reparseMutation.isPending
          }
        >
          <SelectTrigger className="w-full sm:w-72" aria-label="Bản bóc tách">
            <SelectValue placeholder="Chọn bản bóc tách" />
          </SelectTrigger>
          <SelectContent>
            {source.revisions.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                v{r.revision_no} · {r.status}
                {r.id === source.active_source_revision?.id
                  ? " · Đang áp dụng"
                  : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DeleteSourceButton
          sourceId={sourceId}
          status={source.status}
          title={sourceId}
          onDeleted={() =>
            navigate({
              to: "/knowledge/$collectionId",
              params: { collectionId },
            })
          }
        />
      </div>
      {/* 1. Header & Navigation Breadcrumb */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div className="space-y-1">
          <BackButton
            label="Kho"
            className="-ml-3"
            onClick={() =>
              navigate({
                to: "/knowledge/$collectionId",
                params: { collectionId },
              })
            }
          />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              to="/knowledge"
              className="hover:text-foreground transition-colors"
            >
              Kho Tri Thức
            </Link>
            <span>/</span>
            <Link
              to="/knowledge/$collectionId"
              params={{ collectionId }}
              className="hover:text-foreground transition-colors"
            >
              {collection?.name || "Kho"}
            </Link>
            <span>/</span>
            <span className="text-foreground font-medium">Chi tiết nguồn</span>
          </div>

          <div className="flex items-center gap-2.5 pt-1">
            <h1 className="text-lg sm:text-xl font-bold text-foreground">
              Chi Tiết Nguồn Tri Thức
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto flex-wrap">
          {canReviewSemantics && (
            <>
              <Button
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => onStudioModeChange(true)}
              >
                <Scan className="size-3.5" />
                <span>Bóc tách & Studio OCR</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs gap-1.5"
                onClick={() => setIsReparseDialogOpen(true)}
              >
                <RefreshCw className="size-3.5" />
                <span>Bóc tách lại</span>
              </Button>
            </>
          )}
          {source.repository_document_id && (
            <Button
              asChild
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
            >
              <Link
                to="/documents/$documentId"
                params={{ documentId: source.repository_document_id }}
              >
                <ExternalLink className="size-3.5" />
                <span>Xem tệp gốc trong Kho lưu trữ</span>
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* 2. Snapshot Provenance Ribbon */}
      <details>
        <summary className="cursor-pointer text-sm text-muted-foreground">
          Thông tin tài liệu
        </summary>
        <Card className="border border-border/70 shadow-xs bg-muted/20">
          <CardContent className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-muted-foreground text-[11px] block">
                Tài liệu gốc (Repository Doc)
              </span>
              <span className="font-mono font-medium text-foreground block truncate">
                {source.repository_document_id}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground text-[11px] block">
                Mã băm tệp gốc (SHA-256)
              </span>
              <span
                className="font-mono text-muted-foreground text-[11px] block truncate"
                title={activeRev?.origin_file_hash}
              >
                {activeRev?.origin_file_hash
                  ? `${activeRev.origin_file_hash.slice(0, 16)}...`
                  : "—"}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground text-[11px] block">
                Bản sửa đổi hiện hành (Revision)
              </span>
              <span className="font-semibold text-foreground">
                v{activeRev?.revision_no ?? 1} ({activeRev?.status ?? "—"})
              </span>
            </div>
            <div>
              <span className="text-muted-foreground text-[11px] block">
                Ngày nạp (Snapshot Date)
              </span>
              <span className="text-foreground">
                {new Date(source.created_at).toLocaleDateString("vi-VN")}
              </span>
            </div>
          </CardContent>
        </Card>
      </details>

      <IngestionReadinessPanel
        readiness={activeRev?.ingestion_readiness}
        isReady={
          activeRev?.status === "ready" && !activeRev.requires_structured_review
        }
        isProcessing={[
          "queued",
          "extracting",
          "normalizing",
          "validating",
        ].includes(activeRev?.status ?? "")}
        onViewMarkdown={() => {
          setActiveTab("content");
          setIsMarkdownVisible(true);
        }}
        onAdvanced={
          canReviewSemantics ? () => setIsReviewDialogOpen(true) : undefined
        }
        vectorAction={
          <VectorLoadControls
            collectionId={collectionId}
            targets={
              activeRev?.id &&
              activeRev.status === "ready" &&
              !activeRev.requires_structured_review &&
              source.active_source_revision_id === activeRev.id
                ? [{ binding_id: sourceId, source_revision_id: activeRev.id }]
                : []
            }
            disabledReason={
              !rbac.isAccessVerified ||
              rbac.isDemoMode ||
              !rbac.can("ai.knowledge.upload")
                ? "Bạn chưa có quyền nạp vector."
                : activeRev?.status !== "ready" ||
                    activeRev.requires_structured_review ||
                    source.active_source_revision_id !== activeRev.id
                  ? "Nội dung chưa sẵn sàng để nạp vector."
                  : undefined
            }
          />
        }
      />

      {/* 4. Tab Navigation */}
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as typeof activeTab)}
        className="space-y-4"
      >
        <TabsList className="bg-muted/50 p-1">
          <TabsTrigger value="content" className="text-xs gap-1.5">
            <FileText className="size-3.5" />
            <span>Markdown Chuẩn</span>
          </TabsTrigger>
          <TabsTrigger value="quality" className="text-xs gap-1.5">
            <ShieldCheck className="size-3.5" />
            <span>
              Quality Gate{" "}
              {qualityScore !== undefined ? `(${qualityScore}đ)` : ""}
            </span>
          </TabsTrigger>
          <TabsTrigger value="chunks" className="text-xs gap-1.5">
            <Layers className="size-3.5" />
            <span>Tập Đoạn Cắt Chunks ({chunkSets.length})</span>
          </TabsTrigger>
          <TabsTrigger value="revisions" className="text-xs gap-1.5">
            <History className="size-3.5" />
            <span>Lịch Sử Bản Bóc Tách ({source.revisions.length})</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Canonical Markdown Content */}
        <TabsContent value="content" className="space-y-3">
          {activeRev && (
            <KnowledgeWikiPanel
              key={activeRev.id}
              collectionId={collectionId}
              sourceId={sourceId}
              revisionId={activeRev.id}
            />
          )}
          {!isMarkdownVisible && (
            <p className="text-sm text-muted-foreground">
              Dùng Xem Markdown để mở nội dung đã chuẩn hóa.
            </p>
          )}
          {isMarkdownVisible &&
            (activeRev?.qnu_markdown_status === "ready" ? (
              <QnuStandardEditor
                key={activeRev.id}
                collectionId={collectionId}
                sourceId={sourceId}
                revision={activeRev}
                onSaved={setSelectedRevisionId}
              />
            ) : (
              <>
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs text-muted-foreground">
                    {isEditingMarkdown
                      ? "Chế độ hiệu đính Markdown: Bạn có thể chỉnh sửa cấu trúc văn bản hoặc tiêu đề trước khi lập chỉ mục."
                      : "Nội dung Markdown đã được chuẩn hóa qua tầng bóc tách và làm sạch Unicode NFC."}
                  </div>

                  <div className="flex items-center gap-2">
                    {isEditingMarkdown ? (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-xs"
                          onClick={() => {
                            setIsEditingMarkdown(false);
                            setEditedMarkdown(
                              activeRev?.canonical_markdown || "",
                            );
                          }}
                        >
                          Hủy
                        </Button>
                        <Button
                          size="sm"
                          className="h-8 text-xs gap-1.5"
                          disabled={updateContentMutation.isPending}
                          onClick={() => updateContentMutation.mutate()}
                        >
                          {updateContentMutation.isPending ? (
                            <RefreshCw className="size-3.5 animate-spin" />
                          ) : (
                            <Save className="size-3.5" />
                          )}
                          <span>Lưu Thay Đổi</span>
                        </Button>
                      </>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs gap-1.5"
                        onClick={() => setIsEditingMarkdown(true)}
                      >
                        <Pencil className="size-3.5" />
                        <span>Hiệu đính Markdown</span>
                      </Button>
                    )}
                  </div>
                </div>

                <Card className="border border-border">
                  <CardContent className="p-4">
                    {isEditingMarkdown ? (
                      <div className="space-y-3">
                        <Textarea
                          aria-label="Lý do hiệu đính"
                          value={editReason}
                          maxLength={2000}
                          onChange={(e) => setEditReason(e.target.value)}
                          placeholder="Lý do hiệu đính sau khi đối chiếu nguồn…"
                          rows={2}
                        />
                        <Textarea
                          value={editedMarkdown}
                          onChange={(e) => setEditedMarkdown(e.target.value)}
                          rows={20}
                          className="font-mono text-xs leading-relaxed resize-y bg-background"
                        />
                        <p className="text-xs text-muted-foreground">
                          Tạo revision chờ duyệt; không thay nguồn/vector đang
                          xuất bản. Dùng Studio để đối chiếu và kiểm tra chi
                          tiết.
                        </p>
                      </div>
                    ) : activeRev?.canonical_markdown ? (
                      <pre className="font-mono text-xs leading-relaxed text-foreground whitespace-pre-wrap max-h-[600px] overflow-y-auto p-2">
                        {activeRev.canonical_markdown}
                      </pre>
                    ) : (
                      <div className="py-12 text-center text-xs text-muted-foreground">
                        Chưa có nội dung Markdown cho bản sửa đổi này.
                      </div>
                    )}
                  </CardContent>
                </Card>
              </>
            ))}
        </TabsContent>

        {/* Tab 2: Quality Gate */}
        <TabsContent value="quality" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-semibold text-foreground">
                    Báo Cáo Đánh Giá Chất Lượng (Quality Gate Report)
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Tự động kiểm tra tính toàn vẹn văn bản, độ dài, mật độ ký tự
                    rác và cấu trúc bảng.
                  </CardDescription>
                </div>
                {qualityScore !== undefined && (
                  <div className="text-right">
                    <span className="text-[11px] text-muted-foreground block">
                      Điểm chất lượng
                    </span>
                    <span
                      className={`text-lg font-bold ${
                        qualityScore >= 80
                          ? "text-success"
                          : qualityScore >= 60
                            ? "text-warning"
                            : "text-destructive"
                      }`}
                    >
                      {qualityScore} / 100
                    </span>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              {violations.length === 0 ? (
                <div className="py-8 text-center text-xs text-success flex flex-col items-center justify-center gap-2">
                  <CheckCircle2 className="size-8" />
                  <span className="font-medium">
                    Tài liệu đạt 100% tiêu chuẩn chất lượng Quality Gate.
                  </span>
                </div>
              ) : (
                <div className="space-y-2">
                  <h5 className="text-xs font-semibold text-foreground">
                    Danh sách cảnh báo & vi phạm ({violations.length})
                  </h5>
                  <div className="space-y-2">
                    {violations.map((v) => (
                      <div
                        key={`${v.rule_name}:${v.description}:${v.snippet ?? ""}`}
                        className={`p-3 rounded-md border text-xs flex items-start gap-2.5 ${
                          v.level === "error"
                            ? "border-destructive/30 bg-destructive/5 text-destructive"
                            : "border-warning/30 bg-warning/5 text-warning"
                        }`}
                      >
                        {v.level === "error" ? (
                          <XCircle className="size-4 shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle className="size-4 shrink-0 mt-0.5" />
                        )}
                        <div className="space-y-0.5">
                          <span className="font-semibold block font-mono text-[11px]">
                            {v.rule_name}
                          </span>
                          <p className="text-foreground text-[11px]">
                            {v.description}
                          </p>
                          {v.snippet && (
                            <pre className="text-[10px] bg-muted/50 p-1.5 rounded font-mono mt-1 text-muted-foreground">
                              {v.snippet}
                            </pre>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 3: Chunk Sets */}
        <TabsContent value="chunks" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold text-foreground">
                Tập Đoạn Cắt Chunks (Parse Once, Chunk Once, Embed Many)
              </CardTitle>
              <CardDescription className="text-xs">
                Các đoạn văn bản đã được phân tách và lưu cố định, tái sử dụng
                độc lập cho nhiều mô hình vector.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {isChunkSetsLoading ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Đang tải danh sách chunk sets...
                </div>
              ) : chunkSets.length === 0 ? (
                <div className="p-8 text-center text-xs text-muted-foreground">
                  Nguồn này chưa được phân đoạn chunks.
                </div>
              ) : (
                <Table>
                  <TableHeader className="bg-muted/30">
                    <TableRow className="text-xs h-9">
                      <TableHead>Chiến lược</TableHead>
                      <TableHead className="w-24 text-center">
                        Số Chunks
                      </TableHead>
                      <TableHead className="w-24 text-center">
                        Số Facts
                      </TableHead>
                      <TableHead className="w-32">Mã băm cấu hình</TableHead>
                      <TableHead className="w-24 text-center">
                        Trạng thái
                      </TableHead>
                      <TableHead className="w-32 text-right">
                        Ngày tạo
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {chunkSets.map((cs) => (
                      <TableRow key={cs.id} className="text-xs h-11">
                        <TableCell className="font-semibold text-foreground">
                          {cs.chunk_strategy}
                        </TableCell>
                        <TableCell className="text-center font-bold text-primary">
                          {cs.chunk_count}
                        </TableCell>
                        <TableCell className="text-center text-muted-foreground">
                          {cs.fact_count}
                        </TableCell>
                        <TableCell className="font-mono text-[11px] text-muted-foreground">
                          {cs.config_hash.slice(0, 10)}...
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge
                            variant="outline"
                            className="bg-success/10 text-success border-success/30 text-[10px]"
                          >
                            {cs.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {new Date(cs.created_at).toLocaleDateString("vi-VN")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 4: Revisions History */}
        <TabsContent value="revisions" className="space-y-4">
          <Card className="border border-border">
            <CardHeader className="p-4 pb-3 border-b border-border">
              <CardTitle className="text-sm font-semibold text-foreground">
                Lịch Sử Các Bản Bóc Tách Nội Dung (Revisions)
              </CardTitle>
              <CardDescription className="text-xs">
                Lịch sử bóc tách, chuẩn hóa và hiệu đính thủ công của nguồn tri
                thức.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader className="bg-muted/30">
                  <TableRow className="text-xs h-9">
                    <TableHead className="w-24 text-center">Bản số</TableHead>
                    <TableHead>Mã sửa đổi</TableHead>
                    <TableHead className="w-32 text-center">
                      Trạng thái
                    </TableHead>
                    <TableHead className="w-36">Cập nhật lần cuối</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {source.revisions.map((rev) => (
                    <TableRow key={rev.id} className="text-xs h-11">
                      <TableCell className="text-center font-bold">
                        v{rev.revision_no}
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {rev.id}
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${
                            rev.status === "ready"
                              ? "bg-success/10 text-success border-success/30"
                              : rev.status === "review_required"
                                ? "bg-warning/10 text-warning border-warning/30"
                                : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {rev.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(rev.updated_at).toLocaleDateString("vi-VN")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Review Dialog */}
      <Dialog
        open={isReviewDialogOpen}
        onOpenChange={(isOpen) => {
          if (!isSmartApprovalPending) setIsReviewDialogOpen(isOpen);
        }}
      >
        <DialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] flex-col gap-0 p-0 sm:max-w-2xl">
          <DialogHeader className="border-b bg-muted/20 p-4">
            <DialogTitle className="text-base font-bold text-foreground">
              Đối chiếu nâng cao
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Đối chiếu diễn giải và phạm vi dành cho quản trị. Nội dung nguồn
              đạt kiểm tra có thể nạp vector độc lập với proposal chưa duyệt.
            </DialogDescription>
          </DialogHeader>

          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-sm">
            {semanticReview.isPending && (
              <p role="status">Đang tải nội dung đối chiếu...</p>
            )}
            {semanticReview.isError && (
              <p role="alert" className="text-destructive">
                Không tải được đề xuất. Hãy đóng và mở lại hộp thoại.
              </p>
            )}
            {semanticProposal?.status === "unavailable" && (
              <p role="alert" className="text-destructive">
                Chưa tạo được đề xuất ngữ nghĩa. Cần xử lý lỗi bóc tách trước
                khi duyệt.
              </p>
            )}
            <SmartApprovalPanel
              key={`${semanticReviewKey}:${activeRev?.canonical_hash}:${semanticProposal?.status}`}
              disabled={
                !canReviewSemantics ||
                !activeRev?.canonical_hash ||
                semanticReview.isFetching ||
                semanticReview.isPending ||
                semanticReview.isError ||
                isSmartApprovalPending ||
                semanticMutation.isPending ||
                reviewMutation.isPending ||
                proposalMutation.isPending
              }
              onBusyChange={setIsSmartApprovalPending}
              onApprove={async () => {
                if (!activeRev?.id || !activeRev.canonical_hash)
                  throw new Error("Chưa có phiên bản để duyệt.");
                const result = await knowledgeApi.smartApproveSource(
                  collectionId,
                  sourceId,
                  activeRev.id,
                  {
                    expected_canonical_hash: activeRev.canonical_hash,
                    expected_semantic_proposal_hash:
                      semanticProposal?.proposal_hash ?? null,
                    policy_version: "2026-10-19.1",
                    idempotency_key: crypto.randomUUID(),
                    comment:
                      reviewComment.trim().length >= 3
                        ? reviewComment.trim()
                        : undefined,
                  },
                );
                if (result.approved) {
                  toast.success(result.message);
                  await refreshSourceQueries(
                    queryClient,
                    collectionId,
                    sourceId,
                  );
                  await queryClient.invalidateQueries({
                    queryKey: [
                      "source-semantic-review",
                      collectionId,
                      sourceId,
                    ],
                  });
                  setIsReviewDialogOpen(false);
                  setReviewComment("");
                }
                return result;
              }}
              onError={(error) =>
                toast.error(
                  extractErrorMessage(
                    error,
                    "Không thể kiểm tra và duyệt nguồn.",
                  ),
                )
              }
            />
            <details className="space-y-3">
              <summary className="cursor-pointer font-medium">
                Xem chi tiết đối chiếu
              </summary>
              <div className="space-y-4 pt-3">
                <Button
                  type="button"
                  variant="outline"
                  disabled={
                    !canReviewSemantics ||
                    isSmartApprovalPending ||
                    semanticMutation.isPending ||
                    reviewMutation.isPending ||
                    proposalMutation.isPending ||
                    semanticReview.isFetching ||
                    semanticReview.isError ||
                    reviewComment.trim().length < 3 ||
                    (semanticIsPending && !hasReviewedSemantics)
                  }
                  onClick={() => reviewMutation.mutate("approved")}
                >
                  Duyệt sau đối chiếu thủ công
                </Button>
                <p className="text-muted-foreground">
                  Chỉ dùng thao tác thủ công sau khi đã đọc và xử lý các mục bên
                  dưới. Các quy tắc chặn hiện hành vẫn áp dụng.
                </p>

                {activeRev?.status === "review_required" &&
                  !semanticIsPending &&
                  semanticProposal?.status !== "verified" && (
                    <SemanticCheckpointImport
                      key={`${activeRev.id}:${semanticProposal?.proposal_hash ?? "empty"}`}
                      canImport={canReviewSemantics && !isSmartApprovalPending}
                      onImport={async (checkpoint, comment) => {
                        if (!canReviewSemantics)
                          throw new Error("Bạn chưa có quyền nhập đề xuất.");
                        await knowledgeApi.importSemanticCheckpoint(
                          collectionId,
                          sourceId,
                          activeRev.id,
                          checkpoint,
                          comment,
                          semanticProposal?.proposal_hash,
                        );
                        setReviewedSemanticKey(null);
                        setContextSelection({ key: "", decisions: [] });
                        await refreshSourceQueries(
                          queryClient,
                          collectionId,
                          sourceId,
                        );
                        await queryClient.invalidateQueries({
                          queryKey: [
                            "source-semantic-review",
                            collectionId,
                            sourceId,
                          ],
                        });
                        toast.success(
                          "Đã tạo đề xuất chờ đối chiếu. Chưa áp dụng hoặc xuất bản.",
                        );
                      }}
                    />
                  )}
                {semanticReview.data?.structured_artifact?.input_format ===
                  "qnu-rag-projection/v1" &&
                  activeRev?.status === "review_required" &&
                  !["proposed", "verified"].includes(
                    semanticProposal?.status ?? "",
                  ) && (
                    <Button
                      type="button"
                      variant="outline"
                      disabled={
                        proposalMutation.isPending ||
                        isSmartApprovalPending ||
                        semanticMutation.isPending ||
                        reviewMutation.isPending ||
                        semanticReview.isFetching
                      }
                      onClick={() => proposalMutation.mutate()}
                    >
                      {proposalMutation.isPending
                        ? "Đang đọc ngữ nghĩa..."
                        : "Tạo đề xuất đối chiếu qua ModelOps"}
                    </Button>
                  )}
                {semanticReview.data?.structured_artifact && (
                  <SemanticReviewPreview
                    artifact={semanticReview.data.structured_artifact}
                    decisions={contextDecisions}
                    key={semanticReviewKey}
                    onDecision={
                      canReviewSemantics
                        ? (decision, issueId) =>
                            setContextSelection({
                              key: semanticReviewKey,
                              decisions: [
                                ...contextDecisions.filter(
                                  (item) => item.issue_id !== issueId,
                                ),
                                ...(decision ? [decision] : []),
                              ],
                            })
                        : undefined
                    }
                  />
                )}
                {semanticIsPending && (
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={
                      isSmartApprovalPending ||
                      semanticMutation.isPending ||
                      reviewMutation.isPending ||
                      proposalMutation.isPending ||
                      semanticReview.isFetching ||
                      !hasReviewedSemantics ||
                      reviewComment.trim().length < 3
                    }
                    onClick={() => semanticMutation.mutate("rejected")}
                  >
                    Bỏ đề xuất
                  </Button>
                )}
                {semanticIsPending && (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      isSmartApprovalPending ||
                      semanticMutation.isPending ||
                      reviewMutation.isPending ||
                      proposalMutation.isPending ||
                      semanticReview.isFetching ||
                      !hasReviewedSemantics ||
                      reviewComment.trim().length < 3
                    }
                    onClick={() => semanticMutation.mutate("changes_requested")}
                  >
                    Yêu cầu kiểm tra tiếp
                  </Button>
                )}
                {semanticIsPending && (
                  <label
                    htmlFor="review-semantic-proposals"
                    className="flex items-start gap-2"
                  >
                    <Checkbox
                      id="review-semantic-proposals"
                      checked={hasReviewedSemantics}
                      onCheckedChange={(checked) =>
                        setReviewedSemanticKey(
                          checked === true ? semanticReviewKey : null,
                        )
                      }
                    />
                    Tôi đã đối chiếu trích đoạn và toàn bộ phạm vi nêu trên. Nếu
                    xác nhận giới hạn nguồn, tôi xác nhận kết quả kiểm tra trong
                    chính phạm vi này; không suy nghĩa cho ô còn chưa rõ.
                  </label>
                )}
                <div className="space-y-1.5">
                  <div className="font-medium text-foreground block">
                    Yêu cầu xử lý thủ công
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      type="button"
                      variant={
                        reviewDecision === "rejected"
                          ? "destructive"
                          : "outline"
                      }
                      onClick={() => setReviewDecision("rejected")}
                      className="h-9 text-xs gap-1.5"
                    >
                      <XCircle className="size-3.5" />
                      <span>Từ chối (Reject)</span>
                    </Button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label
                    htmlFor="source-review-comment"
                    className="font-medium text-foreground block"
                  >
                    Ghi chú đối chiếu (bắt buộc với bản hiệu đính)
                  </label>
                  <Textarea
                    id="source-review-comment"
                    value={reviewComment}
                    onChange={(e) => setReviewComment(e.target.value)}
                    placeholder="Nhập lý do phê duyệt hoặc yêu cầu chỉnh sửa..."
                    rows={3}
                    className="text-xs resize-none"
                  />
                </div>
                {semanticIsPending && (
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      isSmartApprovalPending ||
                      semanticMutation.isPending ||
                      reviewMutation.isPending ||
                      proposalMutation.isPending ||
                      semanticReview.isFetching ||
                      !hasReviewedSemantics ||
                      reviewComment.trim().length < 3 ||
                      contextApplyBlocked
                    }
                    onClick={() =>
                      semanticMutation.mutate(
                        semanticProposal.annotations?.limitations?.length
                          ? "acknowledged_limits"
                          : "approved",
                      )
                    }
                  >
                    {semanticMutation.isPending
                      ? "Đang áp dụng..."
                      : semanticProposal.annotations?.limitations?.length
                        ? "Xác nhận giới hạn nguồn và diễn giải kèm theo"
                        : "Duyệt diễn giải có bằng chứng"}
                  </Button>
                )}
              </div>
            </details>
          </div>

          <DialogFooter className="border-t bg-card p-4">
            <Button
              type="button"
              variant="ghost"
              disabled={isSmartApprovalPending}
              onClick={() => setIsReviewDialogOpen(false)}
            >
              Hủy
            </Button>
            {reviewDecision === "rejected" && (
              <Button
                type="button"
                variant="destructive"
                disabled={
                  reviewMutation.isPending ||
                  isSmartApprovalPending ||
                  semanticMutation.isPending ||
                  proposalMutation.isPending
                }
                onClick={() => reviewMutation.mutate("rejected")}
              >
                {reviewMutation.isPending
                  ? "Đang xử lý..."
                  : "Xác nhận từ chối"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Bóc Tách Lại */}
      <Dialog open={isReparseDialogOpen} onOpenChange={setIsReparseDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold">
              Bóc Tách Lại Nguồn Tri Thức
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground">
              Thực hiện bóc tách lại từ tệp snapshot nhị phân độc lập. Không phụ
              thuộc vào việc tệp gốc còn trong Kho tài liệu hay không.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <div className="space-y-1.5">
              <label
                htmlFor="reparse-profile-select"
                className="text-xs font-semibold text-foreground block"
              >
                Cấu hình bộ bóc tách (Parser Profile)
              </label>
              <Select
                value={reparseProfile}
                onValueChange={(v) =>
                  setReparseProfile(
                    v as "vision_ocr" | "standard" | "layout_analysis",
                  )
                }
              >
                <SelectTrigger
                  id="reparse-profile-select"
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Chọn profile" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="vision_ocr">
                    Vision OCR (PaddleOCR-VL Bóc Tách Khung & Bảng)
                  </SelectItem>
                  <SelectItem value="standard">
                    Standard (Native Document Parser)
                  </SelectItem>
                  <SelectItem value="layout_analysis">
                    Layout Analysis (Phân tích bố cục tài liệu)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="reparse-engine-select"
                className="text-xs font-semibold text-foreground block"
              >
                Động cơ OCR (OCR Engine)
              </label>
              <Select value={reparseEngine} onValueChange={setReparseEngine}>
                <SelectTrigger
                  id="reparse-engine-select"
                  className="h-8 text-xs"
                >
                  <SelectValue placeholder="Chọn động cơ" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">
                    Tự động phân giải (Auto Pipeline)
                  </SelectItem>
                  <SelectItem value="paddleocr">
                    PaddleOCR-VL (Layout & Table Detection)
                  </SelectItem>
                  <SelectItem value="gemini_vision">
                    Google Gemini Vision
                  </SelectItem>
                  <SelectItem value="mistral_ocr">Mistral OCR</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsReparseDialogOpen(false)}
              disabled={reparseMutation.isPending}
            >
              Hủy
            </Button>
            <Button
              type="button"
              disabled={reparseMutation.isPending}
              onClick={() => reparseMutation.mutate()}
              className="gap-1.5"
            >
              {reparseMutation.isPending ? (
                <RefreshCw className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              <span>Bắt Đầu Bóc Tách Lại</span>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
