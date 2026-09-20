import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, FileSpreadsheet, FileText, Scan } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "../components/admin/confirm-dialog";
import { CollectionHeader } from "../components/knowledge/collection-header";
import { CollectionConfigDialog } from "../components/knowledge/dialogs/collection-config-dialog";
import { CollectionExcelImportDialog } from "../components/knowledge/dialogs/collection-excel-import-dialog";
import { CollectionReconcileDialog } from "../components/knowledge/dialogs/collection-reconcile-dialog";
import { DocumentPreviewDialog } from "../components/knowledge/dialogs/document-preview-dialog";
import { TaskLogDialog } from "../components/knowledge/dialogs/task-log-dialog";
import { CollectionDocumentsTab } from "../components/knowledge/tabs/collection-documents-tab";
import { CollectionFactsTab } from "../components/knowledge/tabs/collection-facts-tab";
import { CollectionPlaygroundTab } from "../components/knowledge/tabs/collection-playground-tab";
import { CollectionTasksTab } from "../components/knowledge/tabs/collection-tasks-tab";
import type {
  CollectionDetailTab,
  CollectionSubView,
  SandboxSearchResult,
} from "../components/knowledge/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  type IngestionTask,
  type KnowledgeCollection,
  type KnowledgeDocument,
  type KnowledgeReconciliationReport,
  apiClient,
} from "../services/api-client";
import { knowledgeApi } from "../services/knowledge-api";
import { DocumentIngestPage } from "./document-ingest-page";
import { ScanStudioPage } from "./scan-studio-page";

export interface CollectionDetailPageProps {
  collectionId: string;
  onBack: () => void;
  onNavigate?: (path: string) => void;
  initialSubView?: CollectionSubView;
  initialVerifyDocId?: string;
}

export function CollectionDetailPage({
  collectionId,
  onBack,
  onNavigate: _onNavigate,
  initialSubView = "list",
  initialVerifyDocId,
}: CollectionDetailPageProps) {
  const queryClient = useQueryClient();

  // Subview navigation: "list" | "ingest" | "verify"
  const [subView, setSubView] = useState<CollectionSubView>(initialSubView);
  const [verifyDocId, setVerifyDocId] = useState<string>(initialVerifyDocId || "");

  // Tabs on List view: "documents" | "facts" | "tasks" | "playground"
  const [detailTab, setDetailTab] = useState<CollectionDetailTab>("documents");

  // Filter & Search states for Documents
  const [docSearchQuery, setDocSearchQuery] = useState<string>("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState<string>("all");

  // Filter & Search states for Tasks
  const [taskSearchQuery, setTaskSearchQuery] = useState<string>("");
  const [taskStatusFilter, setTaskStatusFilter] = useState<string>("all");

  // Dialog preview doc & task log states
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(null);

  // Reindex state
  const [isReindexing, setIsReindexing] = useState<boolean>(false);
  const [reindexingDocId, setReindexingDocId] = useState<string | null>(null);

  // Reconcile state
  const [isReconcileOpen, setIsReconcileOpen] = useState<boolean>(false);
  const [reconcileReport, setReconcileReport] = useState<KnowledgeReconciliationReport | null>(
    null
  );
  const [isLoadingReconcile, setIsLoadingReconcile] = useState<boolean>(false);
  const [isFixingReconcile, setIsFixingReconcile] = useState<boolean>(false);

  // Document action states
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  // Task action states
  const [taskActionId, setTaskActionId] = useState<string | null>(null);
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

  // Playground state
  const [sandboxQuery, setSandboxQuery] = useState<string>("");
  const [isSearchingSandbox, setIsSearchingSandbox] = useState<boolean>(false);
  const [sandboxResults, setSandboxResults] = useState<SandboxSearchResult[] | null>(null);

  // Facts layer state & queries
  const [factsSearchQuery, setFactsSearchQuery] = useState<string>("");
  const [isExcelImportOpen, setIsExcelImportOpen] = useState<boolean>(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);

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

  // Fetch facts
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
    try {
      await apiClient.reindexCollection(currentCollection.id);
      toast.success("Đã kích hoạt tái lập chỉ mục toàn bộ kho tri thức.");
      refreshTasks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Tạo job reindex thất bại.");
    } finally {
      setIsReindexing(false);
    }
  };

  const handleDownloadDocument = async (doc: KnowledgeDocument) => {
    setDownloadingId(doc.id);
    try {
      await apiClient.downloadDocument(doc.id, doc.filename);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Tải tệp gốc thất bại.");
    } finally {
      setDownloadingId(null);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await apiClient.deleteDocument(deleteTarget.id);
      toast.success(`Đã xóa tài liệu "${deleteTarget.title}" vĩnh viễn.`);
      setDeleteTarget(null);
      refreshDocuments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Xóa tài liệu thất bại.");
    } finally {
      setIsDeleting(false);
    }
  };

  const handleQuickApproveDoc = async (docId: string) => {
    try {
      await apiClient.approveDocument(docId);
      toast.success("Đã phê duyệt và lập chỉ mục Vector thành công!");
      refreshDocuments();
      refreshTasks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.");
    }
  };

  const handleBatchApproveDocs = async (docIds: string[]) => {
    try {
      const res = await apiClient.batchApproveDocuments(docIds);
      toast.success(
        `Đã phê duyệt thành công ${res.approved.length} tài liệu (${res.indexed_chunks} chunks).`
      );
      if (res.failed.length > 0) {
        toast.warning(`${res.failed.length} tài liệu cần thẩm định do có cảnh báo.`);
      }
      refreshDocuments();
      refreshTasks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Phê duyệt hàng loạt thất bại.");
    }
  };

  const handleBatchDeleteDocs = async (docIds: string[]) => {
    try {
      for (const id of docIds) {
        await apiClient.deleteDocument(id);
      }
      toast.success(`Đã xóa ${docIds.length} tài liệu thành công.`);
      refreshDocuments();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Xóa hàng loạt thất bại.");
    }
  };

  const handleTaskAction = async (taskId: string, action: "retry" | "cancel") => {
    setTaskActionId(taskId);
    try {
      if (action === "retry") {
        await apiClient.retryJob(taskId);
        toast.success("Đã gửi yêu cầu chạy lại tác vụ.");
      } else {
        await apiClient.cancelJob(taskId);
        toast.success("Đã hủy tác vụ.");
      }
      refreshTasks();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Thao tác job thất bại.");
    } finally {
      setTaskActionId(null);
    }
  };

  const handleConfirmDeleteTask = async () => {
    if (!deleteTaskTarget) return;
    setIsDeletingTask(true);
    try {
      await apiClient.deleteJob(deleteTaskTarget.id);
      setDeleteTaskTarget(null);
      refreshTasks();
      setTaskSuccessMessage("Đã xóa tác vụ thành công.");
      setTimeout(() => setTaskSuccessMessage(null), 3000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Xóa tác vụ thất bại.");
    } finally {
      setIsDeletingTask(false);
    }
  };

  const handleCleanupTasks = async () => {
    setIsCleaningTasks(true);
    try {
      const res = await apiClient.cleanupJobs(currentCollection.id);
      setIsConfirmCleanupOpen(false);
      refreshTasks();
      setTaskSuccessMessage(`Đã dọn dẹp ${res.deleted_count} tác vụ đã kết thúc.`);
      setTimeout(() => setTaskSuccessMessage(null), 4000);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Dọn dẹp tác vụ thất bại.");
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
      toast.error("Tên kho tri thức không được để trống.");
      return;
    }
    setIsSavingConfig(true);
    try {
      await apiClient.updateCollection(currentCollection.id, {
        name: configName.trim(),
        description: configDescription.trim(),
      });
      toast.success("Cập nhật cấu hình kho thành công.");
      setIsConfigOpen(false);
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Cập nhật kho tri thức thất bại.");
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSandboxSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sandboxQuery.trim()) return;
    setIsSearchingSandbox(true);
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
        toast.info("Không tìm thấy chunk phù hợp trong kho này.");
      }
    } catch (err) {
      setSandboxResults(null);
      toast.error(err instanceof Error ? err.message : "Truy vấn thử thất bại.");
    } finally {
      setIsSearchingSandbox(false);
    }
  };

  const handleOpenReconcile = async () => {
    setIsReconcileOpen(true);
    setIsLoadingReconcile(true);
    try {
      const report = await apiClient.reconcileCollection(currentCollection.id);
      setReconcileReport(report);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Không tải được báo cáo đối soát.");
    } finally {
      setIsLoadingReconcile(false);
    }
  };

  const handleFixReconciliation = async () => {
    setIsFixingReconcile(true);
    try {
      const res = await apiClient.fixReconciliation(currentCollection.id);
      toast.success(res.message);
      const report = await apiClient.reconcileCollection(currentCollection.id);
      setReconcileReport(report);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Đồng bộ đối soát thất bại.");
    } finally {
      setIsFixingReconcile(false);
    }
  };

  const handleReindexDoc = async (docId: string) => {
    setReindexingDocId(docId);
    try {
      const res = await apiClient.reindexDocument(docId);
      if (res.index_status === "indexed") {
        toast.success(`Lập chỉ mục thành công ${res.indexed_chunks} chunks.`);
      } else {
        toast.error(`Lỗi: ${res.message}`);
      }
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Lập chỉ mục thất bại.");
    } finally {
      setReindexingDocId(null);
    }
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
      <ScanStudioPage
        collectionId={currentCollection.id}
        documentId={verifyDocId || allDocuments[0]?.id || "doc_ts_2026"}
        onBack={() => setSubView("list")}
        onApproveSuccess={() => {
          setSubView("list");
          queryClient.invalidateQueries({ queryKey: ["documents"] });
          queryClient.invalidateQueries({ queryKey: ["collections"] });
        }}
        onNavigate={_onNavigate}
      />
    );
  }

  // SUBVIEW 3: MASTER DETAIL VIEW WITH 4 TABS
  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <CollectionHeader
        collection={currentCollection}
        documentCount={allDocuments.length}
        systemDefaultEmbeddingModel={systemDefaults?.default_embedding_model}
        isReindexing={isReindexing}
        onBack={onBack}
        onOpenReconcile={handleOpenReconcile}
        onReindex={handleReindex}
        onOpenConfig={openConfigDialog}
        onStartIngest={() => setSubView("ingest")}
        actionError={null}
        reindexJobId={null}
      />

      {/* Tabs Layout */}
      <Tabs
        value={detailTab}
        onValueChange={(val) => setDetailTab(val as CollectionDetailTab)}
        className="space-y-4"
      >
        <div className="border-b border-border pb-px">
          <TabsList className="bg-muted/50 p-1 rounded-lg border border-border h-10">
            <TabsTrigger
              value="documents"
              className="text-xs data-[state=active]:bg-background data-[state=active]:text-foreground font-medium gap-1.5 px-3"
            >
              <FileText className="size-3.5" />
              <span>Danh mục tài liệu ({allDocuments.length})</span>
            </TabsTrigger>
            <TabsTrigger
              value="facts"
              className="text-xs data-[state=active]:bg-background data-[state=active]:text-foreground font-medium gap-1.5 px-3"
            >
              <FileSpreadsheet className="size-3.5" />
              <span>Facts & Số liệu ({factsQuery.data?.total || 0})</span>
            </TabsTrigger>
            <TabsTrigger
              value="tasks"
              className="text-xs data-[state=active]:bg-background data-[state=active]:text-foreground font-medium gap-1.5 px-3"
            >
              <Activity className="size-3.5" />
              <span>Hàng đợi & Tác vụ ngầm ({allTasks.length})</span>
            </TabsTrigger>
            <TabsTrigger
              value="playground"
              className="text-xs data-[state=active]:bg-background data-[state=active]:text-foreground font-medium gap-1.5 px-3"
            >
              <Scan className="size-3.5" />
              <span>Truy vấn thử nghiệm (Playground)</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* TAB 1: DANH MỤC TÀI LIỆU */}
        <TabsContent value="documents" className="space-y-4 mt-0">
          <CollectionDocumentsTab
            documents={filteredDocuments}
            totalDocumentsCount={allDocuments.length}
            searchQuery={docSearchQuery}
            onSearchChange={setDocSearchQuery}
            typeFilter={selectedTypeFilter}
            onTypeFilterChange={setSelectedTypeFilter}
            statusFilter={selectedStatusFilter}
            onStatusFilterChange={setSelectedStatusFilter}
            priorityFilter={selectedPriorityFilter}
            onPriorityFilterChange={setSelectedPriorityFilter}
            reindexingDocId={reindexingDocId}
            downloadingId={downloadingId}
            onReindexDoc={handleReindexDoc}
            onStartVerify={(docId: string) => {
              if (_onNavigate) {
                _onNavigate(
                  `/knowledge/documents/${encodeURIComponent(docId)}/ocr?collectionId=${encodeURIComponent(currentCollection.id)}`
                );
              } else {
                setVerifyDocId(docId);
                setSubView("verify");
              }
            }}
            onPreviewDoc={setPreviewDoc}
            onDownloadDoc={handleDownloadDocument}
            onDeleteDoc={setDeleteTarget}
            onQuickApprove={handleQuickApproveDoc}
            onBatchApprove={handleBatchApproveDocs}
            onBatchDelete={handleBatchDeleteDocs}
          />
        </TabsContent>

        {/* TAB 2: FACTS & SỐ LIỆU */}
        <TabsContent value="facts" className="space-y-4 mt-0">
          <CollectionFactsTab
            facts={filteredFacts}
            totalCount={factsQuery.data?.total || 0}
            searchQuery={factsSearchQuery}
            onSearchChange={setFactsSearchQuery}
            isLoading={factsQuery.isLoading}
            isFetching={factsQuery.isFetching}
            onRefresh={() => factsQuery.refetch()}
            onOpenExcelImport={() => setIsExcelImportOpen(true)}
          />
        </TabsContent>

        {/* TAB 3: HÀNG ĐỢI & TÁC VỤ NGẦM */}
        <TabsContent value="tasks" className="space-y-4 mt-0">
          <CollectionTasksTab
            tasks={filteredTasks}
            totalTasksCount={allTasks.length}
            searchQuery={taskSearchQuery}
            onSearchChange={setTaskSearchQuery}
            statusFilter={taskStatusFilter}
            onStatusFilterChange={setTaskStatusFilter}
            taskActionId={taskActionId}
            isCleaningTasks={isCleaningTasks}
            canCleanup={filteredTasks.some((t) =>
              ["completed", "failed", "cancelled"].includes(t.status)
            )}
            taskSuccessMessage={taskSuccessMessage}
            onRefresh={refreshTasks}
            onOpenConfirmCleanup={() => setIsConfirmCleanupOpen(true)}
            onViewLog={setSelectedTaskLog}
            onTaskAction={handleTaskAction}
            onDeleteTask={setDeleteTaskTarget}
          />
        </TabsContent>

        {/* TAB 4: PLAYGROUND */}
        <TabsContent value="playground" className="space-y-4 mt-0">
          <CollectionPlaygroundTab
            sandboxQuery={sandboxQuery}
            setSandboxQuery={setSandboxQuery}
            isSearchingSandbox={isSearchingSandbox}
            sandboxResults={sandboxResults}
            onSandboxSearch={handleSandboxSearch}
          />
        </TabsContent>
      </Tabs>

      {/* DIALOG 1: Worker Terminal Log */}
      <TaskLogDialog
        open={Boolean(selectedTaskLog)}
        onOpenChange={(open) => {
          if (!open) setSelectedTaskLog(null);
        }}
        task={selectedTaskLog}
      />

      {/* DIALOG 2: Quick Document Preview */}
      <DocumentPreviewDialog
        open={Boolean(previewDoc)}
        onOpenChange={(open) => {
          if (!open) setPreviewDoc(null);
        }}
        document={previewDoc}
        collectionName={currentCollection.name}
      />

      {/* DIALOG 3: Collection Config */}
      <CollectionConfigDialog
        open={isConfigOpen}
        onOpenChange={setIsConfigOpen}
        configName={configName}
        setConfigName={setConfigName}
        configDescription={configDescription}
        setConfigDescription={setConfigDescription}
        isSaving={isSavingConfig}
        onSave={handleSaveConfig}
      />

      {/* DIALOG 4: Excel Facts Import */}
      <CollectionExcelImportDialog
        open={isExcelImportOpen}
        onOpenChange={setIsExcelImportOpen}
        selectedFile={selectedExcelFile}
        setSelectedFile={setSelectedExcelFile}
        isPending={importExcelMutation.isPending}
        onImport={(file) => importExcelMutation.mutate(file)}
      />

      {/* DIALOG 5: Reconciliation Audit */}
      <CollectionReconcileDialog
        open={isReconcileOpen}
        onOpenChange={setIsReconcileOpen}
        collectionCode={currentCollection.code}
        reconcileReport={reconcileReport}
        isLoading={isLoadingReconcile}
        isFixing={isFixingReconcile}
        onRefresh={handleOpenReconcile}
        onFix={handleFixReconciliation}
      />

      {/* CONFIRM DIALOGS */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="Xóa tài liệu?"
        description={`Tài liệu "${deleteTarget?.title}" sẽ bị xóa vĩnh viễn khỏi kho, storage và vector index. Hành động này không thể hoàn tác.`}
        confirmText="Xóa vĩnh viễn"
        onConfirm={handleConfirmDelete}
        isPending={isDeleting}
      />

      <ConfirmDialog
        open={Boolean(deleteTaskTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTaskTarget(null);
        }}
        title="Xóa bản ghi tác vụ?"
        description={`Tác vụ "${deleteTaskTarget?.task_name}" (${deleteTaskTarget?.id}) sẽ bị xóa khỏi danh sách lịch sử. Hành động này không thể hoàn tác.`}
        confirmText="Xóa tác vụ"
        onConfirm={handleConfirmDeleteTask}
        isPending={isDeletingTask}
      />

      <ConfirmDialog
        open={isConfirmCleanupOpen}
        onOpenChange={setIsConfirmCleanupOpen}
        title="Dọn dẹp các tác vụ đã kết thúc?"
        description={`Toàn bộ tác vụ đã hoàn tất, thất bại hoặc đã hủy trong kho "${currentCollection.name}" sẽ được dọn dẹp khỏi danh sách.`}
        confirmText="Xác nhận dọn dẹp"
        onConfirm={handleCleanupTasks}
        isPending={isCleaningTasks}
      />
    </div>
  );
}
