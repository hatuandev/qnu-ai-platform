import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Activity, Cpu, FolderGit2, Table2 } from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { EmptyState } from "@/components/admin/empty-state";
import { CollectionHeader } from "@/components/knowledge/collection-header";
import { CollectionExcelImportDialog } from "@/components/knowledge/dialogs/collection-excel-import-dialog";
import { TaskLogDialog } from "@/components/knowledge/dialogs/task-log-dialog";
import { CollectionBindingsTab } from "@/components/knowledge/tabs/collection-bindings-tab";
import { CollectionFactsTab } from "@/components/knowledge/tabs/collection-facts-tab";
import { CollectionModelsTab } from "@/components/knowledge/tabs/collection-models-tab";
import { CollectionTasksTab } from "@/components/knowledge/tabs/collection-tasks-tab";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { jobsApi } from "@/services/jobs-api";
import { knowledgeApi } from "@/services/knowledge-api";
import type {
  CollectionDataProcessingConfig,
  IngestionTask,
} from "@/types/knowledge";

export interface CollectionDetailPageProps {
  collectionId: string;
  initialTab?: "sources" | "facts" | "tasks" | "models";
}

export const CollectionDetailPage: React.FC<CollectionDetailPageProps> = ({
  collectionId,
  initialTab,
}) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Active Tab: only 4 streamlined tabs
  const [activeTab, setActiveTab] = useState<
    "sources" | "facts" | "tasks" | "models"
  >(initialTab || "sources");

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // Tasks Filters
  const [taskSearchQuery, setTaskSearchQuery] = useState("");
  const [taskStatusFilter, setTaskStatusFilter] = useState("all");

  // Config States
  const [configName, setConfigName] = useState("");
  const [configDescription, setConfigDescription] = useState("");
  const [configDataProcessing, setConfigDataProcessing] =
    useState<CollectionDataProcessingConfig>({});
  const [selectedTaskLog, setSelectedTaskLog] = useState<IngestionTask | null>(
    null,
  );
  const [deleteTaskTarget, setDeleteTaskTarget] =
    useState<IngestionTask | null>(null);

  // Excel Facts Import State
  const [isExcelImportOpen, setIsExcelImportOpen] = useState(false);
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);

  // 1. Fetch Collection Info directly
  const {
    data: collection,
    isLoading: isCollectionLoading,
    isError: isCollectionError,
    error: collectionError,
  } = useQuery({
    queryKey: ["knowledge-collection", collectionId],
    queryFn: () => knowledgeApi.getCollection(collectionId),
  });

  // 2. Fetch Real Summary Metrics
  const { data: summaryMetrics } = useQuery({
    queryKey: ["collection-summary-metrics", collectionId],
    queryFn: () => knowledgeApi.getCollectionSummaryMetrics(collectionId),
    enabled: !!collection,
  });

  useEffect(() => {
    if (collection) {
      setConfigName(collection.name);
      setConfigDescription(collection.description || "");
      if (collection.data_processing) {
        setConfigDataProcessing(collection.data_processing);
      } else {
        setConfigDataProcessing({});
      }
    }
  }, [collection]);

  // 3. Fetch Facts
  const factsQuery = useQuery({
    queryKey: ["collection-facts", collection?.id],
    queryFn: () =>
      collection
        ? knowledgeApi.getCollectionFacts(collection.id, 50)
        : Promise.reject(new Error("No collection")),
    enabled: !!collection && activeTab === "facts",
  });

  // 4. Fetch Ingestion Tasks
  const tasksQuery = useQuery<IngestionTask[]>({
    queryKey: ["ingestion-tasks", collection?.id],
    queryFn: () =>
      collection
        ? jobsApi.getIngestionTasks(collection.id)
        : Promise.reject(new Error("No collection")),
    enabled: !!collection && activeTab === "tasks",
  });

  const allTasks: IngestionTask[] = tasksQuery.data || [];

  const filteredTasks = useMemo(() => {
    return allTasks.filter((task: IngestionTask) => {
      const matchSearch =
        taskSearchQuery.trim() === "" ||
        task.task_name.toLowerCase().includes(taskSearchQuery.toLowerCase()) ||
        task.source_file.toLowerCase().includes(taskSearchQuery.toLowerCase());
      const matchStatus =
        taskStatusFilter === "all" || task.status === taskStatusFilter;
      return matchSearch && matchStatus;
    });
  }, [allTasks, taskSearchQuery, taskStatusFilter]);

  // Mutations
  const updateCollectionMutation = useMutation({
    mutationFn: () => {
      if (!collection) throw new Error("Chưa tải được thông tin kho tri thức.");
      return knowledgeApi.updateCollection(collection.id, {
        name: configName,
        description: configDescription,
        data_processing: configDataProcessing,
      });
    },
    onSuccess: () => {
      toast.success("Cập nhật cấu hình Kho Tri Thức thành công.");
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      queryClient.invalidateQueries({
        queryKey: ["collection-summary-metrics", collection?.id],
      });
    },
    onError: (err: Error) => {
      toast.error(`Cập nhật thất bại: ${err.message}`);
    },
  });

  const importExcelMutation = useMutation({
    mutationFn: (file: File) => {
      if (!collection) throw new Error("Chưa tải được thông tin kho tri thức.");
      return knowledgeApi.importFactsExcel(collection.id, file);
    },
    onSuccess: (res) => {
      toast.success(
        `Nhập dữ liệu thành công: đã tạo ${res.imported_count} facts số mới.`,
      );
      setIsExcelImportOpen(false);
      setSelectedExcelFile(null);
      queryClient.invalidateQueries({
        queryKey: ["collection-facts", collection?.id],
      });
    },
    onError: (err: Error) => {
      toast.error(`Nhập Excel thất bại: ${err.message}`);
    },
  });

  const deleteTaskMutation = useMutation({
    mutationFn: (task: IngestionTask) => jobsApi.deleteJob(task.id),
    onSuccess: () => {
      toast.success("Đã xóa bản ghi tác vụ thành công.");
      queryClient.invalidateQueries({
        queryKey: ["ingestion-tasks", collection?.id],
      });
      setDeleteTaskTarget(null);
    },
    onError: (err: Error) => {
      toast.error(`Xóa tác vụ thất bại: ${err.message}`);
    },
  });

  const [runningTaskActionId, setRunningTaskActionId] = useState<string | null>(
    null,
  );

  const handleTaskAction = async (
    taskId: string,
    action: "retry" | "cancel",
  ) => {
    setRunningTaskActionId(taskId);
    try {
      if (action === "retry") {
        await jobsApi.retryJob(taskId);
        toast.success("Đã kích hoạt chạy lại tác vụ.");
      } else {
        await jobsApi.cancelJob(taskId);
        toast.success("Đã gửi yêu cầu hủy tác vụ.");
      }
      queryClient.invalidateQueries({
        queryKey: ["ingestion-tasks", collection?.id],
      });
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : `Thao tác ${action} thất bại.`,
      );
    } finally {
      setRunningTaskActionId(null);
    }
  };

  if (isCollectionLoading) {
    return (
      <div className="space-y-4 max-w-7xl mx-auto pb-10">
        <Skeleton className="h-28 w-full rounded-xl" />
        <Skeleton className="h-10 w-80 rounded-lg" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (isCollectionError || !collection) {
    return (
      <div className="space-y-4 max-w-7xl mx-auto pb-10 pt-8">
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <EmptyState
              icon={FolderGit2}
              title="Không tìm thấy kho tri thức"
              description={
                collectionError instanceof Error
                  ? collectionError.message
                  : `Kho tri thức '${collectionId}' không tồn tại hoặc bạn không có quyền truy cập.`
              }
              action={{
                label: "Quay lại danh sách",
                onClick: () => navigate({ to: "/knowledge" }),
              }}
            />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-7xl mx-auto pb-10">
      {/* 1. Header with unified metrics and single primary CTA */}
      <CollectionHeader
        collection={collection}
        metrics={summaryMetrics}
        onBack={() => navigate({ to: "/knowledge" })}
        onAddSource={() =>
          navigate({ to: `/knowledge/${collection.id}/add-documents` })
        }
        onOpenConfig={() => setActiveTab("models")}
        onOpenExcelImport={() => setIsExcelImportOpen(true)}
      />

      {/* 2. Streamlined Navigation Tabs (4 main tabs) */}
      <Tabs
        value={activeTab}
        onValueChange={(val) =>
          setActiveTab(val as "sources" | "facts" | "tasks" | "models")
        }
        className="space-y-4"
      >
        <div className="border-b border-border/80 pb-2">
          <TabsList className="bg-muted/60 p-1 h-9 rounded-lg border border-border/50 gap-1 w-full sm:w-auto overflow-x-auto justify-start">
            <TabsTrigger
              value="sources"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <FolderGit2 className="size-3.5" />
              <span>Nguồn tài liệu</span>
            </TabsTrigger>

            <TabsTrigger
              value="facts"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Table2 className="size-3.5" />
              <span>Dữ liệu số</span>
            </TabsTrigger>

            <TabsTrigger
              value="tasks"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Activity className="size-3.5" />
              <span>Hoạt động</span>
            </TabsTrigger>

            <TabsTrigger
              value="models"
              className="text-xs h-7 px-3 sm:px-4 gap-1.5 data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-xs shrink-0 whitespace-nowrap"
            >
              <Cpu className="size-3.5" />
              <span>Cấu hình</span>
            </TabsTrigger>
          </TabsList>
        </div>

        {/* Tab 1: Nguồn Tài Liệu (Snapshot Sources & Bindings ADR-012) */}
        <TabsContent value="sources" className="mt-0 focus-visible:ring-0">
          <CollectionBindingsTab collection={collection} />
        </TabsContent>

        {/* Tab 2: Dữ Liệu Số (Facts) */}
        <TabsContent value="facts" className="mt-0 focus-visible:ring-0">
          <CollectionFactsTab
            facts={factsQuery.data?.facts || []}
            totalCount={factsQuery.data?.total || 0}
            isLoading={factsQuery.isLoading}
            isFetching={factsQuery.isFetching}
            onRefresh={() => factsQuery.refetch()}
            onOpenExcelImport={() => setIsExcelImportOpen(true)}
          />
        </TabsContent>

        {/* Tab 3: Hoạt Động (Tasks) */}
        <TabsContent value="tasks" className="mt-0 focus-visible:ring-0">
          <CollectionTasksTab
            tasks={filteredTasks}
            totalTasksCount={allTasks.length}
            searchQuery={taskSearchQuery}
            onSearchChange={setTaskSearchQuery}
            statusFilter={taskStatusFilter}
            onStatusFilterChange={setTaskStatusFilter}
            taskActionId={runningTaskActionId}
            isCleaningTasks={false}
            canCleanup={false}
            taskSuccessMessage={null}
            onRefresh={() => tasksQuery.refetch()}
            onOpenConfirmCleanup={() => {}}
            onViewLog={setSelectedTaskLog}
            onTaskAction={handleTaskAction}
            onDeleteTask={(task) => setDeleteTaskTarget(task)}
          />
        </TabsContent>

        {/* Tab 4: Cấu Hình Kho & Mô Hình */}
        <TabsContent value="models" className="mt-0 focus-visible:ring-0">
          <CollectionModelsTab
            collection={collection}
            configName={configName}
            setConfigName={setConfigName}
            configDescription={configDescription}
            setConfigDescription={setConfigDescription}
            dataProcessingConfig={configDataProcessing}
            setDataProcessingConfig={setConfigDataProcessing}
            isSaving={updateCollectionMutation.isPending}
            onSave={() => updateCollectionMutation.mutate()}
          />
        </TabsContent>
      </Tabs>

      {/* Dialogs */}
      <CollectionExcelImportDialog
        open={isExcelImportOpen}
        onOpenChange={setIsExcelImportOpen}
        selectedFile={selectedExcelFile}
        setSelectedFile={setSelectedExcelFile}
        isPending={importExcelMutation.isPending}
        onImport={(file) => importExcelMutation.mutate(file)}
      />

      <TaskLogDialog
        task={selectedTaskLog}
        open={Boolean(selectedTaskLog)}
        onOpenChange={(v) => {
          if (!v) setSelectedTaskLog(null);
        }}
      />

      <ConfirmDialog
        open={Boolean(deleteTaskTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTaskTarget(null);
        }}
        title="Xóa bản ghi tác vụ"
        description={`Bạn có chắc chắn muốn xóa bản ghi tác vụ "${deleteTaskTarget?.task_name}"?`}
        confirmLabel="Xóa tác vụ"
        variant="destructive"
        isLoading={deleteTaskMutation.isPending}
        onConfirm={() => {
          if (deleteTaskTarget) {
            deleteTaskMutation.mutate(deleteTaskTarget);
          }
        }}
      />
    </div>
  );
};
