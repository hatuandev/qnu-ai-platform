import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  GitBranch,
  History,
  RefreshCw,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { type WorkflowRun, apiClient } from "../services/api-client";

export const RunsPage: React.FC<{ onNavigateToCanvas?: () => void }> = ({ onNavigateToCanvas }) => {
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);

  const {
    data: runs = [],
    error,
    isPending,
    refetch,
  } = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => apiClient.getWorkflowRuns(),
  });
  const completedCount = runs.filter((run) => run.status === "completed").length;
  const averageLatency = useMemo(
    () =>
      runs.length
        ? Math.round(runs.reduce((sum, run) => sum + run.duration_ms, 0) / runs.length)
        : 0,
    [runs]
  );

  const getStatusPresentation = (status: WorkflowRun["status"]) => {
    if (status === "completed") return { label: "Hoàn thành", variant: "success" as const };
    if (status === "failed") return { label: "Thất bại", variant: "destructive" as const };
    if (status === "paused_for_approval")
      return { label: "Chờ phê duyệt", variant: "warning" as const };
    return { label: "Đang chạy", variant: "info" as const };
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            Lịch Sử Thực Thi Luồng Điều Phối (DAG Runs)
            <Badge variant="outline" className="font-mono text-xs">
              Audit Trails
            </Badge>
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Theo dõi từng phiên chạy workflow, số node đã qua, độ trễ và trạng thái checkpoint lưu
            trữ.
          </p>
        </div>

        {onNavigateToCanvas && (
          <Button size="sm" onClick={onNavigateToCanvas} className="h-8 text-xs gap-1.5">
            <GitBranch className="h-3.5 w-3.5" />
            <span>Mở Visual DAG Studio</span>
          </Button>
        )}
      </div>

      {/* Summary KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Tổng Phiên Thực Thi</span>
          <p className="text-xl font-bold text-foreground mt-1">{runs.length} Phiên chạy</p>
          <span className="text-[11px] text-success flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" /> {completedCount}/{runs.length || 0} hoàn thành
          </span>
        </Card>
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Độ Trễ Trung Bình (E2E Latency)</span>
          <p className="text-xl font-bold text-primary font-mono mt-1">{averageLatency} ms</p>
          <span className="text-[11px] text-muted-foreground">Bao gồm RAG & LLM inference</span>
        </Card>
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Chế Độ Lưu Trữ Checkpoints</span>
          <p className="text-xl font-bold text-foreground font-mono mt-1">PostgreSQL State</p>
          <span className="text-[11px] text-muted-foreground">
            Bảo đảm tính toàn vẹn trạng thái
          </span>
        </Card>
      </div>

      {isPending && (
        <div className="flex items-center gap-2 rounded-surface border border-border bg-card p-4 text-xs text-muted-foreground">
          <RefreshCw className="size-3.5 animate-spin text-primary" />
          Đang tải lịch sử thực thi từ Backend…
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between gap-3 rounded-surface border border-destructive/30 bg-destructive/10 p-4 text-xs text-destructive">
          <span className="flex items-center gap-2">
            <AlertCircle className="size-3.5" />
            {error instanceof Error ? error.message : "Không tải được lịch sử workflow."}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => void refetch()}
          >
            Thử lại
          </Button>
        </div>
      )}

      {/* Runs Table */}
      <div className="rounded-surface border border-border bg-card overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mã Thực Thi (Run ID)</TableHead>
              <TableHead>Tên Quy Trình Workflow</TableHead>
              <TableHead>Tiến Độ Bước</TableHead>
              <TableHead>Thời Gian Chạy</TableHead>
              <TableHead>Khởi Chạy Lúc</TableHead>
              <TableHead>Trạng Thái</TableHead>
              <TableHead className="text-right">Chi Tiết</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id}>
                <TableCell className="font-mono text-xs font-bold text-foreground">
                  {run.id}
                </TableCell>
                <TableCell className="text-xs font-semibold text-foreground">
                  <div className="flex items-center gap-1.5">
                    <History className="h-3.5 w-3.5 text-primary" />
                    <span>{run.workflow_name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-xs font-mono">
                  {run.steps_completed}/{run.total_steps} nodes
                </TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3 text-warning" />
                    {run.duration_ms} ms
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  {run.started_at}
                </TableCell>
                <TableCell>
                  <Badge
                    variant={getStatusPresentation(run.status).variant}
                    className="text-[10px] gap-1"
                  >
                    {run.status === "completed" ? <CheckCircle2 className="h-3 w-3" /> : null}
                    {getStatusPresentation(run.status).label}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedRun(run)}
                    className="h-7 text-xs text-primary hover:text-primary/80 gap-1"
                  >
                    <Eye className="h-3.5 w-3.5" />
                    <span>Xem Trace</span>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!isPending && !error && runs.length === 0 && (
          <div className="p-10 text-center text-xs text-muted-foreground">
            Chưa có phiên thực thi nào được ghi nhận.
          </div>
        )}
      </div>

      {/* Trace Detail Modal */}
      <Dialog
        open={selectedRun !== null}
        onOpenChange={(open) => {
          if (!open) setSelectedRun(null);
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold flex items-center gap-2">
              <History className="h-4 w-4 text-primary" />
              Chi Tiết Truy Vết Thực Thi: {selectedRun?.id}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Các bước checkpoint của luồng quy trình điều phối AI
            </DialogDescription>
          </DialogHeader>

          {selectedRun && (
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-2 p-3 rounded-control bg-muted/40 border border-border text-[11px]">
                <div>
                  <span className="text-muted-foreground">Quy trình:</span>
                  <p className="font-semibold text-foreground">{selectedRun.workflow_name}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Tổng thời gian:</span>
                  <p className="font-mono font-bold text-primary">{selectedRun.duration_ms} ms</p>
                </div>
              </div>

              {/* Execution timeline */}
              <div className="space-y-2.5">
                <span className="font-bold text-foreground text-xs uppercase tracking-wider block">
                  Tiến trình Checkpoints (DAG Nodes Trace):
                </span>

                <div className="space-y-2">
                  {selectedRun.executed_nodes.length > 0 ? (
                    selectedRun.executed_nodes.map((nodeId, index) => (
                      <div
                        className="flex items-center gap-2.5 rounded-control border border-border bg-card p-2.5"
                        key={`${selectedRun.id}-${nodeId}-${index}`}
                      >
                        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success/10 text-[10px] font-bold text-success">
                          {index + 1}
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-foreground">{nodeId}</p>
                          <p className="text-[10px] text-muted-foreground">
                            Node được runtime ghi nhận trong execution trace
                          </p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="rounded-control border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
                      Backend chưa trả trace chi tiết cho phiên chạy này.
                    </p>
                  )}
                </div>
              </div>

              {onNavigateToCanvas && (
                <div className="pt-2 border-t border-border flex justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedRun(null);
                      onNavigateToCanvas();
                    }}
                    className="text-xs gap-1"
                  >
                    <span>Xem sơ đồ trực quan</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
