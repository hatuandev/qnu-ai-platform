import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Eye,
  GitBranch,
  History,
  Inbox,
  RefreshCw,
  ShieldAlert,
  UserCheck,
  XCircle,
} from "lucide-react";
import type React from "react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Spinner } from "../components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Textarea } from "../components/ui/textarea";
import { type WorkflowApproval, type WorkflowRun, apiClient } from "../services/api-client";

export interface RunsPageProps {
  currentPath?: string;
  onNavigate?: (path: string) => void;
  onNavigateToCanvas?: () => void;
}

export const RunsPage: React.FC<RunsPageProps> = ({
  currentPath,
  onNavigate,
  onNavigateToCanvas,
}) => {
  const [selectedRun, setSelectedRun] = useState<WorkflowRun | null>(null);
  const [copiedLinkRunId, setCopiedLinkRunId] = useState<string | null>(null);

  // Approval Dialog state
  const [activeApproval, setActiveApproval] = useState<WorkflowApproval | null>(null);
  const [approvalDecision, setApprovalDecision] = useState<"approved" | "rejected">("approved");
  const [decidedBy, setDecidedBy] = useState("Cán bộ vận hành QNU");
  const [decisionReason, setDecisionReason] = useState("");
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // Workflow runs query
  const {
    data: runs = [],
    error,
    isPending,
    refetch: refetchRuns,
  } = useQuery({
    queryKey: ["workflow-runs"],
    queryFn: () => apiClient.getWorkflowRuns(),
  });

  // Pending approvals query (auto-refreshed for active operations)
  const {
    data: pendingApprovals = [],
    isPending: isPendingApprovals,
    refetch: refetchApprovals,
  } = useQuery({
    queryKey: ["workflow-pending-approvals"],
    queryFn: () => apiClient.getPendingApprovals(),
    refetchInterval: 8000,
  });

  const runIdFromPath = useMemo(() => {
    if (currentPath?.startsWith("/runs/")) {
      return decodeURIComponent(currentPath.replace("/runs/", ""));
    }
    return null;
  }, [currentPath]);

  useEffect(() => {
    if (runIdFromPath && runs.length > 0) {
      const match = runs.find((r) => r.id === runIdFromPath);
      if (match) {
        setSelectedRun(match);
      }
    }
  }, [runIdFromPath, runs]);

  const handleOpenRun = (run: WorkflowRun) => {
    setSelectedRun(run);
    onNavigate?.(`/runs/${encodeURIComponent(run.id)}`);
  };

  const handleCloseRun = () => {
    setSelectedRun(null);
    onNavigate?.("/runs");
  };

  const handleCopyLink = (runId: string) => {
    const url = `${window.location.origin}/runs/${encodeURIComponent(runId)}`;
    void navigator.clipboard.writeText(url);
    setCopiedLinkRunId(runId);
    toast.success("Đã sao chép liên kết trực tiếp tới phiên chạy!");
    setTimeout(() => setCopiedLinkRunId(null), 2000);
  };

  const handleOpenDecisionDialog = (
    approval: WorkflowApproval,
    decision: "approved" | "rejected"
  ) => {
    setActiveApproval(approval);
    setApprovalDecision(decision);
    setDecidedBy("Cán bộ vận hành QNU");
    setDecisionReason(
      decision === "approved"
        ? "Đã thẩm định và đồng ý chuyển tiếp tiến trình workflow."
        : "Nội dung cần chỉnh sửa, từ chối phát hành tại checkpoint này."
    );
  };

  const handleSubmitDecision = async () => {
    if (!activeApproval) return;
    if (!decidedBy.trim()) {
      toast.error("Vui lòng nhập họ tên hoặc chức danh người phê duyệt.");
      return;
    }

    setIsSubmittingDecision(true);
    try {
      const isApproved = approvalDecision === "approved";
      await apiClient.decideApproval(activeApproval.execution_id, activeApproval.id, {
        approved: isApproved,
        decided_by: decidedBy.trim(),
        decision_reason: decisionReason.trim() || undefined,
      });

      toast.success(
        isApproved
          ? `Đã phê duyệt checkpoint [${activeApproval.node_id}]. Luồng quy trình tiếp tục thực thi!`
          : `Đã từ chối checkpoint [${activeApproval.node_id}]. Phiên chạy đã được cập nhật.`
      );

      setActiveApproval(null);
      void refetchRuns();
      void refetchApprovals();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Xử lý phê duyệt thất bại.");
    } finally {
      setIsSubmittingDecision(false);
    }
  };

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
            {pendingApprovals.length > 0 && (
              <Badge variant="warning" className="animate-pulse text-xs">
                {pendingApprovals.length} Chờ duyệt
              </Badge>
            )}
          </h1>
          <p className="text-xs text-muted-foreground mt-1">
            Theo dõi từng phiên chạy workflow, số node đã qua, độ trễ và phê duyệt checkpoint
            Human-in-the-loop trực tiếp.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              void refetchRuns();
              void refetchApprovals();
            }}
            className="h-8 text-xs gap-1.5"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Làm mới</span>
          </Button>

          {onNavigateToCanvas && (
            <Button size="sm" onClick={onNavigateToCanvas} className="h-8 text-xs gap-1.5">
              <GitBranch className="h-3.5 w-3.5" />
              <span>Mở Visual DAG Studio</span>
            </Button>
          )}
        </div>
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
          <span className="text-xs text-muted-foreground">Hộp Thư Phê Duyệt (HITL Inbox)</span>
          <p className="text-xl font-bold text-warning font-mono mt-1">
            {pendingApprovals.length} Yêu cầu
          </p>
          <span className="text-[11px] text-muted-foreground">
            {pendingApprovals.length > 0
              ? "Cần cán bộ kiểm tra & quyết định"
              : "Tất cả chốt kiểm duyệt đã hoàn tất"}
          </span>
        </Card>
      </div>

      {/* Approval Inbox Section */}
      <Card className="p-4 border-warning/40 bg-warning/5">
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <Inbox className="h-4 w-4 text-warning" />
            <h2 className="text-sm font-bold text-foreground">
              Hộp Thư Phê Duyệt Tác Vụ (Human-in-the-Loop Approval Inbox)
            </h2>
            <Badge
              variant={pendingApprovals.length > 0 ? "warning" : "outline"}
              className="text-[10px] font-mono"
            >
              {pendingApprovals.length} Chờ xử lý
            </Badge>
          </div>

          <span className="text-[11px] text-muted-foreground">Tự động cập nhật mỗi 8 giây</span>
        </div>

        {isPendingApprovals ? (
          <div className="flex items-center gap-2 py-3 text-xs text-muted-foreground">
            <Spinner className="h-3.5 w-3.5 text-primary" />
            Đang đồng bộ hộp thư phê duyệt…
          </div>
        ) : pendingApprovals.length === 0 ? (
          <div className="p-4 rounded-surface border border-border/50 bg-background/50 text-xs text-muted-foreground text-center">
            Không có checkpoint nào đang chờ phê duyệt. Toàn bộ tiến trình DAG đang vận hành bình
            thường.
          </div>
        ) : (
          <div className="space-y-2.5">
            {pendingApprovals.map((approval) => (
              <div
                key={approval.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-control border border-warning/30 bg-background shadow-sm"
              >
                <div className="space-y-1 min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="warning" className="text-[10px] font-mono">
                      {approval.node_id}
                    </Badge>
                    <span className="font-mono text-xs font-bold text-foreground">
                      Run: {approval.execution_id}
                    </span>
                    <span className="text-[11px] text-muted-foreground font-mono">
                      Checkpoint: {approval.checkpoint_id}
                    </span>
                  </div>
                  <p className="text-xs text-foreground font-medium">
                    {approval.description ||
                      "Workflow đã tạm dừng tại chốt kiểm duyệt. Chờ cán bộ chuyên môn phê duyệt trước khi đi tiếp."}
                  </p>
                  <p className="text-[10px] text-muted-foreground font-mono">
                    Yêu cầu tạo lúc: {approval.created_at}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenDecisionDialog(approval, "rejected")}
                    className="h-8 text-xs text-destructive hover:bg-destructive/10 border-destructive/30 gap-1"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Từ chối</span>
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleOpenDecisionDialog(approval, "approved")}
                    className="h-8 text-xs bg-emerald-600 hover:bg-emerald-700 text-white gap-1"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Phê duyệt</span>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

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
            onClick={() => void refetchRuns()}
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
              <TableHead className="text-right">Hành Động / Chi Tiết</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => {
              const matchingApproval = pendingApprovals.find(
                (a) => a.execution_id === run.id && a.status === "pending"
              );

              return (
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
                      {run.status === "paused_for_approval" ? (
                        <ShieldAlert className="h-3 w-3 animate-pulse" />
                      ) : null}
                      {getStatusPresentation(run.status).label}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      {matchingApproval && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleOpenDecisionDialog(matchingApproval, "approved")}
                          className="h-7 text-xs text-warning border-warning/40 hover:bg-warning/10 gap-1 mr-1"
                          title="Quyết định phê duyệt checkpoint ngay"
                        >
                          <UserCheck className="h-3.5 w-3.5" />
                          <span>Duyệt ngay</span>
                        </Button>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopyLink(run.id)}
                        title="Sao chép liên kết phiên chạy"
                        className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
                      >
                        {copiedLinkRunId === run.id ? (
                          <Check className="h-3.5 w-3.5 text-success" />
                        ) : (
                          <Copy className="h-3.5 w-3.5" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenRun(run)}
                        className="h-7 text-xs text-primary hover:text-primary/80 gap-1"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Xem Trace</span>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
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
          if (!open) handleCloseRun();
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <div className="flex items-center justify-between gap-2 pr-6">
              <DialogTitle className="text-sm font-bold flex items-center gap-2">
                <History className="h-4 w-4 text-primary" />
                Chi Tiết Truy Vết Thực Thi: {selectedRun?.id}
              </DialogTitle>
              {selectedRun && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleCopyLink(selectedRun.id)}
                  className="h-7 text-xs gap-1.5"
                >
                  {copiedLinkRunId === selectedRun.id ? (
                    <>
                      <Check className="h-3 w-3 text-success" />
                      <span>Đã chép</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3 w-3" />
                      <span>Sao chép link</span>
                    </>
                  )}
                </Button>
              )}
            </div>
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

      {/* Decision Dialog for Human Approval */}
      <Dialog
        open={activeApproval !== null}
        onOpenChange={(open) => {
          if (!open && !isSubmittingDecision) setActiveApproval(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-base font-bold flex items-center gap-2">
              {approvalDecision === "approved" ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span>Xác Nhận Phê Duyệt Checkpoint</span>
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4 text-destructive" />
                  <span>Xác Nhận Từ Chối Checkpoint</span>
                </>
              )}
            </DialogTitle>
            <DialogDescription className="text-xs">
              Quyết định này sẽ tiếp tục hoặc đình chỉ tiến trình thực thi DAG tương ứng.
            </DialogDescription>
          </DialogHeader>

          {activeApproval && (
            <div className="space-y-3.5 text-xs">
              <div className="rounded-control border border-border bg-muted/30 p-3 space-y-1.5 font-mono text-[11px]">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Node Checkpoint:</span>
                  <span className="font-bold text-foreground">{activeApproval.node_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Mã Thực Thi (Run ID):</span>
                  <span className="text-foreground">{activeApproval.execution_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Mã Checkpoint:</span>
                  <span className="text-muted-foreground">{activeApproval.checkpoint_id}</span>
                </div>
              </div>

              {activeApproval.description && (
                <div className="p-2.5 rounded-control border border-warning/30 bg-warning/5 text-xs text-foreground">
                  <span className="font-semibold block mb-0.5 text-warning">
                    Thông điệp kiểm duyệt:
                  </span>
                  {activeApproval.description}
                </div>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="decision-mode" className="text-xs font-semibold">
                  Hành động quyết định:
                </Label>
                <div className="grid grid-cols-2 gap-2" id="decision-mode">
                  <Button
                    type="button"
                    variant={approvalDecision === "approved" ? "default" : "outline"}
                    className={`h-8 text-xs gap-1.5 ${
                      approvalDecision === "approved"
                        ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                        : ""
                    }`}
                    onClick={() => setApprovalDecision("approved")}
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Phê duyệt (Tiếp tục)</span>
                  </Button>
                  <Button
                    type="button"
                    variant={approvalDecision === "rejected" ? "destructive" : "outline"}
                    className="h-8 text-xs gap-1.5"
                    onClick={() => setApprovalDecision("rejected")}
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Từ chối (Dừng)</span>
                  </Button>
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="decided-by" className="text-xs font-semibold">
                  Cán bộ phê duyệt <span className="text-destructive">*</span>:
                </Label>
                <Input
                  id="decided-by"
                  value={decidedBy}
                  onChange={(e) => setDecidedBy(e.target.value)}
                  placeholder="Ví dụ: Cán bộ Tuyển sinh / Phòng Đào tạo"
                  className="h-8 text-xs"
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="decision-reason" className="text-xs font-semibold">
                  Lý do / Ý kiến chỉ đạo:
                </Label>
                <Textarea
                  id="decision-reason"
                  rows={3}
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  placeholder="Nhập ý kiến chuyên môn hoặc căn cứ phê duyệt..."
                  className="text-xs"
                />
              </div>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setActiveApproval(null)}
              disabled={isSubmittingDecision}
              className="h-8 text-xs"
            >
              Hủy bỏ
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => void handleSubmitDecision()}
              disabled={isSubmittingDecision}
              className={`h-8 text-xs gap-1.5 ${
                approvalDecision === "approved"
                  ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                  : "bg-destructive hover:bg-destructive/90 text-destructive-foreground"
              }`}
            >
              {isSubmittingDecision ? (
                <>
                  <Spinner className="h-3.5 w-3.5" />
                  <span>Đang xử lý…</span>
                </>
              ) : approvalDecision === "approved" ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Xác nhận Phê duyệt</span>
                </>
              ) : (
                <>
                  <XCircle className="h-3.5 w-3.5" />
                  <span>Xác nhận Từ chối</span>
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};
