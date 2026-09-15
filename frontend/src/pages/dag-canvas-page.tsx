import type { Edge, Node } from "@xyflow/react";
import {
  BookOpen,
  Clock,
  FileText,
  GitBranch,
  GraduationCap,
  HelpCircle,
  Info,
  Layers,
  Library,
  Play,
  ShieldAlert,
  Sliders,
  X,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { DAGCanvas, type WorkflowNodeData } from "../components/ai/dag-canvas";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Separator } from "../components/ui/separator";

interface WorkflowConfig {
  code: string;
  name: string;
  displayName: string;
  category: string;
  icon: React.ReactNode;
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
}

const WORKFLOW_REGISTRY: Record<string, WorkflowConfig> = {
  admissions: {
    code: "admissions",
    name: "admissions-assistant",
    displayName: "Luồng Trợ lý Tuyển sinh QNU",
    category: "Đào tạo & Tuyển sinh",
    icon: <GraduationCap className="h-4 w-4" />,
    nodes: [
      {
        id: "chat_input",
        type: "chatInput",
        position: { x: 250, y: 30 },
        data: {
          id: "chat_input",
          label: "Câu hỏi thí sinh / phụ huynh",
          category: "input",
          description: "Tiếp nhận câu hỏi thắc mắc tuyển sinh từ cổng thông tin.",
          configSummary: "trim: true, max_length: 10000",
          timeoutSeconds: 2,
        },
      },
      {
        id: "condition_route",
        type: "conditionRoute",
        position: { x: 250, y: 160 },
        data: {
          id: "condition_route",
          label: "Phân loại ý định (Chào hỏi / Tra cứu)",
          category: "route",
          configSummary: "intent: xin chào|hello|cảm ơn -> greeting",
          timeoutSeconds: 2,
        },
      },
      {
        id: "greeting_output",
        type: "chatOutput",
        position: { x: 50, y: 320 },
        data: {
          id: "greeting_output",
          label: "Lời chào & Gợi ý câu hỏi tuyển sinh",
          category: "output",
          description: "Phản hồi nhanh các câu hỏi xã giao và gợi ý điểm chuẩn, học phí.",
          configSummary: "format: markdown, include_citations: false",
          timeoutSeconds: 2,
        },
      },
      {
        id: "knowledge_answer",
        type: "ragKnowledge",
        position: { x: 420, y: 320 },
        data: {
          id: "knowledge_answer",
          label: "Tra cứu Đề án tuyển sinh & Điểm chuẩn",
          category: "rag",
          description: "Truy xuất Qdrant vector + Postgres FTS Tiếng Việt với RRF k=60.",
          configSummary: "retrieval_limit: 10, profile: rag_fast",
          timeoutSeconds: 30,
        },
      },
      {
        id: "citation_guard",
        type: "guardrail",
        position: { x: 420, y: 470 },
        data: {
          id: "citation_guard",
          label: "Xác thực nguồn đề án chính quy",
          category: "guard",
          description: "Chống ảo giác: Kiểm tra tính xác thực của số liệu điểm và chỉ tiêu.",
          configSummary: "require_citation_for_answer: true",
          timeoutSeconds: 2,
        },
      },
      {
        id: "chat_output",
        type: "chatOutput",
        position: { x: 420, y: 610 },
        data: {
          id: "chat_output",
          label: "Giải đáp tuyển sinh có trích dẫn",
          category: "output",
          description: "Lắp ráp bảng markdown, điểm chuẩn và dẫn chứng tài liệu gốc.",
          configSummary: "format: markdown, citations: true",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      {
        id: "e1",
        source: "chat_input",
        target: "condition_route",
        animated: true,
      },
      {
        id: "e2",
        source: "condition_route",
        target: "greeting_output",
        label: "Chào hỏi",
        style: { stroke: "#f59e0b" },
      },
      {
        id: "e3",
        source: "condition_route",
        target: "knowledge_answer",
        label: "Tra cứu điểm",
        style: { stroke: "#3b82f6" },
        animated: true,
      },
      {
        id: "e4",
        source: "knowledge_answer",
        target: "citation_guard",
        animated: true,
      },
      {
        id: "e5",
        source: "citation_guard",
        target: "chat_output",
        label: "Grounded (Hợp lệ)",
        style: { stroke: "#10b981" },
        animated: true,
      },
    ],
  },
  regulations: {
    code: "regulations",
    name: "regulations-assistant",
    displayName: "Luồng Trợ lý Quy chế Học vụ QNU",
    category: "Đào tạo & Khảo thí",
    icon: <BookOpen className="h-4 w-4" />,
    nodes: [
      {
        id: "reg_input",
        type: "chatInput",
        position: { x: 250, y: 30 },
        data: {
          id: "reg_input",
          label: "Thắc mắc quy chế đào tạo tín chỉ",
          category: "input",
          description: "Hỏi về đăng ký học phần, rút môn, cảnh báo học vụ.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "reg_rag",
        type: "ragKnowledge",
        position: { x: 250, y: 180 },
        data: {
          id: "reg_rag",
          label: "Truy cứu Quyết định 1234/QĐ-ĐHQN",
          category: "rag",
          description: "Bóc tách theo Điều/Khoản qua ClauseBasedChunker chuyên biệt.",
          configSummary: "chunker: ClauseBasedChunker, limit: 8",
          timeoutSeconds: 25,
        },
      },
      {
        id: "reg_guard",
        type: "guardrail",
        position: { x: 250, y: 340 },
        data: {
          id: "reg_guard",
          label: "Bộ lọc Zero-Hallucination Điều khoản",
          category: "guard",
          description: "Nếu không có trong quy chế, tự động kích hoạt No-Answer Policy.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "reg_output",
        type: "chatOutput",
        position: { x: 250, y: 490 },
        data: {
          id: "reg_output",
          label: "Văn bản trích dẫn Điều/Khoản & Trang",
          category: "output",
          description: "Hiển thị giải đáp kèm số hiệu văn bản pháp lý chính xác.",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "re1", source: "reg_input", target: "reg_rag", animated: true },
      { id: "re2", source: "reg_rag", target: "reg_guard", animated: true },
      { id: "re3", source: "reg_guard", target: "reg_output", animated: true },
    ],
  },
  library: {
    code: "library",
    name: "library-assistant",
    displayName: "Luồng Trợ lý Thư viện Số QNU",
    category: "Học liệu & Nghiên cứu",
    icon: <Library className="h-4 w-4" />,
    nodes: [
      {
        id: "lib_input",
        type: "chatInput",
        position: { x: 250, y: 30 },
        data: {
          id: "lib_input",
          label: "Yêu cầu mượn sách & tra cứu học liệu",
          category: "input",
          timeoutSeconds: 2,
        },
      },
      {
        id: "lib_rag",
        type: "ragKnowledge",
        position: { x: 250, y: 180 },
        data: {
          id: "lib_rag",
          label: "Tra cứu OPAC & CSDL Scopus / ScienceDirect",
          category: "rag",
          description: "Kết nối cơ sở dữ liệu thư viện trung tâm ĐH Quy Nhơn.",
          timeoutSeconds: 25,
        },
      },
      {
        id: "lib_output",
        type: "chatOutput",
        position: { x: 250, y: 340 },
        data: {
          id: "lib_output",
          label: "Thông tin vị trí kệ sách, thời hạn mượn",
          category: "output",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "le1", source: "lib_input", target: "lib_rag", animated: true },
      { id: "le2", source: "lib_rag", target: "lib_output", animated: true },
    ],
  },
  drafting: {
    code: "drafting",
    name: "drafting-assistant",
    displayName: "Luồng Soạn thảo Văn bản Hành chính (NĐ 30)",
    category: "Hành chính & Pháp chế",
    icon: <FileText className="h-4 w-4" />,
    nodes: [
      {
        id: "dft_input",
        type: "chatInput",
        position: { x: 250, y: 30 },
        data: {
          id: "dft_input",
          label: "Nhu cầu soạn thảo văn bản đơn vị",
          category: "input",
          description: "Quyết định, tờ trình, thông báo theo mẫu ĐH Quy Nhơn.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "dft_rag",
        type: "ragKnowledge",
        position: { x: 250, y: 180 },
        data: {
          id: "dft_rag",
          label: "Nạp Template chuẩn Nghị định 30/2020/NĐ-CP",
          category: "rag",
          description: "Định dạng phông Times New Roman 13-14, căn lề 20-25-30-15 mm.",
          timeoutSeconds: 20,
        },
      },
      {
        id: "dft_approval",
        type: "guardrail",
        position: { x: 250, y: 340 },
        data: {
          id: "dft_approval",
          label: "Chốt chặn Phê duyệt Cán bộ (Human-in-the-loop)",
          category: "guard",
          description: "Cán bộ xem trước bản thảo Word (.docx) trước khi chính thức phát hành.",
          timeoutSeconds: 86400,
        },
      },
      {
        id: "dft_output",
        type: "chatOutput",
        position: { x: 250, y: 490 },
        data: {
          id: "dft_output",
          label: "Xuất tệp Word (.docx) & Mã QR Ban hành",
          category: "output",
          timeoutSeconds: 5,
        },
      },
    ],
    edges: [
      { id: "de1", source: "dft_input", target: "dft_rag", animated: true },
      {
        id: "de2",
        source: "dft_rag",
        target: "dft_approval",
        label: "Duyệt bản thảo",
        style: { stroke: "#a855f7" },
        animated: true,
      },
      {
        id: "de3",
        source: "dft_approval",
        target: "dft_output",
        label: "Đã phê duyệt",
        style: { stroke: "#10b981" },
        animated: true,
      },
    ],
  },
  "question-bank": {
    code: "question-bank",
    name: "question-bank-assistant",
    displayName: "Luồng Ngân hàng Câu hỏi & Ma trận Bloom",
    category: "Khảo thí & ĐBCL",
    icon: <HelpCircle className="h-4 w-4" />,
    nodes: [
      {
        id: "qb_input",
        type: "chatInput",
        position: { x: 250, y: 30 },
        data: {
          id: "qb_input",
          label: "Chủ đề học phần & Chuẩn đầu ra (CLO)",
          category: "input",
          timeoutSeconds: 2,
        },
      },
      {
        id: "qb_rag",
        type: "ragKnowledge",
        position: { x: 250, y: 180 },
        data: {
          id: "qb_rag",
          label: "Ma trận 4 mức Bloom (Nhận biết -> VDC)",
          category: "rag",
          description: "Đối chiếu đề cương chi tiết môn học chính thức.",
          timeoutSeconds: 25,
        },
      },
      {
        id: "qb_output",
        type: "chatOutput",
        position: { x: 250, y: 340 },
        data: {
          id: "qb_output",
          label: "Thẻ trắc nghiệm 4 đáp án & Xuất Excel",
          category: "output",
          description: "Kèm lời giải thích chi tiết và trích dẫn giáo trình môn học.",
          timeoutSeconds: 5,
        },
      },
    ],
    edges: [
      { id: "qe1", source: "qb_input", target: "qb_rag", animated: true },
      { id: "qe2", source: "qb_rag", target: "qb_output", animated: true },
    ],
  },
};

export const DAGCanvasPage: React.FC<{ onNavigateToChat?: (code: string) => void }> = ({
  onNavigateToChat,
}) => {
  const [selectedWorkflowKey, setSelectedWorkflowKey] = useState<string>("admissions");
  const [selectedNodeData, setSelectedNodeData] = useState<WorkflowNodeData | null>(null);

  const activeWorkflow = useMemo(
    () => WORKFLOW_REGISTRY[selectedWorkflowKey] || WORKFLOW_REGISTRY.admissions,
    [selectedWorkflowKey]
  );

  return (
    <div className="flex h-[calc(100vh-var(--topbar-height)-2rem)] flex-col gap-3">
      {/* Top Controller Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-surface border border-border bg-card shadow-xs">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-control bg-primary text-primary-foreground">
            <GitBranch className="h-4 w-4" />
          </div>
          <div>
            <h1 className="font-bold text-sm text-foreground flex items-center gap-2">
              Visual DAG Workflow Studio
              <Badge variant="outline" className="font-mono text-[10px]">
                @xyflow/react v12
              </Badge>
            </h1>
            <p className="text-[11px] text-muted-foreground">
              Mô hình hóa quy trình điều phối AI không chu trình (Directed Acyclic Graph)
            </p>
          </div>
        </div>

        {/* Workflow Switcher Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          {Object.values(WORKFLOW_REGISTRY).map((wf) => {
            const isSelected = wf.code === selectedWorkflowKey;
            return (
              <button
                key={wf.code}
                type="button"
                onClick={() => {
                  setSelectedWorkflowKey(wf.code);
                  setSelectedNodeData(null);
                }}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control text-xs font-medium transition-all cursor-pointer border ${
                  isSelected
                    ? "bg-primary text-primary-foreground border-primary shadow-xs"
                    : "bg-muted/50 hover:bg-muted text-muted-foreground hover:text-foreground border-border/80"
                }`}
              >
                {wf.icon}
                <span>{wf.displayName.replace("Luồng ", "")}</span>
              </button>
            );
          })}
        </div>

        {onNavigateToChat && (
          <Button
            size="sm"
            onClick={() => onNavigateToChat(selectedWorkflowKey)}
            className="h-8 text-xs gap-1.5 rounded-control"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>Thử trong Chat Studio</span>
          </Button>
        )}
      </div>

      {/* Main Canvas & Side Inspector Layout */}
      <div className="flex-1 flex gap-3 min-h-0 relative">
        {/* Visual Graph View */}
        <div className="flex-1 rounded-surface border border-border bg-card shadow-xs overflow-hidden relative">
          <DAGCanvas
            key={selectedWorkflowKey}
            initialNodes={activeWorkflow.nodes}
            initialEdges={activeWorkflow.edges}
            workflowName={activeWorkflow.displayName}
            onNodeSelect={(node) => setSelectedNodeData(node)}
          />
        </div>

        {/* Node Inspector Drawer */}
        {selectedNodeData && (
          <div className="w-80 shrink-0 rounded-surface border border-border bg-card p-4 shadow-xs flex flex-col gap-3 overflow-y-auto animate-in slide-in-from-right-4 duration-200 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-1.5">
                <Info className="h-4 w-4 text-primary" />
                <span className="font-bold text-foreground">Chi tiết Node</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedNodeData(null)}
                className="h-6 w-6 p-0 text-muted-foreground hover:text-foreground"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase font-mono">Node ID</span>
              <p className="font-mono font-bold text-foreground text-xs bg-muted/60 p-1.5 rounded-micro">
                {selectedNodeData.id}
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-[10px] text-muted-foreground uppercase">Tên hiển thị</span>
              <p className="font-semibold text-foreground">{selectedNodeData.label}</p>
            </div>

            {selectedNodeData.description && (
              <div className="space-y-1">
                <span className="text-[10px] text-muted-foreground uppercase">Mô tả chức năng</span>
                <p className="text-muted-foreground leading-relaxed">
                  {selectedNodeData.description}
                </p>
              </div>
            )}

            <Separator />

            {/* Execution Policies */}
            <div className="space-y-2">
              <span className="font-semibold text-foreground flex items-center gap-1.5">
                <Sliders className="h-3.5 w-3.5 text-primary" />
                Chính sách thực thi (Execution Policy)
              </span>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded-micro bg-muted/40 border border-border/80">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3 text-warning" />
                    Timeout
                  </span>
                  <p className="font-mono font-bold text-foreground mt-0.5">
                    {selectedNodeData.timeoutSeconds || 30} giây
                  </p>
                </div>

                <div className="p-2 rounded-micro bg-muted/40 border border-border/80">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Layers className="h-3 w-3 text-info" />
                    Max Attempts
                  </span>
                  <p className="font-mono font-bold text-foreground mt-0.5">2 lần</p>
                </div>
              </div>

              {selectedNodeData.configSummary && (
                <div className="space-y-1 pt-1">
                  <span className="text-[10px] text-muted-foreground uppercase">
                    Cấu hình Node (Config Schema)
                  </span>
                  <pre className="p-2 rounded-control bg-muted/90 font-mono text-[11px] text-foreground overflow-x-auto border border-border/80 whitespace-pre-wrap">
                    {selectedNodeData.configSummary}
                  </pre>
                </div>
              )}
            </div>

            <Separator />

            <div className="p-2.5 rounded-control bg-primary/5 border border-primary/20 text-[11px] text-muted-foreground space-y-1">
              <span className="font-semibold text-primary flex items-center gap-1">
                <ShieldAlert className="h-3.5 w-3.5" />
                Chuẩn QNU AI Architecture
              </span>
              <p className="leading-relaxed">
                Node tuân thủ nguyên tắc Pipeline Pattern và Circuit Breaker. Khi một nhánh gặp lỗi
                quá ngưỡng, hệ thống tự động ngắt và kích hoạt Fallback Model.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
