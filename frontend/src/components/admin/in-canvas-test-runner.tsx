import {
  Bot,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  MessageSquare,
  Play,
  RotateCcw,
  Send,
  Sparkles,
  UserCheck,
  X,
} from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { type WorkflowExecutionResponse, workflowsApi } from "../../services/workflows-api";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

export interface NodeExecutionState {
  status: "idle" | "running" | "completed" | "failed" | "waiting";
  durationMs?: number;
  error?: string;
}

export interface InCanvasTestRunnerProps {
  workflowId: string;
  workflowName: string;
  isOpen: boolean;
  onClose: () => void;
  onUpdateExecutionState: (nodeStates: Record<string, NodeExecutionState>) => void;
  onResetCanvasStates: () => void;
}

const QUICK_PROMPTS_BY_WORKFLOW: Record<string, string[]> = {
  admissions: [
    "Điểm chuẩn ngành Công nghệ thông tin năm 2024?",
    "Học phí ngành Sư phạm Toán và hỗ trợ NĐ 116?",
    "Xin chào, tôi muốn tìm hiểu thông tin tuyển sinh.",
  ],
  regulations: [
    "Số tín chỉ tối thiểu sinh viên cần đăng ký một học kỳ?",
    "Điều kiện nhận học bổng khuyến khích học tập?",
    "Quy định cảnh báo học vụ và buộc thôi học?",
  ],
  drafting: [
    "Soạn thảo Quyết định khen thưởng sinh viên đạt giải Nhất NCKH.",
    "Quy cách căn lề và thể thức văn bản theo Nghị định 30?",
    "Soạn Tờ trình xin phê duyệt kế hoạch tổ chức hội nghị.",
  ],
  question_bank: [
    "Biên soạn 1 câu hỏi trắc nghiệm Bloom mức Vận dụng học phần CSDL.",
    "Giải thích ma trận CLO tương ứng với Bloom Level 2?",
    "Tạo bảng câu hỏi trắc nghiệm kiểm thử kết xuất Excel.",
  ],
  library: [
    "Thời hạn mượn sách và số lượng tối đa của sinh viên?",
    "Cách truy cập cơ sở dữ liệu Scopus và ScienceDirect từ xa?",
    "Quy định nộp luận văn tốt nghiệp vào kho thư viện số?",
  ],
};

function getResponseText(response: WorkflowExecutionResponse): string {
  const output = response.outputs.answer ?? response.outputs.text ?? response.outputs.message;
  return typeof output === "string" ? output : "Chưa có nội dung phản hồi từ workflow.";
}

export const InCanvasTestRunner: React.FC<InCanvasTestRunnerProps> = ({
  workflowId,
  workflowName,
  isOpen,
  onClose,
  onUpdateExecutionState,
  onResetCanvasStates,
}) => {
  const [inputMessage, setInputMessage] = useState<string>(
    QUICK_PROMPTS_BY_WORKFLOW[workflowId]?.[0] || "Xin chào, cho tôi hỏi thông tin."
  );
  const [isExecuting, setIsExecuting] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("chat");
  const [lastResponse, setLastResponse] = useState<WorkflowExecutionResponse | null>(null);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [isHumanApproved, setIsHumanApproved] = useState<boolean>(false);
  const [approvalId, setApprovalId] = useState<string | null>(null);
  const [executionError, setExecutionError] = useState<string | null>(null);

  const assistantCode = workflowId.replace(/-assistant$/, "");
  const quickPrompts =
    QUICK_PROMPTS_BY_WORKFLOW[assistantCode] || QUICK_PROMPTS_BY_WORKFLOW.admissions;

  const handleCopyText = useCallback((text: string) => {
    if (!navigator.clipboard) return;
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  }, []);

  const handleResetRun = useCallback(() => {
    setLastResponse(null);
    setIsHumanApproved(false);
    setApprovalId(null);
    setExecutionError(null);
    onResetCanvasStates();
  }, [onResetCanvasStates]);

  const handleExecute = async () => {
    if (!inputMessage.trim() || isExecuting) return;

    setIsExecuting(true);
    setIsHumanApproved(false);
    setApprovalId(null);
    setExecutionError(null);
    setActiveTab("chat");

    // Clear previous states
    onResetCanvasStates();

    try {
      // 1. Initial State: Chat input running
      onUpdateExecutionState({
        chat_input: { status: "running" },
      });

      // 2. Call API
      const response = await workflowsApi.execute({
        workflow_id: workflowId,
        inputs: { message: inputMessage.trim(), text: inputMessage.trim() },
      });

      // 3. Render the server execution trace exactly as returned by the runtime.
      const executed = response.executed_nodes;
      const currentStates: Record<string, NodeExecutionState> = {};
      for (const nodeId of executed) {
        currentStates[nodeId] = {
          status:
            response.status === "paused_for_approval" && nodeId === response.paused_node_id
              ? "waiting"
              : response.status === "failed"
                ? "failed"
                : "completed",
          error: response.status === "failed" ? response.error_message || undefined : undefined,
        };
      }
      onUpdateExecutionState({ ...currentStates });
      setLastResponse(response);
      setApprovalId(
        typeof response.outputs.approval_id === "string" ? response.outputs.approval_id : null
      );
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Lỗi thực thi luồng DAG.";
      setExecutionError(message);
      onUpdateExecutionState({
        chat_input: { status: "failed", error: message },
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleApproveCheckpoint = async () => {
    if (!lastResponse || !approvalId || isExecuting) return;
    setIsExecuting(true);
    setExecutionError(null);
    try {
      const response = await workflowsApi.decideApproval(lastResponse.execution_id, approvalId, {
        approved: true,
        decided_by: "platform-admin",
      });
      setIsHumanApproved(true);
      const completedStates = Object.fromEntries(
        response.executed_nodes.map((nodeId) => [nodeId, { status: "completed" as const }])
      );
      onUpdateExecutionState(completedStates);
      setLastResponse(response);
      setApprovalId(null);
    } catch (error: unknown) {
      setExecutionError(error instanceof Error ? error.message : "Không thể phê duyệt checkpoint.");
    } finally {
      setIsExecuting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <aside
      aria-label="In-Canvas Test Runner"
      className="absolute bottom-4 right-4 z-20 w-[420px] max-h-[85vh] flex flex-col rounded-surface bg-card/95 backdrop-blur-md border border-border shadow-xl overflow-hidden transition-all animate-in fade-in slide-in-from-bottom-3 duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Play className="size-3.5 fill-primary" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <span>Trình Chạy Thử Nghiệm Luồng (In-Canvas)</span>
            </h3>
            <p className="text-[11px] text-muted-foreground line-clamp-1">{workflowName}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground"
            onClick={handleResetRun}
            title="Xóa trạng thái chạy"
          >
            <RotateCcw className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-muted-foreground hover:text-foreground"
            onClick={onClose}
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Body / Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 max-h-[calc(85vh-130px)]">
        {/* Input Textarea */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-muted-foreground font-medium">
            <span className="flex items-center gap-1">
              <MessageSquare className="size-3 text-primary" />
              <span>Câu hỏi đầu vào (Chat Input):</span>
            </span>
            <span className="font-mono text-[10px]">{inputMessage.length} ký tự</span>
          </div>
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Nhập câu hỏi để chạy thử qua đồ thị..."
            rows={3}
            className="w-full text-xs rounded-control border border-border bg-background p-2.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleExecute();
              }
            }}
          />
        </div>

        {/* Quick Prompts */}
        <div className="space-y-1.5">
          <span className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider flex items-center gap-1">
            <Sparkles className="size-3 text-primary" />
            <span>Câu hỏi gợi ý nhanh</span>
          </span>
          <div className="flex flex-wrap gap-1.5">
            {quickPrompts.map((prompt) => (
              <button
                type="button"
                key={prompt}
                onClick={() => setInputMessage(prompt)}
                className="text-[11px] text-left px-2 py-1 rounded-control bg-muted/60 hover:bg-muted border border-border/80 text-foreground transition-all line-clamp-1 max-w-full cursor-pointer"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            className="w-full h-9 text-xs font-semibold"
            disabled={!inputMessage.trim() || isExecuting}
            onClick={handleExecute}
          >
            {isExecuting ? (
              <>
                <span className="size-3.5 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin mr-1.5" />
                <span>Đang điều phối luồng DAG...</span>
              </>
            ) : (
              <>
                <Send className="size-3.5 mr-1.5" />
                <span>Chạy Thử Luồng (Run DAG)</span>
              </>
            )}
          </Button>
        </div>

        {executionError && (
          <div className="rounded-control border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
            {executionError}
          </div>
        )}

        {/* Approval only appears after a real paused execution returns an approval id. */}
        {lastResponse?.status === "paused_for_approval" && approvalId && !isHumanApproved && (
          <div className="p-3 rounded-surface bg-warning/10 border border-warning/30 space-y-2 animate-in fade-in duration-200">
            <div className="flex items-start gap-2">
              <UserCheck className="size-4 text-warning shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-foreground">Điểm Dừng Phê Duyệt Cán Bộ</p>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {String(
                    lastResponse.outputs.action_required ||
                      "Cần cán bộ chuyên môn xác nhận trước khi tiếp tục."
                  )}
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button
                size="sm"
                variant="default"
                className="h-7 text-xs bg-warning text-warning-foreground hover:bg-warning/90"
                onClick={handleApproveCheckpoint}
              >
                <Check className="size-3 mr-1" />
                <span>Phê Duyệt Ngay (Quick Approve)</span>
              </Button>
            </div>
          </div>
        )}

        {/* Results Area */}
        {lastResponse && (
          <div className="border-t border-border pt-3 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="size-3.5 text-success" />
                <span className="text-xs font-bold text-foreground">Kết Quả Thực Thi</span>
                <Badge variant="outline" className="text-[10px] font-mono ml-1 text-primary">
                  {lastResponse.latency_ms}ms
                </Badge>
              </div>

              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList className="h-7 p-0.5">
                  <TabsTrigger value="chat" className="text-[11px] h-6 px-2">
                    Phản hồi
                  </TabsTrigger>
                  <TabsTrigger value="trace" className="text-[11px] h-6 px-2">
                    Trace ({lastResponse.executed_nodes.length})
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>

            {activeTab === "chat" && (
              <div className="relative p-3 rounded-surface bg-muted/40 border border-border text-xs leading-relaxed text-foreground max-h-52 overflow-y-auto">
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute top-2 right-2 size-6 text-muted-foreground hover:text-foreground"
                  onClick={() => handleCopyText(getResponseText(lastResponse))}
                  title="Sao chép kết quả"
                >
                  {isCopied ? (
                    <Check className="size-3 text-success" />
                  ) : (
                    <Copy className="size-3" />
                  )}
                </Button>
                <div
                  data-testid="test-runner-markdown-output"
                  className="prose prose-sm dark:prose-invert max-w-none text-xs"
                >
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {getResponseText(lastResponse)}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {activeTab === "trace" && (
              <div className="space-y-1.5 max-h-52 overflow-y-auto">
                {lastResponse.executed_nodes.map((nodeId, idx) => (
                  <div
                    key={nodeId}
                    className="flex items-center justify-between p-2 rounded-control bg-muted/40 border border-border/80 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span className="flex size-5 items-center justify-center rounded-full bg-primary/10 text-primary font-mono text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      <span className="font-mono font-semibold text-foreground">{nodeId}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground font-mono">
                      <Clock className="size-3 text-muted-foreground" />
                      <span>đã ghi nhận</span>
                      <span className="size-1.5 rounded-full bg-success" />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer status */}
      <div className="px-4 py-2 border-t border-border bg-muted/20 text-[11px] text-muted-foreground flex items-center justify-between">
        <span className="flex items-center gap-1">
          <Bot className="size-3 text-primary" />
          <span>DAG Engine v1.0.0</span>
        </span>
        <span className="font-mono text-[10px]">
          {isExecuting ? "Đang chạy..." : "Sẵn sàng nhận lệnh"}
        </span>
      </div>
    </aside>
  );
};
