import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowLeft,
  Bot,
  CheckCircle2,
  CircleAlert,
  Cpu,
  Download,
  Eye,
  FileSpreadsheet,
  FileText,
  RefreshCw,
  RotateCcw,
  Scan,
  Search,
  Settings,
  Table2,
  Terminal,
  Trash2,
  Upload,
  X,
  Zap,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "../components/admin/confirm-dialog";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { cn } from "../lib/utils";
import {
  type IngestionTask,
  type KnowledgeCollection,
  type KnowledgeDocument,
  apiClient,
} from "../services/api-client";
import { knowledgeApi } from "../services/knowledge-api";
import { DocumentIngestPage } from "./document-ingest-page";
import { DocumentVerificationStudioPage } from "./document-verification-studio-page";

export interface CollectionDetailPageProps {
  collectionId: string;
  onBack: () => void;
  onNavigate?: (path: string) => void;
  initialSubView?: "list" | "ingest" | "verify";
  initialVerifyDocId?: string;
}

export const CollectionDetailPage: React.FC<CollectionDetailPageProps> = ({
  collectionId,
  onBack,
  onNavigate: _onNavigate,
  initialSubView = "list",
  initialVerifyDocId,
}) => {
  const queryClient = useQueryClient();

  // Subview navigation: "list" | "ingest" | "verify"
  const [subView, setSubView] = useState<"list" | "ingest" | "verify">(initialSubView);
  const [verifyDocId, setVerifyDocId] = useState<string>(initialVerifyDocId || "");

  // Tabs on List view: "documents" | "tasks" | "playground"
  const [detailTab, setDetailTab] = useState<string>("documents");

  // Filter & Search states
  const [docSearchQuery, setDocSearchQuery] = useState<string>("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState<string>("all");

  const [taskSearchQuery, setTaskSearchQuery] = useState<string>("");
  const [taskStatusFilter, setTaskStatusFilter] = useState<string>("all");

  // Dialog preview doc state
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(null);

  // Reindex state
  const [isReindexing, setIsReindexing] = useState<boolean>(false);
  const [reindexJobId, setReindexJobId] = useState<string | null>(null);

  // Row-level + header action states
  const [actionError, setActionError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [taskActionId, setTaskActionId] = useState<string | null>(null);

  // Task delete & cleanup states
  const [deleteTaskTarget, setDeleteTaskTarget] = useState<IngestionTask | null>(null);
  const [isDeletingTask, setIsDeletingTask] = useState<boolean>(false);
  const [isCleaningTasks, setIsCleaningTasks] = useState<boolean>(false);
  const [isConfirmCleanupOpen, setIsConfirmCleanupOpen] = useState<boolean>(false);
  const [taskSuccessMessage, setTaskSuccessMessage] = useState<string | null>(null);

  // Collection config dialog state
  const [isConfigOpen, setIsConfigOpen] = useState<boolean>(false);
  const [configName, setConfigName] = useState<string>("");
  const [configDescription, setConfigDescription] = useState<string>("");
  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);

  const STATUS_BADGE: Record<string, { label: string; className: string }> = {
    approved: {
      label: "Hiệu lực",
      className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-200",
    },
    completed: {
      label: "Hiệu lực",
      className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-200",
    },
    pending: {
      label: "Chờ duyệt",
      className: "bg-amber-500/10 text-amber-600 border-amber-500/30",
    },
    processing: {
      label: "Đang xử lý",
      className: "bg-sky-500/10 text-sky-600 border-sky-500/30",
    },
    archived: {
      label: "Lưu trữ",
      className: "bg-muted text-muted-foreground border-border",
    },
    failed: {
      label: "Lỗi",
      className: "bg-rose-500/10 text-rose-600 border-rose-500/30",
    },
  };

  const TASK_STATUS_BADGE: Record<string, { label: string; className: string }> = {
    completed: {
      label: "Hoàn tất",
      className: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 border-emerald-300",
    },
    processing: {
      label: "Đang xử lý",
      className: "bg-sky-500/10 text-sky-600 border-sky-500/30",
    },
    failed: {
      label: "Thất bại",
      className: "bg-rose-500/10 text-rose-600 border-rose-500/30",
    },
    cancelled: {
      label: "Đã hủy",
      className: "bg-muted text-muted-foreground border-border",
    },
  };

  // Playground state
  const [sandboxQuery, setSandboxQuery] = useState<string>("");
  const [isSearchingSandbox, setIsSearchingSandbox] = useState<boolean>(false);
  const [sandboxResults, setSandboxResults] = useState<
    | { id: string; title: string; clause: string; text: string; score: number; method: string }[]
    | null
  >(null);

  // Fetch collections
  const { data: collections = [] } = useQuery({
    queryKey: ["collections"],
    queryFn: () => apiClient.getCollections(),
  });

  // Fetch system-wide model defaults (Embedding, Reranker, OCR)
  const { data: systemDefaultsResponse } = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    staleTime: 30000,
  });
  const systemDefaults = systemDefaultsResponse?.defaults;

  const currentCollection = useMemo<KnowledgeCollection>(() => {
    const found = collections.find((c) => c.id === collectionId || c.code === collectionId);
    if (found) return found;
    return {
      id: collectionId,
      code: "admissions",
      name: "Kho Tri thức Tuyển sinh Đại học",
      description:
        "Lưu trữ đề án tuyển sinh, điểm chuẩn, tổ hợp xét tuyển và chỉ tiêu hàng năm của Đại học Quy Nhơn.",
      document_count: 1,
      chunk_count: 10,
      chunking_strategy: "SemanticChunker",
      ocr_profile: "Docling",
      embedding_model: "BAAI/bge-m3 (1024-dim)",
      status: "ready",
      updated_at: "19:48 12/09/2026",
    };
  }, [collections, collectionId]);

  // Fetch documents for this collection
  const { data: allDocuments = [] } = useQuery({
    queryKey: ["documents", currentCollection.id],
    queryFn: () => apiClient.getDocuments(currentCollection.id),
  });

  // Fetch ingestion tasks
  const { data: allTasks = [] } = useQuery({
    queryKey: ["ingestion-tasks", currentCollection.id],
    queryFn: () => apiClient.getIngestionTasks(currentCollection.id),
  });

  // Facts layer state & queries
  const [factsSearchQuery, setFactsSearchQuery] = useState<string>("");
  const [isExcelImportOpen, setIsExcelImportOpen] = useState<boolean>(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);

  const factsQuery = useQuery({
    queryKey: ["collection-facts", currentCollection.id],
    queryFn: () => knowledgeApi.getCollectionFacts(currentCollection.id),
    enabled: Boolean(currentCollection.id),
  });

  const importExcelMutation = useMutation({
    mutationFn: (file: File) => knowledgeApi.importFactsExcel(currentCollection.id, file),
    onSuccess: (res) => {
      toast.success(res.message || `Đã nạp thành công ${res.imported_count} số liệu!`);
      setIsExcelImportOpen(false);
      setSelectedExcelFile(null);
      queryClient.invalidateQueries({ queryKey: ["collection-facts", currentCollection.id] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
    onError: (err: Error) => toast.error(`Nạp bảng tính thất bại: ${err.message}`),
  });

  const filteredFacts = useMemo(() => {
    const list = factsQuery.data?.facts || [];
    if (!factsSearchQuery.trim()) return list;
    const q = factsSearchQuery.toLowerCase();
    return list.filter(
      (f) =>
        f.entity_name.toLowerCase().includes(q) ||
        f.attribute_name.toLowerCase().includes(q) ||
        f.attribute_value.toLowerCase().includes(q)
    );
  }, [factsQuery.data?.facts, factsSearchQuery]);

  // Filtered documents
  const filteredDocuments = useMemo(() => {
    return allDocuments.filter((d) => {
      const matchSearch =
        !docSearchQuery.trim() ||
        d.title.toLowerCase().includes(docSearchQuery.toLowerCase()) ||
        d.filename.toLowerCase().includes(docSearchQuery.toLowerCase());
      const matchType =
        selectedTypeFilter === "all" || (d.document_type || "Quy chế") === selectedTypeFilter;
      const matchStatus =
        selectedStatusFilter === "all" || (d.status || "completed") === selectedStatusFilter;
      const matchPriority =
        selectedPriorityFilter === "all" || (d.priority_level || "core") === selectedPriorityFilter;
      return matchSearch && matchType && matchStatus && matchPriority;
    });
  }, [
    allDocuments,
    docSearchQuery,
    selectedTypeFilter,
    selectedStatusFilter,
    selectedPriorityFilter,
  ]);

  // Filtered tasks
  const filteredTasks = useMemo(() => {
    return allTasks.filter((t) => {
      const matchSearch =
        !taskSearchQuery.trim() ||
        t.task_name.toLowerCase().includes(taskSearchQuery.toLowerCase()) ||
        t.source_file.toLowerCase().includes(taskSearchQuery.toLowerCase()) ||
        t.worker_name.toLowerCase().includes(taskSearchQuery.toLowerCase());
      const matchStatus = taskStatusFilter === "all" || t.status === taskStatusFilter;
      return matchSearch && matchStatus;
    });
  }, [allTasks, taskSearchQuery, taskStatusFilter]);

  const refreshDocuments = () => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["collections"] });
  };

  const refreshTasks = () => {
    queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] });
  };

  const handleReindex = async () => {
    setIsReindexing(true);
    setActionError(null);
    try {
      const job = await apiClient.reindexCollection(currentCollection.id);
      setReindexJobId(job.job_id);
      refreshTasks();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Tạo job reindex thất bại.");
    } finally {
      setIsReindexing(false);
    }
  };

  const handleDownloadDocument = async (doc: KnowledgeDocument) => {
    setDownloadingId(doc.id);
    setActionError(null);
    try {
      await apiClient.downloadDocument(doc.id, doc.filename);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Tải tệp gốc thất bại.");
    } finally {
      setDownloadingId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    setActionError(null);
    try {
      await apiClient.deleteDocument(deleteTarget.id);
      setDeleteTarget(null);
      refreshDocuments();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Xóa tài liệu thất bại.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleTaskAction = async (taskId: string, action: "retry" | "cancel") => {
    setTaskActionId(taskId);
    setActionError(null);
    try {
      if (action === "retry") {
        await apiClient.retryJob(taskId);
      } else {
        await apiClient.cancelJob(taskId);
      }
      refreshTasks();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Thao tác job thất bại.");
    } finally {
      setTaskActionId(null);
    }
  };

  const handleConfirmDeleteTask = async () => {
    if (!deleteTaskTarget) return;
    setIsDeletingTask(true);
    setActionError(null);
    try {
      await apiClient.deleteJob(deleteTaskTarget.id);
      setDeleteTaskTarget(null);
      refreshTasks();
      setTaskSuccessMessage("Đã xóa tác vụ thành công.");
      setTimeout(() => setTaskSuccessMessage(null), 3000);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Xóa tác vụ thất bại.");
    } finally {
      setIsDeletingTask(false);
    }
  };

  const handleCleanupTasks = async () => {
    setIsCleaningTasks(true);
    setActionError(null);
    try {
      const res = await apiClient.cleanupJobs(currentCollection.id);
      setIsConfirmCleanupOpen(false);
      refreshTasks();
      setTaskSuccessMessage(`Đã dọn dẹp ${res.deleted_count} tác vụ đã kết thúc.`);
      setTimeout(() => setTaskSuccessMessage(null), 4000);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Dọn dẹp tác vụ thất bại.");
    } finally {
      setIsCleaningTasks(false);
    }
  };

  const openConfigDialog = () => {
    setConfigName(currentCollection.name);
    setConfigDescription(currentCollection.description || "");
    setIsConfigOpen(true);
  };

  const handleSaveConfig = async () => {
    if (!configName.trim()) {
      setActionError("Tên kho tri thức không được để trống.");
      return;
    }
    setIsSavingConfig(true);
    setActionError(null);
    try {
      await apiClient.updateCollection(currentCollection.id, {
        name: configName.trim(),
        description: configDescription.trim(),
      });
      setIsConfigOpen(false);
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Cập nhật kho tri thức thất bại.");
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSandboxSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sandboxQuery.trim()) return;
    setIsSearchingSandbox(true);
    setActionError(null);
    try {
      const items = await apiClient.testCollection(currentCollection.id, sandboxQuery.trim(), 5);
      setSandboxResults(
        items.map((item) => ({
          id: item.chunk_id,
          title: currentCollection.name,
          clause: item.section || `Tài liệu ${item.document_id}`,
          text: item.content,
          score: item.score,
          method: "Hybrid RRF (Dense BGE-M3 + Postgres FTS)",
        }))
      );
      if (items.length === 0) {
        setActionError("Không tìm thấy chunk phù hợp trong kho này.");
      }
    } catch (err) {
      setSandboxResults(null);
      setActionError(err instanceof Error ? err.message : "Truy vấn thử thất bại.");
    } finally {
      setIsSearchingSandbox(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  // SUBVIEW 1: INGEST FORM
  if (subView === "ingest") {
    return (
      <DocumentIngestPage
        collection={currentCollection}
        onBack={() => setSubView("list")}
        onStartVerification={(docId) => {
          setVerifyDocId(docId);
          setSubView("verify");
        }}
      />
    );
  }

  // SUBVIEW 2: SPLIT-PANE VERIFICATION STUDIO
  if (subView === "verify") {
    return (
      <DocumentVerificationStudioPage
        collectionId={currentCollection.id}
        documentId={verifyDocId || allDocuments[0]?.id || "doc_ts_2026"}
        onBackToConfig={() => setSubView("ingest")}
        onCommitSuccess={() => {
          setSubView("list");
          queryClient.invalidateQueries({ queryKey: ["documents"] });
          queryClient.invalidateQueries({ queryKey: ["collections"] });
        }}
      />
    );
  }

  // SUBVIEW 3: MASTER DETAIL VIEW WITH 3 TABS
  return (
    <div className="space-y-6">
      {/* Top Header Card matching Screenshot 2 */}
      <div className="bg-card border border-border rounded-lg p-5 sm:p-6 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={onBack}
              className="size-9 rounded-md shrink-0 text-muted-foreground hover:text-foreground"
              title="Quay lại danh sách kho"
            >
              <ArrowLeft className="size-4" />
            </Button>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-lg sm:text-xl font-bold text-foreground">
                  {currentCollection.name}
                </h1>
                <Badge
                  variant="outline"
                  className="bg-emerald-500/10 text-emerald-600 border-emerald-500/30 font-medium text-[11px]"
                >
                  Sẵn sàng
                </Badge>
                <span className="font-mono text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                  {currentCollection.code}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {currentCollection.description}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReindex}
              disabled={isReindexing}
              className="h-8 text-xs gap-1.5"
            >
              <RefreshCw
                className={`size-3.5 ${isReindexing ? "animate-spin text-primary" : ""}`}
              />
              <span>{isReindexing ? "Đang Reindex..." : "Reindex Kho"}</span>
            </Button>

            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs gap-1.5"
              onClick={openConfigDialog}
            >
              <Settings className="size-3.5" />
              <span>Cấu hình</span>
            </Button>

            <Button
              size="sm"
              onClick={() => setSubView("ingest")}
              className="h-8 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium shadow-sm"
            >
              <Upload className="size-3.5" />
              <span>+ Nạp tài liệu</span>
            </Button>
          </div>
        </div>

        {/* Sub Meta Info Line */}
        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/60 flex-wrap">
          <span className="flex items-center gap-1.5 font-mono text-[11px] text-primary">
            {(
              currentCollection.embedding_model ||
              systemDefaults?.default_embedding_model ||
              ""
            ).includes("@cf/") ? (
              <Zap className="size-3.5 text-amber-500 shrink-0" />
            ) : (
              <Cpu className="size-3.5 shrink-0" />
            )}
            <span>
              {currentCollection.embedding_model ||
                systemDefaults?.default_embedding_model ||
                "BAAI/bge-m3 (1024-dim)"}
            </span>
            {!currentCollection.embedding_model && systemDefaults?.default_embedding_model && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 border-primary/30 text-primary bg-primary/5 font-sans font-normal"
              >
                Mặc định hệ thống
              </Badge>
            )}
          </span>
          <span>•</span>
          <span className="text-[11px]">Cập nhật: {currentCollection.updated_at}</span>
          <span>•</span>
          <span className="text-[11px] font-medium text-foreground">
            {allDocuments.length} văn bản ({currentCollection.chunk_count} chunks)
          </span>
          {reindexJobId && (
            <span className="text-[11px] text-emerald-600 font-semibold ml-auto flex items-center gap-1">
              <CheckCircle2 className="size-3.5" /> Đã tạo job reindex ({reindexJobId}) — theo dõi ở
              tab Tác vụ!
            </span>
          )}
        </div>
        {actionError && (
          <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/30 text-xs text-destructive leading-relaxed">
            <CircleAlert className="size-4 shrink-0 mt-0.5" />
            <span>{actionError}</span>
          </div>
        )}
      </div>

      {/* 3 Main Sub-Tabs */}
      <Tabs value={detailTab} onValueChange={setDetailTab} className="space-y-4">
        <TabsList className="bg-muted/60 p-1 rounded-md border border-border">
          <TabsTrigger value="documents" className="text-xs px-3.5 py-1.5 gap-1.5">
            <FileText className="size-3.5" />
            <span>Danh mục Tài liệu ({allDocuments.length})</span>
          </TabsTrigger>
          <TabsTrigger value="facts" className="text-xs px-3.5 py-1.5 gap-1.5">
            <Table2 className="size-3.5 text-primary" />
            <span>Bảng Biểu & Số Liệu ({factsQuery.data?.total ?? 0})</span>
          </TabsTrigger>
          <TabsTrigger value="tasks" className="text-xs px-3.5 py-1.5 gap-1.5">
            <Activity className="size-3.5" />
            <span>Tiến trình & Lịch sử Tác vụ ({allTasks.length})</span>
          </TabsTrigger>
          <TabsTrigger value="playground" className="text-xs px-3.5 py-1.5 gap-1.5">
            <Bot className="size-3.5" />
            <span>Hỏi Thử Nghiệm trong Kho (Playground)</span>
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: DANH MỤC TÀI LIỆU */}
        <TabsContent value="documents" className="space-y-4 mt-0">
          {/* Search and Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border">
            <div className="flex items-center gap-2 w-full sm:w-80">
              <Search className="size-4 text-muted-foreground shrink-0" />
              <Input
                placeholder="Tìm tiêu đề, tên tệp..."
                value={docSearchQuery}
                onChange={(e) => setDocSearchQuery(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto flex-wrap justify-end">
              <Select value={selectedTypeFilter} onValueChange={setSelectedTypeFilter}>
                <SelectTrigger sizeVariant="sm" className="w-[160px]">
                  <SelectValue placeholder="Tất cả loại văn bản" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả loại văn bản</SelectItem>
                  <SelectItem value="Quy chế">Quy chế</SelectItem>
                  <SelectItem value="Đề án">Đề án</SelectItem>
                  <SelectItem value="Nghị định">Nghị định</SelectItem>
                </SelectContent>
              </Select>

              <Select value={selectedStatusFilter} onValueChange={setSelectedStatusFilter}>
                <SelectTrigger sizeVariant="sm" className="w-[165px]">
                  <SelectValue placeholder="Tất cả trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả trạng thái</SelectItem>
                  <SelectItem value="pending">Chờ duyệt</SelectItem>
                  <SelectItem value="approved">Đã duyệt (Hiệu lực)</SelectItem>
                  <SelectItem value="completed">Hiệu lực</SelectItem>
                  <SelectItem value="processing">Đang xử lý</SelectItem>
                  <SelectItem value="archived">Lưu trữ</SelectItem>
                  <SelectItem value="failed">Lỗi</SelectItem>
                </SelectContent>
              </Select>

              <Select value={selectedPriorityFilter} onValueChange={setSelectedPriorityFilter}>
                <SelectTrigger sizeVariant="sm" className="w-[170px]">
                  <SelectValue placeholder="Tất cả mức ưu tiên" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả mức ưu tiên</SelectItem>
                  <SelectItem value="core">Ưu tiên Cao (Cốt lõi)</SelectItem>
                  <SelectItem value="high">Ưu tiên Trung bình</SelectItem>
                </SelectContent>
              </Select>

              <span className="text-xs text-muted-foreground ml-2">
                Hiển thị {filteredDocuments.length} / {allDocuments.length} tài liệu
              </span>
            </div>
          </div>

          {/* Documents Table */}
          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead className="w-10 text-center">
                    <input type="checkbox" className="rounded border-border size-3.5" />
                  </TableHead>
                  <TableHead>Tài liệu & Tên tệp gốc</TableHead>
                  <TableHead>Loại văn bản</TableHead>
                  <TableHead>Chunks Vector</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredDocuments.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      Không tìm thấy tài liệu phù hợp trong kho này.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredDocuments.map((doc) => (
                    <TableRow key={doc.id} className="hover:bg-muted/30 transition-colors">
                      <TableCell className="text-center">
                        <input type="checkbox" className="rounded border-border size-3.5" />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-start gap-3">
                          <div className="flex size-8 items-center justify-center rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 shrink-0 mt-0.5">
                            <FileText className="size-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-xs text-foreground hover:text-primary transition-colors cursor-pointer">
                              {doc.title}
                            </p>
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
                              <span>{doc.filename}</span>
                              <span>•</span>
                              <span>{formatFileSize(doc.file_size)}</span>
                              <span>•</span>
                              <span className="text-primary font-medium">
                                {doc.version || "v1.0"}
                              </span>
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <span className="text-xs text-foreground font-medium block">
                            {doc.document_type || "Quy chế"}
                          </span>
                          <Badge
                            variant="outline"
                            className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                          >
                            Ưu tiên Cao (Cốt lõi)
                          </Badge>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="font-semibold text-xs text-emerald-600 font-mono">
                          {doc.chunk_count} chunks
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`text-[11px] ${
                            STATUS_BADGE[doc.status]?.className || STATUS_BADGE.pending.className
                          }`}
                        >
                          {STATUS_BADGE[doc.status]?.label || doc.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => {
                              setVerifyDocId(doc.id);
                              setSubView("verify");
                            }}
                            className="size-7 text-muted-foreground hover:text-primary"
                            title="Mở Studio Bóc Tách & Đối Soát (Split-Pane)"
                          >
                            <Scan className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setPreviewDoc(doc)}
                            className="size-7 text-muted-foreground hover:text-foreground"
                            title="Xem trước Chunks Inspector"
                          >
                            <Eye className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDownloadDocument(doc)}
                            disabled={downloadingId === doc.id}
                            className="size-7 text-muted-foreground hover:text-foreground"
                            title="Tải tệp gốc"
                          >
                            <Download className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTarget(doc)}
                            className="size-7 text-rose-500 hover:text-rose-600"
                            title="Xóa tài liệu"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* TAB: BẢNG BIỂU SỐ LIỆU (STRUCTURED FACTS LAYER) */}
        <TabsContent value="facts" className="space-y-4 mt-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-lg border border-border">
            <div>
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <Table2 className="size-4 text-primary" />
                <span>Bảng Biểu & Số Liệu Trích Xuất (Facts Layer)</span>
                <Badge variant="outline" className="font-mono text-xs">
                  {factsQuery.data?.total ?? 0} facts
                </Badge>
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Các số liệu chính xác 100% dạng bảng (điểm chuẩn, chỉ tiêu, học phí) được nạp trực
                tiếp từ bảng tính Excel/CSV để Trợ lý AI tra cứu đối soát, chống bịa đặt (Zero
                Hallucination).
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => factsQuery.refetch()}
                disabled={factsQuery.isFetching}
                className="h-8 text-xs gap-1.5"
              >
                <RefreshCw className={cn("size-3.5", factsQuery.isFetching && "animate-spin")} />
                <span>Làm mới</span>
              </Button>
              <Button
                size="sm"
                onClick={() => setIsExcelImportOpen(true)}
                className="h-8 text-xs gap-1.5 bg-primary text-primary-foreground hover:bg-primary/90"
              >
                <FileSpreadsheet className="size-3.5" />
                <span>+ Nạp Bảng Biểu Excel/CSV</span>
              </Button>
            </div>
          </div>

          {/* Search bar for facts */}
          <div className="flex items-center gap-2 bg-card p-3 rounded-lg border border-border">
            <Search className="size-4 text-muted-foreground shrink-0" />
            <Input
              placeholder="Tìm theo thực thể (ngành, khoa), tên thuộc tính (điểm chuẩn, chỉ tiêu) hoặc giá trị..."
              value={factsSearchQuery}
              onChange={(e) => setFactsSearchQuery(e.target.value)}
              className="h-8 text-xs"
            />
            {factsSearchQuery && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs px-2"
                onClick={() => setFactsSearchQuery("")}
              >
                Xóa lọc
              </Button>
            )}
          </div>

          {/* Facts Table */}
          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead>Thực thể (Entity)</TableHead>
                  <TableHead>Phân loại</TableHead>
                  <TableHead>Thuộc tính (Attribute)</TableHead>
                  <TableHead>Giá trị (Value)</TableHead>
                  <TableHead>Độ tin cậy</TableHead>
                  <TableHead>Thời điểm số hóa</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {factsQuery.isLoading ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="text-center py-12 text-xs text-muted-foreground"
                    >
                      Đang tải danh sách bảng biểu số liệu...
                    </TableCell>
                  </TableRow>
                ) : filteredFacts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12 text-muted-foreground">
                      <FileSpreadsheet className="size-8 mx-auto mb-2 opacity-30 text-primary" />
                      <p className="text-sm font-medium text-foreground">
                        {factsSearchQuery
                          ? "Không tìm thấy số liệu phù hợp với từ khóa"
                          : "Chưa có bảng biểu số liệu nào trong kho này"}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1 max-w-md mx-auto">
                        Tải lên tệp Excel (.xlsx) hoặc CSV chứa các cột (Mã ngành, Tên ngành, Điểm
                        chuẩn, Chỉ tiêu, Học phí) để hệ thống tự động bóc tách thành facts tra cứu.
                      </p>
                      {!factsSearchQuery && (
                        <Button
                          size="sm"
                          onClick={() => setIsExcelImportOpen(true)}
                          className="h-8 text-xs gap-1.5 mt-3"
                        >
                          <FileSpreadsheet className="size-3.5" />
                          <span>Tải tệp Excel ngay</span>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredFacts.map((fact) => (
                    <TableRow key={fact.id} className="hover:bg-muted/30 text-xs">
                      <TableCell className="font-semibold text-foreground">
                        {fact.entity_name}
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-[10px] font-normal uppercase">
                          {fact.entity_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-[11px] text-muted-foreground">
                        {fact.attribute_name}
                      </TableCell>
                      <TableCell className="font-semibold text-primary font-mono">
                        {fact.attribute_value}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="default"
                          className="text-[10px] bg-emerald-500/10 text-emerald-600 border-emerald-500/30"
                        >
                          {Math.round(fact.confidence * 100)}%
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-[11px]">
                        {fact.created_at
                          ? new Date(fact.created_at).toLocaleString("vi-VN")
                          : "N/A"}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* TAB 2: TIẾN TRÌNH & LỊCH SỬ TÁC VỤ NGẦM */}
        <TabsContent value="tasks" className="space-y-4 mt-0">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-card p-4 rounded-lg border border-border">
            <div>
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                Hàng Đợi & Lịch Sử Tác Vụ Ngầm ({allTasks.length})
              </h3>
              <p className="text-xs text-muted-foreground mt-0.5">
                Giám sát thời gian thực quá trình Bóc tách (Ingestion), OCR tài liệu và Tái lập chỉ
                mục (Reindex) của kho này.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsConfirmCleanupOpen(true)}
                disabled={
                  isCleaningTasks || allTasks.filter((t) => t.status !== "processing").length === 0
                }
                className="h-8 text-xs text-muted-foreground hover:text-foreground gap-1.5"
                title="Dọn dẹp các tác vụ đã hoàn tất, thất bại hoặc đã hủy"
              >
                <Trash2 className="size-3.5" />
                <span>{isCleaningTasks ? "Đang dọn..." : "Dọn dẹp đã xong"}</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => queryClient.invalidateQueries({ queryKey: ["ingestion-tasks"] })}
                className="h-8 text-xs gap-1.5"
              >
                <RefreshCw className="size-3.5" />
                <span>Làm mới</span>
              </Button>
            </div>
          </div>

          {taskSuccessMessage && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-600">
              <CheckCircle2 className="size-4 shrink-0" />
              <span>{taskSuccessMessage}</span>
            </div>
          )}

          {/* Filter Bar for Tasks */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border">
            <div className="flex items-center gap-2 w-full sm:w-80">
              <Search className="size-4 text-muted-foreground shrink-0" />
              <Input
                placeholder="Tìm tác vụ, tệp, worker..."
                value={taskSearchQuery}
                onChange={(e) => setTaskSearchQuery(e.target.value)}
                className="h-8 text-xs"
              />
            </div>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Select value={taskStatusFilter} onValueChange={setTaskStatusFilter}>
                <SelectTrigger sizeVariant="sm" className="w-[155px]">
                  <SelectValue placeholder="Tất cả trạng thái" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tất cả trạng thái</SelectItem>
                  <SelectItem value="completed">Hoàn tất</SelectItem>
                  <SelectItem value="processing">Đang xử lý</SelectItem>
                  <SelectItem value="cancelled">Đã hủy</SelectItem>
                  <SelectItem value="failed">Thất bại</SelectItem>
                </SelectContent>
              </Select>
              <span className="text-xs text-muted-foreground ml-2">
                Hiển thị {filteredTasks.length} / {allTasks.length} tác vụ
              </span>
            </div>
          </div>

          {/* Tasks Table matching Screenshot 3 */}
          <div className="bg-card rounded-lg border border-border overflow-hidden shadow-xs">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/40 hover:bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase">
                  <TableHead>Tác vụ & Tài nguyên mục tiêu</TableHead>
                  <TableHead>Phân loại</TableHead>
                  <TableHead>Tiến độ</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead>Thời điểm</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.length === 0 ? (
                  <TableRow>
                    <TableCell
                      colSpan={6}
                      className="h-32 text-center text-xs text-muted-foreground"
                    >
                      Không có tác vụ nền nào đang chờ hoặc đã xử lý.
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredTasks.map((t) => (
                    <TableRow key={t.id} className="hover:bg-muted/30 transition-colors">
                      <TableCell>
                        <div className="flex items-start gap-3">
                          <div className="flex size-8 items-center justify-center rounded bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 shrink-0 mt-0.5">
                            <Upload className="size-4" />
                          </div>
                          <div>
                            <p className="font-semibold text-xs text-foreground">{t.task_name}</p>
                            <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono mt-0.5">
                              <span>{t.source_file}</span>
                              <span>•</span>
                              <span>Worker: {t.worker_name}</span>
                              <span>•</span>
                              <span>{t.duration_seconds}s</span>
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs font-medium text-foreground">
                          {t.category === "ingestion"
                            ? "Nạp tài liệu"
                            : t.category === "ocr"
                              ? "OCR & Bóc tách"
                              : "Tái lập chỉ mục"}
                        </span>
                      </TableCell>
                      <TableCell>
                        <div className="w-28 space-y-1">
                          <div className="flex justify-between text-[11px] font-mono">
                            <span className="text-emerald-600 font-bold">
                              {t.progress_percent}%
                            </span>
                            <span className="text-muted-foreground">Xong</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-emerald-600 rounded-full"
                              style={{ width: `${t.progress_percent}%` }}
                            />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`text-[11px] gap-1 ${
                            TASK_STATUS_BADGE[t.status]?.className ||
                            TASK_STATUS_BADGE.processing.className
                          }`}
                        >
                          {t.status === "completed" ? (
                            <CheckCircle2 className="size-3" />
                          ) : t.status === "processing" ? (
                            <RefreshCw className="size-3 animate-spin" />
                          ) : t.status === "cancelled" ? (
                            <X className="size-3" />
                          ) : (
                            <CircleAlert className="size-3" />
                          )}
                          <span>{TASK_STATUS_BADGE[t.status]?.label || t.status}</span>
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <span className="text-xs text-muted-foreground font-mono">
                          {t.created_at}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setSelectedTaskLog(t)}
                            className="size-7 font-mono text-xs text-muted-foreground hover:text-foreground"
                            title="Xem nhật ký Terminal"
                          >
                            <Terminal className="size-3.5" />
                          </Button>
                          {(t.status === "failed" || t.status === "cancelled") && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleTaskAction(t.id, "retry")}
                              disabled={taskActionId === t.id}
                              className="size-7 text-emerald-600 hover:text-emerald-700"
                              title="Chạy lại job"
                            >
                              <RotateCcw className="size-3.5" />
                            </Button>
                          )}
                          {t.status === "processing" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleTaskAction(t.id, "cancel")}
                              disabled={taskActionId === t.id}
                              className="size-7 text-amber-600 hover:text-amber-700"
                              title="Hủy job"
                            >
                              <X className="size-3.5" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTaskTarget(t)}
                            disabled={taskActionId === t.id}
                            className="size-7 text-rose-500 hover:text-rose-600"
                            title="Xóa tác vụ khỏi danh sách"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        {/* TAB 3: PLAYGROUND TRONG KHO */}
        <TabsContent value="playground" className="space-y-4 mt-0">
          <Card className="p-5 border-border">
            <form onSubmit={handleSandboxSearch} className="space-y-3">
              <label
                htmlFor="sandbox-query"
                className="text-xs font-semibold text-foreground block"
              >
                Truy vấn thử nghiệm (Hybrid RRF BGE-M3 + PostgreSQL FTS):
              </label>
              <div className="flex gap-2">
                <Input
                  id="sandbox-query"
                  value={sandboxQuery}
                  onChange={(e) => setSandboxQuery(e.target.value)}
                  placeholder="VD: Điểm chuẩn và phương thức xét tuyển ngành Quản lý giáo dục năm 2026..."
                  className="h-9 text-xs"
                />
                <Button
                  type="submit"
                  disabled={isSearchingSandbox}
                  className="h-9 text-xs gap-1.5 bg-primary text-primary-foreground shrink-0"
                >
                  <Search className="size-3.5" />
                  <span>{isSearchingSandbox ? "Đang tìm..." : "Truy vấn"}</span>
                </Button>
              </div>
            </form>

            {sandboxResults && (
              <div className="mt-5 space-y-3 pt-4 border-t border-border">
                <p className="text-xs font-semibold text-foreground">
                  Kết quả truy xuất ({sandboxResults.length} Chunks phù hợp nhất):
                </p>
                {sandboxResults.map((res) => (
                  <div
                    key={res.id}
                    className="p-3 bg-muted/20 border border-border rounded-lg space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-primary">{res.clause}</span>
                      <Badge variant="secondary" className="font-mono text-[10px]">
                        Điểm phù hợp: {res.score}
                      </Badge>
                    </div>
                    <p className="text-xs text-foreground leading-relaxed">{res.text}</p>
                    <p className="text-[10px] text-muted-foreground font-mono">
                      Phương pháp: {res.method}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>

      {/* Terminal Log Modal for Task */}
      <Dialog open={!!selectedTaskLog} onOpenChange={() => setSelectedTaskLog(null)}>
        <DialogContent className="max-w-2xl bg-slate-950 text-slate-100 font-mono text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-mono text-emerald-400 flex items-center gap-2">
              <Terminal className="size-4" />
              <span>Worker Log: {selectedTaskLog?.worker_name}</span>
            </DialogTitle>
          </DialogHeader>
          <pre className="p-4 bg-slate-900 rounded border border-slate-800 text-[11px] leading-relaxed overflow-x-auto whitespace-pre-wrap">
            {selectedTaskLog?.log_output ||
              "[INFO] Tác vụ đã thực thi thành công không có cảnh báo."}
          </pre>
        </DialogContent>
      </Dialog>

      {/* Delete Document Confirm */}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Xóa tài liệu?"
        description={`Tài liệu "${deleteTarget?.title}" sẽ bị xóa vĩnh viễn khỏi kho, storage và vector index. Hành động này không thể hoàn tác.`}
        confirmText="Xóa vĩnh viễn"
        onConfirm={handleConfirmDelete}
        isPending={isDeleting}
      />

      {/* Delete Task Confirm */}
      <ConfirmDialog
        open={!!deleteTaskTarget}
        onOpenChange={(open) => {
          if (!open) setDeleteTaskTarget(null);
        }}
        title="Xóa bản ghi tác vụ?"
        description={`Tác vụ "${deleteTaskTarget?.task_name}" (${deleteTaskTarget?.id}) sẽ bị xóa khỏi danh sách lịch sử. Hành động này không thể hoàn tác.`}
        confirmText="Xóa tác vụ"
        onConfirm={handleConfirmDeleteTask}
        isPending={isDeletingTask}
      />

      {/* Cleanup Finished Tasks Confirm */}
      <ConfirmDialog
        open={isConfirmCleanupOpen}
        onOpenChange={setIsConfirmCleanupOpen}
        title="Dọn dẹp các tác vụ đã kết thúc?"
        description={`Toàn bộ tác vụ đã hoàn tất, thất bại hoặc đã hủy trong kho "${currentCollection.name}" sẽ được dọn dẹp khỏi danh sách.`}
        confirmText="Xác nhận dọn dẹp"
        onConfirm={handleCleanupTasks}
        isPending={isCleaningTasks}
      />

      {/* Collection Config Dialog */}
      <Dialog open={isConfigOpen} onOpenChange={setIsConfigOpen}>
        <DialogContent className="max-w-md text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <Settings className="size-4 text-primary" />
              <span>Cấu hình kho tri thức</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground block">Tên kho</span>
              <Input
                value={configName}
                onChange={(e) => setConfigName(e.target.value)}
                className="h-9 text-xs"
                placeholder="Tên bộ sưu tập tri thức"
              />
            </div>
            <div className="space-y-1.5">
              <span className="text-xs font-semibold text-foreground block">Mô tả</span>
              <Input
                value={configDescription}
                onChange={(e) => setConfigDescription(e.target.value)}
                className="h-9 text-xs"
                placeholder="Mô tả ngắn về kho tri thức"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                className="h-8 text-xs"
                onClick={() => setIsConfigOpen(false)}
              >
                Hủy bỏ
              </Button>
              <Button
                size="sm"
                className="h-8 text-xs"
                onClick={handleSaveConfig}
                disabled={isSavingConfig}
              >
                {isSavingConfig ? "Đang lưu..." : "Lưu cấu hình"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Document Quick Preview Modal */}
      <Dialog open={!!previewDoc} onOpenChange={() => setPreviewDoc(null)}>
        <DialogContent className="max-w-md text-xs">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <FileText className="size-4 text-primary" />
              <span>{previewDoc?.title}</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="flex justify-between text-muted-foreground font-mono text-[11px] pb-2 border-b border-border">
              <span>Tên tệp: {previewDoc?.filename}</span>
              <span>{previewDoc ? formatFileSize(previewDoc.file_size) : ""}</span>
            </div>
            <p className="text-muted-foreground text-xs leading-relaxed">
              Tài liệu đã được bóc tách và phân đoạn thành công qua engine{" "}
              <strong className="text-foreground">{previewDoc?.ocr_method}</strong> với{" "}
              <strong className="text-primary">{previewDoc?.chunk_count} vector chunks</strong>{" "}
              trong kho tri thức{" "}
              <strong className="text-foreground">{currentCollection.name}</strong>.
            </p>
          </div>
        </DialogContent>
      </Dialog>

      {/* Excel Facts Import Dialog */}
      <Dialog open={isExcelImportOpen} onOpenChange={setIsExcelImportOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-base font-bold">
              <FileSpreadsheet className="size-4 text-primary" />
              <span>Nạp Bảng Biểu Số Liệu (Excel / CSV)</span>
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-2 text-xs">
            <p className="text-muted-foreground leading-relaxed">
              Chọn tệp bảng tính <code>.xlsx</code>, <code>.xls</code> hoặc <code>.csv</code> chứa
              các cột số liệu (Điểm chuẩn, Chỉ tiêu, Học phí, Tổ hợp xét tuyển). Hệ thống sẽ tự động
              bóc tách từng dòng thành các facts định lượng.
            </p>

            <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
              <input
                type="file"
                id="excel-facts-upload"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) setSelectedExcelFile(f);
                }}
              />
              <label htmlFor="excel-facts-upload" className="cursor-pointer block">
                <FileSpreadsheet className="size-10 mx-auto mb-2 text-primary/70" />
                {selectedExcelFile ? (
                  <div>
                    <p className="font-semibold text-foreground text-sm">
                      {selectedExcelFile.name}
                    </p>
                    <p className="text-muted-foreground text-[11px] mt-0.5">
                      {(selectedExcelFile.size / 1024).toFixed(1)} KB — Nhấp để chọn tệp khác
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="font-medium text-foreground">Kéo thả hoặc nhấp để chọn tệp</p>
                    <p className="text-muted-foreground text-[11px] mt-0.5">
                      Hỗ trợ .xlsx, .xls, .csv
                    </p>
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-border">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => {
                setIsExcelImportOpen(false);
                setSelectedExcelFile(null);
              }}
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              className="h-8 text-xs gap-1.5"
              disabled={!selectedExcelFile || importExcelMutation.isPending}
              onClick={() => {
                if (selectedExcelFile) {
                  importExcelMutation.mutate(selectedExcelFile);
                }
              }}
            >
              {importExcelMutation.isPending ? (
                <>
                  <RefreshCw className="size-3.5 animate-spin" />
                  <span>Đang trích xuất...</span>
                </>
              ) : (
                <>
                  <Upload className="size-3.5" />
                  <span>Bắt đầu nạp facts</span>
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
