import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Activity, FileText, Table2, Zap } from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { CollectionHeader } from "@/components/knowledge/collection-header";
import { CollectionConfigDialog } from "@/components/knowledge/dialogs/collection-config-dialog";
import { CollectionExcelImportDialog } from "@/components/knowledge/dialogs/collection-excel-import-dialog";
import { CollectionReconcileDialog } from "@/components/knowledge/dialogs/collection-reconcile-dialog";
import { DocumentPreviewDialog } from "@/components/knowledge/dialogs/document-preview-dialog";
import { DocumentUploadDialog } from "@/components/knowledge/dialogs/document-upload-dialog";
import { TaskLogDialog } from "@/components/knowledge/dialogs/task-log-dialog";
import { CollectionDocumentsTab } from "@/components/knowledge/tabs/collection-documents-tab";
import { CollectionFactsTab } from "@/components/knowledge/tabs/collection-facts-tab";
import { CollectionPlaygroundTab } from "@/components/knowledge/tabs/collection-playground-tab";
import { CollectionTasksTab } from "@/components/knowledge/tabs/collection-tasks-tab";
import type {
  CollectionDetailTab,
  SandboxSearchResult,
} from "@/components/knowledge/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { apiClient } from "@/services/api-client";
import { jobsApi } from "@/services/jobs-api";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  IngestionTask,
  KnowledgeCollection,
  KnowledgeDocument,
  KnowledgeReconciliationReport,
} from "@/types/knowledge";

export interface CollectionDetailPageProps {
  collectionId: string;
}

export const CollectionDetailPage: React.FC<CollectionDetailPageProps> = ({
  collectionId,
}) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Active Tab
  const [activeTab, setActiveTab] = useState<CollectionDetailTab>("documents");

  // Document Filters
  const [docSearchQuery, setDocSearchQuery] = useState("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("all");
  const [selectedPriorityFilter, setSelectedPriorityFilter] = useState("all");

  // Tasks Filters
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
  const [taskStatusFilter, setTaskStatusFilter] = useState("all");

  // Facts Filters
  const [factsSearchQuery, setFactsSearchQuery] = useState("");

  // Dialog States
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [configName, setConfigName] = useState("");
  const [configDescription, setConfigDescription] = useState("");
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDocument | null>(null);
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(
    null,
  );
  const [deleteDocTarget, setDeleteDocTarget] =
    useState<KnowledgeDocument | null>(null);

  // Reconcile Dialog States
  const [isReconcileOpen, setIsReconcileOpen] = useState(false);
  const [reconcileReport, setReconcileReport] =
    useState<KnowledgeReconciliationReport | null>(null);
  const [isLoadingReconcile, setIsLoadingReconcile] = useState(false);
  const [isFixingReconcile, setIsFixingReconcile] = useState(false);

  // Excel Facts Import State
  const [isExcelImportOpen, setIsExcelImportOpen] = useState(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);

  // Reindex State
  const [isReindexing, setIsReindexing] = useState(false);
  const [reindexJobId, setReindexJobId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Playground Sandbox State
  const [sandboxQuery, setSandboxQuery] = useState("");
  const [isSearchingSandbox, setIsSearchingSandbox] = useState(false);
  const [sandboxResults, setSandboxResults] = useState<
    SandboxSearchResult[] | null
  >(null);

  // 1. Fetch Collections
  const { data: collections = [] } = useQuery({
    queryKey: ["collections"],
    queryFn: () => knowledgeApi.getCollections(),
  });

  // Current Collection object
  const collection = useMemo<KnowledgeCollection>(() => {
    const found = collections.find(
      (c) => c.id === collectionId || c.code === collectionId,
    );
    if (found) return found;
    return {
      id: collectionId,
      name: "Kho Tri Thức",
      code: collectionId,
      description: "",
      document_count: 0,
      chunk_count: 0,
      chunking_strategy: "SemanticChunker",
      ocr_profile: "PyMuPDF",
      updated_at: new Date().toISOString(),
    };
  }, [collections, collectionId]);

  // 2. Fetch System Defaults for Embedding Model
  const { data: systemDefaultsResponse } = useQuery({
    queryKey: ["system-model-defaults"],
    queryFn: () => apiClient.getSystemModelDefaults(),
    staleTime: 60000,
  });

  // 3. Fetch Documents
  const { data: allDocuments = [], refetch: refetchDocs } = useQuery({
    queryKey: ["documents", collection.id],
    queryFn: () => knowledgeApi.getDocuments(collection.id),
    refetchInterval: (query) => {
      const docs = query.state.data || [];
      const hasProcessing = docs.some(
        (d) => d.status === "processing" || d.index_status === "indexing",
      );
      return hasProcessing ? 3000 : false;
    },
  });

  // 4. Fetch Tasks
  const { data: allTasks = [], refetch: refetchTasks } = useQuery({
    queryKey: ["ingestion-tasks", collection.id],
    queryFn: () => jobsApi.getIngestionTasks(collection.id),
  });

  // 5. Fetch Facts
  const factsQuery = useQuery({
    queryKey: ["collection-facts", collection.id],
    queryFn: () => knowledgeApi.getCollectionFacts(collection.id),
    enabled: Boolean(collection.id),
  });

  // Filtered Documents
  const filteredDocuments = useMemo(() => {
    return allDocuments.filter((d) => {
      const q = docSearchQuery.toLowerCase().trim();
      const matchSearch =
        !q ||
        d.title.toLowerCase().includes(q) ||
        d.filename.toLowerCase().includes(q);

      const docType = (
        d.document_type ||
        d.document_type_code ||
        ""
      ).toLowerCase();
      const filterType = selectedTypeFilter.toLowerCase();
      const matchType =
        selectedTypeFilter === "all" ||
        docType === filterType ||
        docType.includes(filterType) ||
        filterType.includes(docType);

      const matchStatus =
        selectedStatusFilter === "all" ||
        d.status === selectedStatusFilter ||
        (selectedStatusFilter === "approved" &&
          (d.status === "ready" || d.status === "completed"));

      const matchPriority =
        selectedPriorityFilter === "all" ||
        (d.priority_level || "core") === selectedPriorityFilter;

      return matchSearch && matchType && matchStatus && matchPriority;
    });
  }, [
    allDocuments,
    docSearchQuery,
    selectedTypeFilter,
    selectedStatusFilter,
    selectedPriorityFilter,
  ]);

  // Filtered Tasks
  const filteredTasks = useMemo(() => {
    return allTasks.filter((t: IngestionTask) => {
      const q = taskSearchQuery.toLowerCase().trim();
      const matchSearch =
        !q ||
        t.task_name.toLowerCase().includes(q) ||
        t.source_file.toLowerCase().includes(q) ||
        t.worker_name.toLowerCase().includes(q);

      const matchStatus =
        taskStatusFilter === "all" || t.status === taskStatusFilter;

      return matchSearch && matchStatus;
    });
  }, [allTasks, taskSearchQuery, taskStatusFilter]);

  // Filtered Facts
  const filteredFacts = useMemo(() => {
    const list = factsQuery.data?.facts || [];
    const q = factsSearchQuery.toLowerCase().trim();
    if (!q) return list;
    return list.filter(
      (f) =>
        f.entity_name.toLowerCase().includes(q) ||
        f.attribute_name.toLowerCase().includes(q) ||
        f.attribute_value.toLowerCase().includes(q),
    );
  }, [factsQuery.data?.facts, factsSearchQuery]);

  // Mutations
  const updateCollectionMutation = useMutation({
    mutationFn: () =>
      knowledgeApi.updateCollection(collection.id, {
        name: configName.trim() || undefined,
        description: configDescription.trim() || undefined,
      }),
    onSuccess: () => {
      toast.success("Cập nhật thông tin kho thành công.");
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      setIsConfigOpen(false);
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật thất bại: ${err.message}`);
    },
  });

  const importExcelMutation = useMutation({
    mutationFn: (file: File) =>
      knowledgeApi.importFactsExcel(collection.id, file),
    onSuccess: (res) => {
      toast.success(
        res.message || `Đã nạp ${res.imported_count} số liệu facts.`,
      );
      setIsExcelImportOpen(false);
      setSelectedExcelFile(null);
      queryClient.invalidateQueries({
        queryKey: ["collection-facts", collection.id],
      });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
    onError: (err: Error) => {
      toast.error(`Nạp bảng tính thất bại: ${err.message}`);
    },
  });

  const deleteDocMutation = useMutation({
    mutationFn: (docId: string) => knowledgeApi.deleteDocument(docId),
    onSuccess: () => {
      toast.success("Đã xóa tài liệu khỏi kho.");
      queryClient.invalidateQueries({ queryKey: ["documents", collection.id] });
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      setDeleteDocTarget(null);
    },
    onError: (err: Error) => {
      toast.error(`Xóa tài liệu thất bại: ${err.message}`);
    },
  });

  // Handlers
  const handleReindexCollection = async () => {
    setIsReindexing(true);
    setActionError(null);
    try {
      const res = await knowledgeApi.reindexCollection(collection.id);
      setReindexJobId(res.job_id);
      toast.success("Đã kích hoạt job reindex toàn bộ kho thành công.");
      queryClient.invalidateQueries({
        queryKey: ["ingestion-tasks", collection.id],
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Reindex thất bại.";
      setActionError(msg);
      toast.error(msg);
    } finally {
      setIsReindexing(false);
    }
  };

  const handleOpenReconcile = async () => {
    setIsReconcileOpen(true);
    setIsLoadingReconcile(true);
    setReconcileReport(null);
    try {
      const rep = await knowledgeApi.reconcileCollection(collection.id);
      setReconcileReport(rep);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Đối soát dữ liệu thất bại.",
      );
    } finally {
      setIsLoadingReconcile(false);
    }
  };

  const handleFixReconcile = async () => {
    setIsFixingReconcile(true);
    try {
      const res = await knowledgeApi.fixReconciliation(collection.id);
      toast.success(res.message || "Đã đồng bộ dữ liệu sạch.");
      const rep = await knowledgeApi.reconcileCollection(collection.id);
      setReconcileReport(rep);
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      queryClient.invalidateQueries({ queryKey: ["documents", collection.id] });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Đồng bộ thất bại.");
    } finally {
      setIsFixingReconcile(false);
    }
  };

  const handleOpenConfig = () => {
    setConfigName(collection.name);
    setConfigDescription(collection.description);
    setIsConfigOpen(true);
  };

  const handleReindexSingleDoc = async (docId: string) => {
    try {
      await knowledgeApi.reindexDocument(docId);
      toast.success("Đã kích hoạt reindex cho tài liệu.");
      refetchDocs();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Reindex tài liệu thất bại.",
      );
    }
  };

  const handleQuickApprove = async (docId: string) => {
    try {
      await knowledgeApi.approveDocument(docId);
      toast.success("Đã phê duyệt tài liệu.");
      refetchDocs();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.",
      );
    }
  };

  const handleBatchApprove = async (docIds: string[]) => {
    try {
      for (const id of docIds) {
        await knowledgeApi.approveDocument(id);
      }
      toast.success(`Đã phê duyệt ${docIds.length} tài liệu.`);
      refetchDocs();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Phê duyệt tài liệu thất bại.",
      );
    }
  };

  const handleBatchDelete = async (docIds: string[]) => {
    try {
      for (const id of docIds) {
        await knowledgeApi.deleteDocument(id);
      }
      toast.success(`Đã xóa ${docIds.length} tài liệu.`);
      refetchDocs();
      queryClient.invalidateQueries({ queryKey: ["collections"] });
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Xóa tài liệu thất bại.",
      );
    }
  };

  const handleSandboxSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sandboxQuery.trim()) return;
    setIsSearchingSandbox(true);
    try {
      const res = await knowledgeApi.testCollection(
        collection.id,
        sandboxQuery.trim(),
        5,
      );
      setSandboxResults(
        res.map((item) => ({
          id: item.chunk_id,
          title: item.document_id,
          clause: item.section || "Nội dung",
          text: item.content,
          score: item.score,
          method: "Hybrid RRF",
        })),
      );
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Truy vấn thử nghiệm thất bại.",
      );
    } finally {
      setIsSearchingSandbox(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* 1. Header Hero & Navigation Bar */}
      <CollectionHeader
        collection={collection}
        documentCount={allDocuments.length}
        systemDefaultEmbeddingModel={
          systemDefaultsResponse?.defaults?.default_embedding_model
        }
        onBack={() => navigate({ to: "/knowledge" })}
        onOpenReconcile={handleOpenReconcile}
        onReindex={handleReindexCollection}
        isReindexing={isReindexing}
        onOpenConfig={handleOpenConfig}
        onStartIngest={() => setIsUploadOpen(true)}
        actionError={actionError}
        reindexJobId={reindexJobId}
      />

      {/* 2. Responsive Tabs Navigation */}
      <Tabs
        value={activeTab}
        onValueChange={(val) => setActiveTab(val as CollectionDetailTab)}
        className="w-full space-y-4"
      >
        <div className="w-full overflow-x-auto no-scrollbar pb-0.5">
          <TabsList className="h-9 p-1 bg-muted/60 inline-flex w-auto min-w-full sm:min-w-0 justify-start gap-1">
            <TabsTrigger
              value="documents"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <FileText className="size-3.5" />
              <span>Tài liệu</span>
            </TabsTrigger>

            <TabsTrigger
              value="facts"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Table2 className="size-3.5" />
              <span>Facts số</span>
            </TabsTrigger>

            <TabsTrigger
              value="tasks"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Activity className="size-3.5" />
              <span>Tiến trình</span>
            </TabsTrigger>

            <TabsTrigger
              value="playground"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Zap className="size-3.5" />
              <span>Thử nghiệm</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* 3. Tab Contents */}
        {/* Tab 1: Tài Liệu */}
        <TabsContent value="documents" className="mt-0 focus-visible:ring-0">
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
            reindexingDocId={null}
            downloadingId={null}
            onReindexDoc={handleReindexSingleDoc}
            onStartVerify={(docId) => {
              toast.info(`Mở trình thẩm định tài liệu ${docId}`);
            }}
            onPreviewDoc={setPreviewDoc}
            onDownloadDoc={(doc) => {
              window.open(
                knowledgeApi.getDocumentDownloadUrl(doc.id),
                "_blank",
              );
            }}
            onDeleteDoc={setDeleteDocTarget}
            onQuickApprove={handleQuickApprove}
            onBatchApprove={handleBatchApprove}
            onBatchDelete={handleBatchDelete}
          />
        </TabsContent>

        {/* Tab 2: Facts Số */}
        <TabsContent value="facts" className="mt-0 focus-visible:ring-0">
          <CollectionFactsTab
            facts={filteredFacts}
            totalCount={factsQuery.data?.total || 0}
            isLoading={factsQuery.isLoading}
            isFetching={factsQuery.isFetching}
            searchQuery={factsSearchQuery}
            onSearchChange={setFactsSearchQuery}
            onRefresh={() => factsQuery.refetch()}
            onOpenExcelImport={() => setIsExcelImportOpen(true)}
          />
        </TabsContent>

        {/* Tab 3: Tiến Trình Tác Vụ */}
        <TabsContent value="tasks" className="mt-0 focus-visible:ring-0">
          <CollectionTasksTab
            tasks={filteredTasks}
            totalTasksCount={allTasks.length}
            searchQuery={taskSearchQuery}
            onSearchChange={setTaskSearchQuery}
            statusFilter={taskStatusFilter}
            onStatusFilterChange={setTaskStatusFilter}
            taskActionId={null}
            isCleaningTasks={false}
            canCleanup={false}
            taskSuccessMessage={null}
            onRefresh={() => refetchTasks()}
            onOpenConfirmCleanup={() => {}}
            onViewLog={setSelectedTaskLog}
            onTaskAction={(taskId, action) => {
              toast.info(`Thao tác ${action} trên task ${taskId}`);
            }}
            onDeleteTask={(task) => {
              toast.info(`Xóa task ${task.id}`);
            }}
          />
        </TabsContent>

        {/* Tab 4: Thử Nghiệm Sandbox */}
        <TabsContent value="playground" className="mt-0 focus-visible:ring-0">
          <CollectionPlaygroundTab
            sandboxQuery={sandboxQuery}
            setSandboxQuery={setSandboxQuery}
            isSearchingSandbox={isSearchingSandbox}
            sandboxResults={sandboxResults}
            onSandboxSearch={handleSandboxSearch}
          />
        </TabsContent>
      </Tabs>

      {/* 4. Dialogs */}
      {/* Nạp Tài Liệu */}
      <DocumentUploadDialog
        open={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        collectionId={collection.id}
        collectionName={collection.name}
        onSuccess={() => {
          refetchDocs();
          refetchTasks();
        }}
      />

      {/* Cấu Hình Kho */}
      <CollectionConfigDialog
        open={isConfigOpen}
        onOpenChange={setIsConfigOpen}
        configName={configName}
        setConfigName={setConfigName}
        configDescription={configDescription}
        setConfigDescription={setConfigDescription}
        isSaving={updateCollectionMutation.isPending}
        onSave={() => updateCollectionMutation.mutate()}
      />

      {/* Đối Soát Dữ Liệu */}
      <CollectionReconcileDialog
        open={isReconcileOpen}
        onOpenChange={setIsReconcileOpen}
        collectionCode={collection.code}
        reconcileReport={reconcileReport}
        isLoading={isLoadingReconcile}
        isFixing={isFixingReconcile}
        onRefresh={handleOpenReconcile}
        onFix={handleFixReconcile}
      />

      {/* Nhập Excel Facts */}
      <CollectionExcelImportDialog
        open={isExcelImportOpen}
        onOpenChange={setIsExcelImportOpen}
        selectedFile={selectedExcelFile}
        setSelectedFile={setSelectedExcelFile}
        isPending={importExcelMutation.isPending}
        onImport={(file) => importExcelMutation.mutate(file)}
      />

      {/* Xem Trước Tài Liệu */}
      <DocumentPreviewDialog
        open={Boolean(previewDoc)}
        onOpenChange={(v) => {
          if (!v) setPreviewDoc(null);
        }}
        document={previewDoc}
        collectionName={collection.name}
      />

      {/* Xem Log Tác Vụ */}
      <TaskLogDialog
        open={Boolean(selectedTaskLog)}
        onOpenChange={(v) => {
          if (!v) setSelectedTaskLog(null);
        }}
        task={selectedTaskLog}
      />

      {/* Xác Nhận Xóa Tài Liệu */}
      <ConfirmDialog
        open={Boolean(deleteDocTarget)}
        onOpenChange={(v) => {
          if (!v) setDeleteDocTarget(null);
        }}
        title="Xóa tài liệu"
        description={`Bạn có chắc chắn muốn xóa tài liệu "${deleteDocTarget?.title}"? Các vector embeddings liên kết trong Qdrant cũng sẽ bị gỡ bỏ.`}
        confirmText="Xóa tài liệu"
        cancelText="Hủy"
        variant="destructive"
        isLoading={deleteDocMutation.isPending}
        onConfirm={() => {
          if (deleteDocTarget) deleteDocMutation.mutate(deleteDocTarget.id);
        }}
      />
    </div>
  );
};
