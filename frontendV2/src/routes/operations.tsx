import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  AlertCircle,
  Archive,
  CheckCircle2,
  Clock,
  Database,
  Download,
  FileArchive,
  Loader2,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiProblemError } from "@/api/client";
import {
  useOperationsJobsQuery,
  useWorkspaceBackupsQuery,
} from "@/api/operations/queries";
import {
  createWorkspaceBackup,
  downloadWorkspaceBackup,
  exportSystemBackup,
  getWorkspaceBackup,
  restoreSystemBackup,
} from "@/api/operations/requests";
import type {
  SystemBackupRestoreReport,
  SystemBackupTarget,
} from "@/api/operations/types";
import { useWorkspacesQuery } from "@/api/workspaces/queries";
import { CopyButton } from "@/components/admin/copy-button";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useUiStore } from "@/lib/ui-store";

export const Route = createFileRoute("/operations")({
  component: OperationsPage,
});

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("vi-VN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatDuration(
  startIso?: string | null,
  endIso?: string | null,
): string {
  if (!startIso) return "—";
  try {
    const start = new Date(startIso).getTime();
    const end = endIso ? new Date(endIso).getTime() : Date.now();
    const diffMs = Math.max(0, end - start);
    if (diffMs < 1000) return `${diffMs}ms`;
    if (diffMs < 60000) return `${(diffMs / 1000).toFixed(1)}s`;
    return `${Math.floor(diffMs / 60000)}m ${Math.round((diffMs % 60000) / 1000)}s`;
  } catch {
    return "—";
  }
}

function kindLabel(kind: string): { label: string; badgeColor: string } {
  switch (kind) {
    case "ocr":
      return {
        label: "Bóc tách OCR",
        badgeColor: "bg-blue-500/10 text-blue-600 border-blue-500/20",
      };
    case "index":
      return {
        label: "Lập chỉ mục Vector",
        badgeColor: "bg-teal-500/10 text-teal-600 border-teal-500/20",
      };
    case "compiler":
      return {
        label: "Biên dịch & Rà soát",
        badgeColor: "bg-indigo-500/10 text-indigo-600 border-indigo-500/20",
      };
    case "spelling":
      return {
        label: "Đối soát chính tả",
        badgeColor: "bg-purple-500/10 text-purple-600 border-purple-500/20",
      };
    case "backup":
      return {
        label: "Sao lưu bằng chứng",
        badgeColor: "bg-amber-500/10 text-amber-600 border-amber-500/20",
      };
    default:
      return {
        label: kind,
        badgeColor: "bg-muted text-muted-foreground border-border/40",
      };
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "completed":
      return (
        <Badge
          variant="outline"
          className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px] gap-1"
        >
          <CheckCircle2 className="size-2.5" />
          <span>Hoàn thành</span>
        </Badge>
      );
    case "running":
      return (
        <Badge
          variant="outline"
          className="bg-blue-500/10 text-blue-600 border-blue-500/20 text-[10px] gap-1"
        >
          <RefreshCw className="size-2.5 animate-spin" />
          <span>Đang chạy</span>
        </Badge>
      );
    case "queued":
      return (
        <Badge
          variant="outline"
          className="bg-amber-500/10 text-amber-600 border-amber-500/20 text-[10px] gap-1"
        >
          <Clock className="size-2.5" />
          <span>Chờ xử lý</span>
        </Badge>
      );
    case "failed":
      return (
        <Badge
          variant="outline"
          className="bg-red-500/10 text-red-600 border-red-500/20 text-[10px] gap-1"
        >
          <AlertCircle className="size-2.5" />
          <span>Thất bại</span>
        </Badge>
      );
    default:
      return (
        <Badge variant="outline" className="text-[10px]">
          {status}
        </Badge>
      );
  }
}

function formatApiError(err: unknown, fallback: string): string {
  if (err instanceof ApiProblemError) return err.message || fallback;
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

function OperationsPage() {
  const [activeTab, setActiveTab] = useState<string>("jobs");
  const storeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);

  // System backup & restore states
  const [backupTarget, setBackupTarget] = useState<SystemBackupTarget>("all");
  const [isExportingSystem, setIsExportingSystem] = useState(false);
  const [lastExportSummary, setLastExportSummary] = useState<{
    fileName: string;
    size: number;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<SystemBackupTarget>("all");
  const [isVerifyingRestore, setIsVerifyingRestore] = useState(false);
  const [restorePreview, setRestorePreview] =
    useState<SystemBackupRestoreReport | null>(null);
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [confirmRestoreOpen, setConfirmRestoreOpen] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [restoreResult, setRestoreResult] =
    useState<SystemBackupRestoreReport | null>(null);

  // Workspace evidence backup states
  const [isCreatingEvidenceBackup, setIsCreatingEvidenceBackup] =
    useState(false);
  const [evidenceBackupStatusText, setEvidenceBackupStatusText] = useState<
    string | null
  >(null);
  const [downloadingBackupId, setDownloadingBackupId] = useState<string | null>(
    null,
  );

  // Fetch workspaces to fallback if activeWorkspaceId not set
  const { data: workspacesData, isLoading: isLoadingWorkspaces } =
    useWorkspacesQuery();
  const effectiveWorkspaceId = useMemo(() => {
    if (storeWorkspaceId) return storeWorkspaceId;
    return workspacesData?.items?.[0]?.id ?? null;
  }, [storeWorkspaceId, workspacesData]);

  // Queries
  const {
    data: jobsData,
    isLoading: isLoadingJobs,
    refetch: refetchJobs,
    isRefetching: isRefetchingJobs,
  } = useOperationsJobsQuery(effectiveWorkspaceId, { limit: 50 });

  const {
    data: backupsData,
    isLoading: isLoadingBackups,
    refetch: refetchBackups,
    isRefetching: isRefetchingBackups,
  } = useWorkspaceBackupsQuery(effectiveWorkspaceId, { limit: 50 });

  const jobs = jobsData?.items ?? [];
  const backups = backupsData?.items ?? [];

  const handleSystemBackupAndDownload = async () => {
    if (isExportingSystem) return;
    setIsExportingSystem(true);
    try {
      const result = await exportSystemBackup(backupTarget);
      const fileName = result.fileName || "qnu-system-backup.tar.gz";
      setLastExportSummary({ fileName, size: result.size });
      toast.success(`Đã sao lưu và tải về ${fileName}`);
    } catch (err) {
      toast.error(
        formatApiError(err, "Không thể tạo bản sao lưu hệ thống. Vui lòng thử lại."),
      );
    } finally {
      setIsExportingSystem(false);
    }
  };

  const handleSelectRestoreFile = async (file: File | null) => {
    if (!file) return;
    setRestoreFile(file);
    setRestorePreview(null);
    setRestoreResult(null);
    setRestoreError(null);
    setIsVerifyingRestore(true);
    try {
      const preview = await restoreSystemBackup(file, {
        target: restoreTarget,
        confirm: false,
      });
      setRestorePreview(preview);
      toast.success("Tệp sao lưu hợp lệ và đã xác minh toàn vẹn.");
    } catch (err) {
      const msg = formatApiError(
        err,
        "Tệp sao lưu không hợp lệ hoặc bị hỏng.",
      );
      setRestoreError(msg);
      toast.error(msg);
    } finally {
      setIsVerifyingRestore(false);
    }
  };

  const handleConfirmRestore = async () => {
    if (!restoreFile || isRestoring) return;
    setIsRestoring(true);
    setRestoreError(null);
    try {
      const report = await restoreSystemBackup(restoreFile, {
        target: restoreTarget,
        confirm: true,
      });
      setRestoreResult(report);
      setConfirmRestoreOpen(false);
      toast.success("Khôi phục dữ liệu hệ thống thành công.");
      void refetchBackups();
      void refetchJobs();
    } catch (err) {
      const msg = formatApiError(
        err,
        "Khôi phục dữ liệu thất bại. Vui lòng kiểm tra log máy chủ.",
      );
      setRestoreError(msg);
      setConfirmRestoreOpen(false);
      toast.error(msg);
    } finally {
      setIsRestoring(false);
    }
  };

  const handleDownloadEvidenceBackup = async (backupId: string) => {
    if (!effectiveWorkspaceId || downloadingBackupId) return;
    setDownloadingBackupId(backupId);
    try {
      const res = await downloadWorkspaceBackup(effectiveWorkspaceId, backupId);
      toast.success(`Đã tải về ${res.fileName || `${backupId}.zip`}`);
    } catch (err) {
      toast.error(formatApiError(err, "Không thể tải tệp sao lưu bằng chứng."));
    } finally {
      setDownloadingBackupId(null);
    }
  };

  const handleCreateAndDownloadEvidenceBackup = async () => {
    if (!effectiveWorkspaceId || isCreatingEvidenceBackup) return;
    setIsCreatingEvidenceBackup(true);
    setEvidenceBackupStatusText("Đang khởi tạo tác vụ sao lưu...");
    try {
      const created = await createWorkspaceBackup(effectiveWorkspaceId, {
        retention_days: 30,
      });
      void refetchBackups();

      const deadline = Date.now() + 90_000;
      let current = created;
      while (
        current.status !== "completed" &&
        current.status !== "failed" &&
        current.status !== "uncertain" &&
        Date.now() < deadline
      ) {
        setEvidenceBackupStatusText(
          current.status === "running"
            ? "Đang đóng gói tài liệu & bằng chứng..."
            : "Đang chờ worker xử lý...",
        );
        await new Promise((resolve) => setTimeout(resolve, 1500));
        current = await getWorkspaceBackup(effectiveWorkspaceId, created.id);
      }

      void refetchBackups();
      if (current.status === "completed") {
        setEvidenceBackupStatusText("Đang tải tệp nén về máy...");
        const res = await downloadWorkspaceBackup(
          effectiveWorkspaceId,
          current.id,
        );
        toast.success(
          `Đã tạo và tải về gói bằng chứng ${res.fileName || `${current.id}.zip`}`,
        );
      } else if (current.status === "failed" || current.status === "uncertain") {
        toast.error(
          "Tác vụ sao lưu bằng chứng thất bại. Vui lòng kiểm tra trạng thái worker.",
        );
      } else {
        toast.info(
          "Bản sao lưu đang tiếp tục chạy nền. Bạn có thể bấm Tải về trong bảng khi hoàn tất.",
        );
      }
    } catch (err) {
      toast.error(
        formatApiError(err, "Không thể tạo bản sao lưu bằng chứng đơn vị."),
      );
    } finally {
      setIsCreatingEvidenceBackup(false);
      setEvidenceBackupStatusText(null);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <PageHeader
        eyebrow="Hệ thống & Vận hành"
        title="Quản trị Vận hành & Sao lưu"
        description="Giám sát tiến trình nền, lịch sử tác vụ OCR/lập chỉ mục và quy trình sao lưu an toàn CSDL PostgreSQL & vector Qdrant."
        actions={
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 text-xs"
            onClick={() => {
              if (activeTab === "jobs") refetchJobs();
              else refetchBackups();
            }}
            disabled={isRefetchingJobs || isRefetchingBackups}
          >
            <RefreshCw
              className={`size-3.5 ${
                isRefetchingJobs || isRefetchingBackups ? "animate-spin" : ""
              }`}
            />
            <span>Làm mới</span>
          </Button>
        }
      />

      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-4"
      >
        <TabsList className="bg-muted/50 p-1 border border-border/40">
          <TabsTrigger value="jobs" className="gap-2 text-xs">
            <Activity className="size-3.5" />
            <span>Tiến trình & Tác vụ</span>
          </TabsTrigger>
          <TabsTrigger value="backups" className="gap-2 text-xs">
            <Database className="size-3.5" />
            <span>Sao lưu & Khôi phục</span>
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: Background Jobs */}
        <TabsContent value="jobs" className="space-y-4">
          <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
            {isLoadingJobs || isLoadingWorkspaces ? (
              <div className="py-16 text-center text-xs text-muted-foreground">
                <RefreshCw className="size-5 animate-spin mx-auto mb-2 text-primary" />
                <span>Đang tải danh sách tác vụ...</span>
              </div>
            ) : jobs.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="Chưa có tác vụ nền nào"
                description={
                  effectiveWorkspaceId
                    ? "Chưa có tiến trình OCR, lập chỉ mục hoặc biên dịch nào trong đơn vị hiện tại."
                    : "Vui lòng chọn đơn vị làm việc để xem lịch sử tiến trình."
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="h-10 text-xs">
                    <TableHead className="w-[180px]">Mã tác vụ</TableHead>
                    <TableHead className="w-[160px]">Loại tác vụ</TableHead>
                    <TableHead className="w-[120px]">Trạng thái</TableHead>
                    <TableHead className="w-[130px]">Tiến độ</TableHead>
                    <TableHead className="w-[160px]">Bắt đầu</TableHead>
                    <TableHead className="w-[110px] text-right">
                      Thời lượng
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {jobs.map((job) => {
                    const kind = kindLabel(job.kind);
                    return (
                      <TableRow key={job.id} className="h-11 text-xs">
                        <TableCell className="font-mono text-[11px] text-foreground flex items-center gap-1.5">
                          <span
                            className="truncate max-w-[120px]"
                            title={job.id}
                          >
                            {job.id}
                          </span>
                          <CopyButton value={job.id} className="size-6" />
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`text-[10px] font-normal ${kind.badgeColor}`}
                          >
                            {kind.label}
                          </Badge>
                        </TableCell>
                        <TableCell>{statusBadge(job.status)}</TableCell>
                        <TableCell className="text-muted-foreground font-mono text-[11px]">
                          {job.progress_total !== null &&
                          job.progress_total !== undefined
                            ? `${job.progress_done ?? 0} / ${job.progress_total}`
                            : "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-[11px]">
                          {formatDate(job.started_at || job.created_at)}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground text-[11px]">
                          {formatDuration(
                            job.started_at || job.created_at,
                            job.finished_at,
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* Tab 2: System Backup, Upload-Restore & Evidence Archives */}
        <TabsContent value="backups" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* 1-Click System Backup & Download */}
            <Card className="border-border/60 bg-card">
              <CardContent className="p-5 space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Database className="size-4 text-primary" />
                      <h3 className="text-sm font-semibold text-foreground">
                        Sao lưu Hệ thống (PostgreSQL & Qdrant)
                      </h3>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Đóng gói nhất quán cơ sở dữ liệu quan hệ, chỉ mục vector và
                      chữ ký kiểm chứng SHA-256 thành một tệp nén duy nhất.
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {(
                    [
                      { value: "all", label: "Toàn bộ (CSDL + Vector)" },
                      { value: "postgres", label: "Chỉ PostgreSQL" },
                      { value: "qdrant", label: "Chỉ Qdrant" },
                    ] as const
                  ).map((opt) => (
                    <Button
                      key={opt.value}
                      type="button"
                      variant={
                        backupTarget === opt.value ? "secondary" : "outline"
                      }
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setBackupTarget(opt.value)}
                      disabled={isExportingSystem}
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <Button
                    type="button"
                    size="sm"
                    className="h-9 gap-2 text-xs"
                    onClick={handleSystemBackupAndDownload}
                    disabled={isExportingSystem}
                  >
                    {isExportingSystem ? (
                      <>
                        <Loader2 className="size-3.5 animate-spin" />
                        <span>Đang sao lưu & đóng gói...</span>
                      </>
                    ) : (
                      <>
                        <Download className="size-3.5" />
                        <span>Sao lưu & Tải ngay</span>
                      </>
                    )}
                  </Button>
                  {lastExportSummary && (
                    <span className="text-xs text-emerald-600 flex items-center gap-1.5">
                      <CheckCircle2 className="size-3.5 shrink-0" />
                      <span>
                        {lastExportSummary.fileName} (
                        {formatBytes(lastExportSummary.size)})
                      </span>
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Upload Backup File & Restore */}
            <Card className="border-border/60 bg-card">
              <CardContent className="p-5 space-y-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <RotateCcw className="size-4 text-primary" />
                    <h3 className="text-sm font-semibold text-foreground">
                      Khôi phục từ Tệp sao lưu
                    </h3>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Tải lên tệp sao lưu (.tar.gz hoặc .dump) để kiểm tra chữ ký
                    toàn vẹn SHA-256 trước khi khôi phục dữ liệu.
                  </p>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".tar.gz,.tgz,.gz,.dump"
                  className="hidden"
                  onChange={(e) => {
                    const selected = e.target.files?.[0] ?? null;
                    void handleSelectRestoreFile(selected);
                    e.target.value = "";
                  }}
                />

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setIsDraggingFile(true);
                  }}
                  onDragLeave={() => setIsDraggingFile(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setIsDraggingFile(false);
                    const dropped = e.dataTransfer.files?.[0] ?? null;
                    void handleSelectRestoreFile(dropped);
                  }}
                  disabled={isVerifyingRestore || isRestoring}
                  className={`w-full rounded-lg border border-dashed p-4 text-left transition-colors flex items-center gap-3 cursor-pointer ${
                    isDraggingFile
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50 hover:bg-muted/40"
                  }`}
                >
                  <div className="rounded-md bg-muted p-2 text-primary shrink-0">
                    {isVerifyingRestore ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : restoreFile ? (
                      <FileArchive className="size-4" />
                    ) : (
                      <Upload className="size-4" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-foreground truncate">
                      {isVerifyingRestore
                        ? "Đang kiểm tra tính toàn vẹn tệp sao lưu..."
                        : restoreFile
                          ? `${restoreFile.name} (${formatBytes(restoreFile.size)})`
                          : "Chọn tệp sao lưu hoặc kéo thả vào đây"}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Hỗ trợ gói sao lưu hệ thống (.tar.gz) hoặc bản xuất
                      PostgreSQL (.dump)
                    </p>
                  </div>
                </button>

                {restoreError && (
                  <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive flex items-start gap-2">
                    <AlertCircle className="size-4 shrink-0 mt-0.5" />
                    <span>{restoreError}</span>
                  </div>
                )}

                {restorePreview && (
                  <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-3 space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5">
                        <ShieldCheck className="size-4" />
                        <span>Đã xác minh toàn vẹn tệp sao lưu</span>
                      </span>
                      <Badge variant="outline" className="text-[10px]">
                        {restorePreview.format === "pg_dump_custom"
                          ? "PostgreSQL Dump"
                          : restorePreview.format === "postgres_native_tar_gz"
                            ? "PostgreSQL Archive"
                            : "Gói Hệ thống"}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                      <span>
                        Bảng dữ liệu:{" "}
                        <strong className="text-foreground">
                          {restorePreview.postgres_tables ?? "—"}
                        </strong>
                      </span>
                      <span>
                        Tổng số dòng:{" "}
                        <strong className="text-foreground">
                          {restorePreview.postgres_rows?.toLocaleString("vi-VN") ??
                            "—"}
                        </strong>
                      </span>
                      <span>
                        Tập vector Qdrant:{" "}
                        <strong className="text-foreground">
                          {restorePreview.qdrant_collections.length}
                        </strong>
                      </span>
                      <span className="truncate" title={restorePreview.sha256}>
                        SHA-256:{" "}
                        <strong className="font-mono text-foreground">
                          {restorePreview.sha256.slice(0, 12)}…
                        </strong>
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <div className="flex items-center gap-1.5">
                        {(
                          [
                            { value: "all", label: "Toàn bộ" },
                            { value: "postgres", label: "PostgreSQL" },
                            { value: "qdrant", label: "Qdrant" },
                          ] as const
                        ).map((opt) => (
                          <Button
                            key={opt.value}
                            type="button"
                            variant={
                              restoreTarget === opt.value
                                ? "secondary"
                                : "outline"
                            }
                            size="sm"
                            className="h-7 text-[11px] px-2"
                            onClick={() => setRestoreTarget(opt.value)}
                            disabled={isRestoring}
                          >
                            {opt.label}
                          </Button>
                        ))}
                      </div>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        className="h-8 gap-1.5 text-xs"
                        onClick={() => setConfirmRestoreOpen(true)}
                        disabled={isRestoring}
                      >
                        <RotateCcw className="size-3.5" />
                        <span>Khôi phục dữ liệu</span>
                      </Button>
                    </div>
                  </div>
                )}

                {restoreResult && (
                  <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-400 flex items-start gap-2">
                    <CheckCircle2 className="size-4 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">Khôi phục hoàn tất</p>
                      <p className="text-[11px] opacity-90">
                        {restoreResult.targets?.postgres
                          ? `PostgreSQL: ${restoreResult.targets.postgres.table_count ?? "đầy đủ"} bảng`
                          : null}
                        {restoreResult.targets?.postgres &&
                        restoreResult.targets?.qdrant
                          ? " · "
                          : null}
                        {restoreResult.targets?.qdrant
                          ? `Qdrant: ${restoreResult.targets.qdrant.length} tập vector`
                          : null}
                      </p>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Workspace Evidence Backups Table */}
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Archive className="size-4 text-primary" />
                  <span>Bản sao lưu Bằng chứng Đơn vị</span>
                </h3>
                <p className="text-xs text-muted-foreground">
                  Gói lưu trữ đóng gói tài liệu nguồn, văn bản OCR và bằng chứng
                  rà soát của đơn vị hiện tại.
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 gap-1.5 text-xs"
                onClick={handleCreateAndDownloadEvidenceBackup}
                disabled={!effectiveWorkspaceId || isCreatingEvidenceBackup}
              >
                {isCreatingEvidenceBackup ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    <span>
                      {evidenceBackupStatusText || "Đang xử lý bản sao lưu..."}
                    </span>
                  </>
                ) : (
                  <>
                    <Download className="size-3.5" />
                    <span>Sao lưu & Tải gói bằng chứng</span>
                  </>
                )}
              </Button>
            </div>

            <div className="rounded-lg border border-border/60 bg-card overflow-hidden">
              {isLoadingBackups || isLoadingWorkspaces ? (
                <div className="py-16 text-center text-xs text-muted-foreground">
                  <RefreshCw className="size-5 animate-spin mx-auto mb-2 text-primary" />
                  <span>Đang tải bản sao lưu bằng chứng...</span>
                </div>
              ) : backups.length === 0 ? (
                <EmptyState
                  icon={Archive}
                  title="Chưa có bản sao lưu bằng chứng nào"
                  description="Bấm Sao lưu & Tải gói bằng chứng ở góc trên để tạo và tải xuống gói lưu trữ cho đơn vị."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 text-xs">
                      <TableHead className="w-[180px]">Mã sao lưu</TableHead>
                      <TableHead className="w-[110px]">Trạng thái</TableHead>
                      <TableHead className="w-[120px]">Dung lượng</TableHead>
                      <TableHead>Mã băm SHA-256</TableHead>
                      <TableHead className="w-[160px]">Thời gian tạo</TableHead>
                      <TableHead className="w-[80px] text-right">
                        Tải về
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {backups.map((bak) => (
                      <TableRow key={bak.id} className="h-11 text-xs">
                        <TableCell className="font-mono text-[11px] text-foreground flex items-center gap-1.5">
                          <span
                            className="truncate max-w-[120px]"
                            title={bak.id}
                          >
                            {bak.id}
                          </span>
                          <CopyButton value={bak.id} className="size-6" />
                        </TableCell>
                        <TableCell>{statusBadge(bak.status)}</TableCell>
                        <TableCell className="text-muted-foreground text-[11px] font-mono">
                          {formatBytes(bak.size_bytes)}
                        </TableCell>
                        <TableCell className="text-muted-foreground font-mono text-[11px]">
                          {bak.sha256 ? (
                            <div className="flex items-center gap-1">
                              <span
                                className="truncate max-w-[160px]"
                                title={bak.sha256}
                              >
                                {bak.sha256}
                              </span>
                              <CopyButton
                                value={bak.sha256}
                                className="size-6"
                              />
                            </div>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-[11px]">
                          {formatDate(bak.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          {bak.status === "completed" &&
                          effectiveWorkspaceId ? (
                            <Button
                              type="button"
                              variant="ghost"
                              size="sm"
                              className="size-7 p-0"
                              title="Tải tệp nén an toàn"
                              disabled={downloadingBackupId === bak.id}
                              onClick={() =>
                                void handleDownloadEvidenceBackup(bak.id)
                              }
                            >
                              {downloadingBackupId === bak.id ? (
                                <Loader2 className="size-3.5 animate-spin text-primary" />
                              ) : (
                                <Download className="size-3.5 text-muted-foreground hover:text-foreground" />
                              )}
                            </Button>
                          ) : (
                            <span className="text-muted-foreground text-[11px]">
                              —
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

      {/* Confirmation Dialog for Destructive Restore */}
      <Dialog open={confirmRestoreOpen} onOpenChange={setConfirmRestoreOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Xác nhận khôi phục dữ liệu hệ thống</DialogTitle>
            <DialogDescription>
              Thao tác này sẽ ghi đè dữ liệu hiện tại bằng nội dung từ tệp{" "}
              <strong className="text-foreground">{restoreFile?.name}</strong>{" "}
              (phạm vi:{" "}
              <strong className="text-foreground">
                {restoreTarget === "all"
                  ? "PostgreSQL & Qdrant"
                  : restoreTarget === "postgres"
                    ? "Chỉ PostgreSQL"
                    : "Chỉ Qdrant"}
              </strong>
              ). Hãy chắc chắn bạn đã sao lưu bản hiện tại trước khi tiếp tục.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmRestoreOpen(false)}
              disabled={isRestoring}
            >
              Hủy
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => void handleConfirmRestore()}
              disabled={isRestoring}
              className="gap-1.5"
            >
              {isRestoring ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Đang khôi phục...</span>
                </>
              ) : (
                <>
                  <RotateCcw className="size-3.5" />
                  <span>Xác nhận khôi phục</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
