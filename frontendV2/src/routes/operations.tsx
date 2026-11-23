import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  AlertCircle,
  Archive,
  CheckCircle2,
  Clock,
  Database,
  Download,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";
import {
  useOperationsJobsQuery,
  useWorkspaceBackupsQuery,
} from "@/api/operations/queries";
import { useWorkspacesQuery } from "@/api/workspaces/queries";
import { CopyButton } from "@/components/admin/copy-button";
import { EmptyState } from "@/components/admin/empty-state";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

function OperationsPage() {
  const [activeTab, setActiveTab] = useState<string>("jobs");
  const storeWorkspaceId = useUiStore((s) => s.activeWorkspaceId);

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
            <span>Tiến trình & Tác vụ ({jobs.length})</span>
          </TabsTrigger>
          <TabsTrigger value="backups" className="gap-2 text-xs">
            <Database className="size-3.5" />
            <span>Sao lưu & Khôi phục CSDL</span>
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

        {/* Tab 2: System Backup & Evidence Archives */}
        <TabsContent value="backups" className="space-y-6">
          {/* Global PostgreSQL + Qdrant snapshot system status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="border-border/60 bg-card">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Database className="size-4 text-emerald-600" />
                  <span className="text-sm font-semibold text-foreground">
                    Cơ sở dữ liệu PostgreSQL (Port 5432)
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Sao lưu toàn bộ 66 bảng schema và dữ liệu thực thể: Không gian
                  làm việc, Trợ lý AI, Khóa API, Phiên bản biên dịch & Dẫn chứng
                  OCR theo chuẩn toàn vẹn SHA-256.
                </p>
                <div className="bg-muted/50 rounded p-2.5 font-mono text-[11px] text-foreground space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      # Lệnh sao lưu hệ thống:
                    </span>
                    <CopyButton value="python scripts/backup_system.py --target all" />
                  </div>
                  <code className="text-primary block overflow-x-auto">
                    python scripts/backup_system.py --target all
                  </code>
                </div>
              </CardContent>
            </Card>

            <Card className="border-border/60 bg-card">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Server className="size-4 text-teal-600" />
                  <span className="text-sm font-semibold text-foreground">
                    Vector Cluster Qdrant (Port 6333)
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Trích xuất ảnh chụp nhanh (collection snapshot) cho toàn bộ
                  các tập chỉ mục vector, hỗ trợ xác thực toàn vẹn & khôi phục
                  nguyên trạng vector embedding cùng payloads.
                </p>
                <div className="bg-muted/50 rounded p-2.5 font-mono text-[11px] text-foreground space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">
                      # Lệnh kiểm tra an toàn (Dry-run):
                    </span>
                    <CopyButton value="python scripts/restore_system.py backups/<dir> --verify-only" />
                  </div>
                  <code className="text-primary block overflow-x-auto">
                    python scripts/restore_system.py &lt;dir&gt; --verify-only
                  </code>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Retention & Operational Guide */}
          <div className="rounded-lg border border-border/60 bg-card/60 p-4 space-y-2.5">
            <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
              <ShieldCheck className="size-4 text-emerald-600" />
              <span>
                Chính sách Xoay vòng & Bảo toàn Dữ liệu (Retention & Recovery
                Gates)
              </span>
            </div>
            <ul className="text-xs text-muted-foreground space-y-1.5 list-disc list-inside">
              <li>
                <strong className="text-foreground">
                  Xoay vòng tự động (Retention):
                </strong>{" "}
                Tùy chọn{" "}
                <code className="font-mono text-primary bg-muted px-1 py-0.5 rounded text-[11px]">
                  --retention-days 30
                </code>{" "}
                hoặc{" "}
                <code className="font-mono text-primary bg-muted px-1 py-0.5 rounded text-[11px]">
                  --retention-keep 10
                </code>{" "}
                giúp tự động dọn bản cũ mà không làm gián đoạn hệ thống.
              </li>
              <li>
                <strong className="text-foreground">
                  Rào chắn khôi phục (Safety Gate):
                </strong>{" "}
                Công cụ khôi phục{" "}
                <code className="font-mono text-primary bg-muted px-1 py-0.5 rounded text-[11px]">
                  restore_system.py
                </code>{" "}
                bắt buộc cờ{" "}
                <code className="font-mono text-primary bg-muted px-1 py-0.5 rounded text-[11px]">
                  --confirm-restore
                </code>{" "}
                và tự động kiểm tra chữ ký SHA-256 trước khi áp dụng vào CSDL.
              </li>
            </ul>
          </div>

          {/* Workspace Evidence Backups Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                  <Archive className="size-4 text-primary" />
                  <span>
                    Bản sao lưu Bằng chứng Đơn vị (Workspace Evidence Archives)
                  </span>
                </h3>
                <p className="text-xs text-muted-foreground">
                  Gói lưu trữ dẫn xuất đóng gói tài liệu nguồn, văn bản OCR và
                  bằng chứng rà soát của đơn vị.
                </p>
              </div>
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
                  description="Các bản sao lưu bằng chứng đóng gói được tạo qua API hoặc tác vụ bảo trì đơn vị sẽ hiển thị tại đây."
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
                              variant="ghost"
                              size="sm"
                              className="size-7 p-0"
                              asChild
                              title="Tải tệp nén an toàn"
                            >
                              <a
                                href={`/api/workspaces/${effectiveWorkspaceId}/operations/backups/${bak.id}/download`}
                                download
                              >
                                <Download className="size-3.5 text-muted-foreground hover:text-foreground" />
                              </a>
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
    </div>
  );
}
