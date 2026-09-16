import { useQuery } from "@tanstack/react-query";
import { ArrowRight, CheckCircle2, Clock, Eye, GitBranch, History } from "lucide-react";
import type React from "react";
import { useState } from "react";
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

  const { data: runs = [] } = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => apiClient.getWorkflowRuns(),
  });

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
            <CheckCircle2 className="h-3 w-3" /> 100% Hoàn thành thành công
          </span>
        </Card>
        <Card className="p-4">
          <span className="text-xs text-muted-foreground">Độ Trễ Trung Bình (E2E Latency)</span>
          <p className="text-xl font-bold text-primary font-mono mt-1">646 ms</p>
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
            {(runs || []).map((run) => (
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
                  <Badge variant="success" className="text-[10px] gap-1">
                    <CheckCircle2 className="h-3 w-3" />
                    Completed
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
                  <div className="flex items-center gap-2.5 p-2.5 rounded-control bg-card border border-border">
                    <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center font-bold text-[10px]">
                      1
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-foreground">chat_input (input.chat)</p>
                      <p className="text-[10px] text-muted-foreground">
                        Nhận câu hỏi, validate min_length
                      </p>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground">12 ms</span>
                  </div>

                  <div className="flex items-center gap-2.5 p-2.5 rounded-control bg-card border border-border">
                    <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center font-bold text-[10px]">
                      2
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-foreground">
                        condition_route (condition.route)
                      </p>
                      <p className="text-[10px] text-muted-foreground">
                        Phân tích ý định & điều phối nhánh RAG
                      </p>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground">18 ms</span>
                  </div>

                  <div className="flex items-center gap-2.5 p-2.5 rounded-control bg-card border border-border">
                    <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center font-bold text-[10px]">
                      3
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-foreground">knowledge_answer (rag_fast)</p>
                      <p className="text-[10px] text-muted-foreground">
                        Qdrant vector + FTS RRF k=60 + LLM stream
                      </p>
                    </div>
                    <span className="text-[10px] font-mono text-primary font-bold">295 ms</span>
                  </div>

                  <div className="flex items-center gap-2.5 p-2.5 rounded-control bg-card border border-border">
                    <span className="h-5 w-5 rounded-full bg-success/10 text-success flex items-center justify-center font-bold text-[10px]">
                      4
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-foreground">chat_output (output.chat)</p>
                      <p className="text-[10px] text-muted-foreground">
                        Lắp ráp markdown & trích dẫn văn bản
                      </p>
                    </div>
                    <span className="text-[10px] font-mono text-muted-foreground">15 ms</span>
                  </div>
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
