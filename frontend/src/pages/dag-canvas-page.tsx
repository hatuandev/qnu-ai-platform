import type { Edge, Node } from "@xyflow/react";
import {
  BookOpen,
  Check,
  Copy,
  FileText,
  GraduationCap,
  Layers,
  Library,
  MessageSquare,
  Network,
  Play,
  Plus,
  RotateCcw,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import {
  InCanvasTestRunner,
  type NodeExecutionState,
} from "../components/admin/in-canvas-test-runner";
import { NodeCatalogDrawer, type NodeCatalogItem } from "../components/admin/node-catalog-drawer";
import { PropertyInspector } from "../components/admin/property-inspector";
import { DAGCanvas, type WorkflowNodeData } from "../components/ai/dag-canvas";
import { Button } from "../components/ui/button";

interface WorkflowConfig {
  code: string;
  name: string;
  displayName: string;
  category: string;
  icon: React.ReactNode;
  nodes: Node<WorkflowNodeData>[];
  edges: Edge[];
}

const INITIAL_WORKFLOWS: Record<string, WorkflowConfig> = {
  admissions: {
    code: "admissions",
    name: "admissions-assistant",
    displayName: "Luồng Trợ lý Tuyển sinh QNU",
    category: "Đào tạo & Tuyển sinh",
    icon: <GraduationCap className="size-4" />,
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
        position: { x: 60, y: 310 },
        data: {
          id: "greeting_output",
          label: "Lời chào & Gợi ý câu hỏi tuyển sinh",
          category: "output",
          description: "Phản hồi nhanh các câu hỏi xã giao và gợi ý điểm chuẩn, học phí.",
          configSummary: "format: markdown, stream: true",
          timeoutSeconds: 2,
        },
      },
      {
        id: "knowledge_answer",
        type: "ragKnowledge",
        position: { x: 440, y: 310 },
        data: {
          id: "knowledge_answer",
          label: "Tra cứu Đề án tuyển sinh & Điểm chuẩn",
          category: "rag",
          description: "Truy xuất Qdrant vector + Postgres FTS Tiếng Việt với RRF k=60.",
          configSummary: "retrieval_limit: 8, profile: rag_fast",
          timeoutSeconds: 30,
        },
      },
      {
        id: "citation_guard",
        type: "guardrail",
        position: { x: 440, y: 460 },
        data: {
          id: "citation_guard",
          label: "Xác thực nguồn đề án chính quy",
          category: "guard",
          description: "Chống hallucination, kiểm định Điều/Khoản trích dẫn từ ĐH Quy Nhơn.",
          configSummary: "groundedness_threshold: 0.85",
          timeoutSeconds: 5,
        },
      },
      {
        id: "chat_output",
        type: "chatOutput",
        position: { x: 340, y: 600 },
        data: {
          id: "chat_output",
          label: "Kết xuất Markdown kèm bảng chỉ tiêu",
          category: "output",
          description: "Định dạng câu trả lời chuẩn xác kèm trích dẫn văn bản chính quy.",
          configSummary: "format: markdown, include_citations: true",
          timeoutSeconds: 2,
        },
      },
      {
        id: "no_answer_output",
        type: "chatOutput",
        position: { x: 560, y: 600 },
        data: {
          id: "no_answer_output",
          label: "Từ chối / Hotline Tuyển sinh",
          category: "output",
          description: "Kích hoạt No-Answer Policy: Hotline 0256.3846.156 khi không có căn cứ.",
          configSummary: "status: insufficient_context",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "e1", source: "chat_input", target: "condition_route", animated: true },
      { id: "e2", source: "condition_route", target: "greeting_output", label: "Chào hỏi" },
      {
        id: "e3",
        source: "condition_route",
        target: "knowledge_answer",
        label: "Hỏi điểm/chỉ tiêu",
      },
      { id: "e4", source: "knowledge_answer", target: "citation_guard", animated: true },
      { id: "e5", source: "citation_guard", target: "chat_output", label: "Đủ căn cứ" },
      { id: "e6", source: "citation_guard", target: "no_answer_output", label: "Thiếu căn cứ" },
    ],
  },
  regulations: {
    code: "regulations",
    name: "regulations-assistant",
    displayName: "Luồng Trợ lý Quy chế Học vụ",
    category: "Đào tạo tín chỉ",
    icon: <BookOpen className="size-4" />,
    nodes: [
      {
        id: "chat_input",
        type: "chatInput",
        position: { x: 260, y: 30 },
        data: {
          id: "chat_input",
          label: "Thắc mắc quy chế / tín chỉ",
          category: "input",
          description: "Tiếp nhận câu hỏi về đăng ký tín chỉ, xét học bổng, cảnh báo học vụ.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "knowledge_answer",
        type: "ragKnowledge",
        position: { x: 260, y: 170 },
        data: {
          id: "knowledge_answer",
          label: "Đối soát Quy chế 1284/QĐ-ĐHQN",
          category: "rag",
          description: "Clause-based chunking bóc tách chính xác Điều 14, Khoản 2 về học lực.",
          timeoutSeconds: 30,
        },
      },
      {
        id: "citation_guard",
        type: "guardrail",
        position: { x: 260, y: 310 },
        data: {
          id: "citation_guard",
          label: "Kiểm tra trích dẫn số hiệu quyết định",
          category: "guard",
          description: "Đảm bảo dẫn đúng số hiệu văn bản và năm ban hành.",
          timeoutSeconds: 5,
        },
      },
      {
        id: "chat_output",
        type: "chatOutput",
        position: { x: 140, y: 460 },
        data: {
          id: "chat_output",
          label: "Hướng dẫn thực hiện quyền lợi SV",
          category: "output",
          description: "Xuất phản hồi chi tiết và căn cứ Điều/Khoản quy chế.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "no_answer_output",
        type: "chatOutput",
        position: { x: 380, y: 460 },
        data: {
          id: "no_answer_output",
          label: "Điều hướng Phòng Đào tạo (P.108 A1)",
          category: "output",
          description: "Hướng dẫn sinh viên liên hệ Phòng Đào tạo khi vượt thẩm quyền.",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "e1", source: "chat_input", target: "knowledge_answer", animated: true },
      { id: "e2", source: "knowledge_answer", target: "citation_guard", animated: true },
      { id: "e3", source: "citation_guard", target: "chat_output", label: "Có quy chế" },
      { id: "e4", source: "citation_guard", target: "no_answer_output", label: "Chưa quy định" },
    ],
  },
  drafting: {
    code: "drafting",
    name: "drafting-assistant",
    displayName: "Luồng Soạn thảo Văn bản NĐ 30",
    category: "Hành chính & Pháp chế",
    icon: <FileText className="size-4" />,
    nodes: [
      {
        id: "chat_input",
        type: "chatInput",
        position: { x: 260, y: 30 },
        data: {
          id: "chat_input",
          label: "Yêu cầu soạn thảo văn bản",
          category: "input",
          description: "Tiếp nhận nội dung: Quyết định, Tờ trình, Công văn hành chính.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "condition_route",
        type: "conditionRoute",
        position: { x: 260, y: 160 },
        data: {
          id: "condition_route",
          label: "Nhận diện loại văn bản NĐ 30",
          category: "route",
          configSummary: "Quyết định | Công văn | Tờ trình | Kế hoạch",
          timeoutSeconds: 2,
        },
      },
      {
        id: "nd30_formatter",
        type: "toolCall",
        position: { x: 260, y: 310 },
        data: {
          id: "nd30_formatter",
          label: "Áp chuẩn thể thức NĐ 30/2020/NĐ-CP",
          category: "tool",
          description:
            "Căn lề chuẩn (Trên 20mm, Dưới 20mm, Trái 30mm, Phải 15mm), font Times New Roman.",
          timeoutSeconds: 15,
        },
      },
      {
        id: "human_approval",
        type: "humanApproval",
        position: { x: 260, y: 460 },
        data: {
          id: "human_approval",
          label: "Phê duyệt của Trưởng phòng HCTH",
          category: "human",
          description: "Cán bộ chuyên trách rà soát trước khi xuất bản tệp .docx chính thức.",
          timeoutSeconds: 86400,
        },
      },
      {
        id: "final_output",
        type: "chatOutput",
        position: { x: 260, y: 610 },
        data: {
          id: "final_output",
          label: "Xuất bản file Word chuẩn NĐ 30",
          category: "output",
          description: "Cung cấp link tải tệp Word định dạng chuẩn từ MinIO S3.",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "e1", source: "chat_input", target: "condition_route", animated: true },
      { id: "e2", source: "condition_route", target: "nd30_formatter", label: "Đúng thể thức" },
      {
        id: "e3",
        source: "nd30_formatter",
        target: "human_approval",
        label: "Cần kiểm duyệt",
        animated: true,
      },
      {
        id: "e4",
        source: "human_approval",
        target: "final_output",
        label: "Đã duyệt",
        animated: true,
      },
    ],
  },
  question_bank: {
    code: "question_bank",
    name: "question-bank-assistant",
    displayName: "Luồng Ngân hàng Đề thi Bloom",
    category: "Khảo thí & Đảm bảo chất lượng",
    icon: <Layers className="size-4" />,
    nodes: [
      {
        id: "chat_input",
        type: "chatInput",
        position: { x: 260, y: 30 },
        data: {
          id: "chat_input",
          label: "Yêu cầu biên soạn câu hỏi",
          category: "input",
          description: "Tên học phần, mức độ Bloom (1-4) và số lượng câu hỏi.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "condition_route",
        type: "conditionRoute",
        position: { x: 260, y: 160 },
        data: {
          id: "condition_route",
          label: "Kiểm tra mức độ nhận thức",
          category: "route",
          configSummary: "Nhận biết | Thông hiểu | Vận dụng | Vận dụng cao",
          timeoutSeconds: 2,
        },
      },
      {
        id: "bloom_generator",
        type: "llmGenerate",
        position: { x: 260, y: 310 },
        data: {
          id: "bloom_generator",
          label: "Tạo câu hỏi trắc nghiệm Bloom",
          category: "llm",
          description: "Sinh 4 phương án (A,B,C,D) kèm giải thích chi tiết và đáp án.",
          timeoutSeconds: 45,
        },
      },
      {
        id: "clo_matrix",
        type: "toolCall",
        position: { x: 260, y: 460 },
        data: {
          id: "clo_matrix",
          label: "Ánh xạ Ma trận Chuẩn đầu ra (CLO)",
          category: "tool",
          description: "Gắn nhãn CLO tương ứng và xuất dữ liệu ra bảng tính Excel.",
          timeoutSeconds: 15,
        },
      },
      {
        id: "final_output",
        type: "chatOutput",
        position: { x: 260, y: 600 },
        data: {
          id: "final_output",
          label: "Kết xuất file Excel Bloom Matrix",
          category: "output",
          description: "Cung cấp bảng câu hỏi và link tải Excel đã định dạng.",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "e1", source: "chat_input", target: "condition_route", animated: true },
      { id: "e2", source: "condition_route", target: "bloom_generator", animated: true },
      { id: "e3", source: "bloom_generator", target: "clo_matrix", animated: true },
      { id: "e4", source: "clo_matrix", target: "final_output", animated: true },
    ],
  },
  library: {
    code: "library",
    name: "library-assistant",
    displayName: "Luồng Trợ lý Thư viện Số QNU",
    category: "Thư viện & NCKH",
    icon: <Library className="size-4" />,
    nodes: [
      {
        id: "chat_input",
        type: "chatInput",
        position: { x: 260, y: 30 },
        data: {
          id: "chat_input",
          label: "Tra cứu tài liệu học tập",
          category: "input",
          description: "Từ khóa giáo trình, tác giả, bài báo hoặc luận văn tốt nghiệp.",
          timeoutSeconds: 2,
        },
      },
      {
        id: "condition_route",
        type: "conditionRoute",
        position: { x: 260, y: 160 },
        data: {
          id: "condition_route",
          label: "Phân loại nguồn tài liệu",
          category: "route",
          configSummary: "Sách in | Luận văn số | CSDL Quốc tế Scopus",
          timeoutSeconds: 2,
        },
      },
      {
        id: "knowledge_answer",
        type: "ragKnowledge",
        position: { x: 260, y: 310 },
        data: {
          id: "knowledge_answer",
          label: "Truy vấn Kho tài liệu Thư viện QNU",
          category: "rag",
          description: "Tìm kiếm vị trí sách trên kệ, số lượng bản còn mượn.",
          timeoutSeconds: 30,
        },
      },
      {
        id: "final_output",
        type: "chatOutput",
        position: { x: 260, y: 460 },
        data: {
          id: "final_output",
          label: "Thông tin vị trí sách & Hướng dẫn mượn",
          category: "output",
          description: "Mã vạch tài liệu, phòng đọc tương ứng và quy định mượn về nhà.",
          timeoutSeconds: 2,
        },
      },
    ],
    edges: [
      { id: "e1", source: "chat_input", target: "condition_route", animated: true },
      { id: "e2", source: "condition_route", target: "knowledge_answer", animated: true },
      { id: "e3", source: "knowledge_answer", target: "final_output", animated: true },
    ],
  },
};

export interface DAGCanvasPageProps {
  onNavigateToChat?: (assistantCode: string) => void;
}

export const DAGCanvasPage: React.FC<DAGCanvasPageProps> = ({ onNavigateToChat }) => {
  const [selectedWorkflowKey, setSelectedWorkflowKey] = useState<string>("admissions");
  const [workflowState, setWorkflowState] =
    useState<Record<string, WorkflowConfig>>(INITIAL_WORKFLOWS);

  // Dynamic execution states for visual animation
  const [executionStates, setExecutionStates] = useState<Record<string, NodeExecutionState>>({});

  // Active selected node for Property Inspector
  const [selectedNodeData, setSelectedNodeData] = useState<WorkflowNodeData | null>(null);

  // Drawers state
  const [isCatalogOpen, setIsCatalogOpen] = useState<boolean>(false);
  const [isTestRunnerOpen, setIsTestRunnerOpen] = useState<boolean>(false);
  const [isJsonCopied, setIsJsonCopied] = useState<boolean>(false);

  const currentWorkflow = useMemo(() => {
    return workflowState[selectedWorkflowKey] || workflowState.admissions;
  }, [workflowState, selectedWorkflowKey]);

  // Handle workflow selection
  const handleSelectWorkflow = (key: string) => {
    setSelectedWorkflowKey(key);
    setSelectedNodeData(null);
    setExecutionStates({});
  };

  // Reset workflow back to default
  const handleResetWorkflow = () => {
    setWorkflowState((prev) => ({
      ...prev,
      [selectedWorkflowKey]: INITIAL_WORKFLOWS[selectedWorkflowKey],
    }));
    setExecutionStates({});
    setSelectedNodeData(null);
  };

  // Add node from catalog
  const handleAddNodeFromCatalog = (catalogItem: NodeCatalogItem) => {
    const newId = `${catalogItem.category}_${Date.now().toString().slice(-4)}`;
    const yOffset = currentWorkflow.nodes.length * 80 + 50;

    let nodeType = "ragKnowledge";
    if (catalogItem.category === "input") nodeType = "chatInput";
    else if (catalogItem.category === "route") nodeType = "conditionRoute";
    else if (catalogItem.category === "llm") nodeType = "llmGenerate";
    else if (catalogItem.category === "tool") nodeType = "toolCall";
    else if (catalogItem.category === "guard") nodeType = "guardrail";
    else if (catalogItem.category === "human") nodeType = "humanApproval";
    else if (catalogItem.category === "output") nodeType = "chatOutput";

    const newNode: Node<WorkflowNodeData> = {
      id: newId,
      type: nodeType,
      position: { x: 260, y: yOffset },
      data: {
        id: newId,
        label: catalogItem.label,
        category: catalogItem.category,
        description: catalogItem.description,
        configSummary: catalogItem.defaultConfigSummary,
        timeoutSeconds: catalogItem.timeoutSeconds,
      },
    };

    setWorkflowState((prev) => ({
      ...prev,
      [selectedWorkflowKey]: {
        ...currentWorkflow,
        nodes: [...currentWorkflow.nodes, newNode],
      },
    }));

    setSelectedNodeData(newNode.data);
    setIsCatalogOpen(false);
  };

  // Update existing node data
  const handleUpdateNode = (nodeId: string, updatedData: Partial<WorkflowNodeData>) => {
    setWorkflowState((prev) => ({
      ...prev,
      [selectedWorkflowKey]: {
        ...currentWorkflow,
        nodes: currentWorkflow.nodes.map((n) => {
          if (n.id === nodeId) {
            return {
              ...n,
              data: {
                ...n.data,
                ...updatedData,
              },
            };
          }
          return n;
        }),
      },
    }));

    if (selectedNodeData?.id === nodeId) {
      setSelectedNodeData((prev) => (prev ? { ...prev, ...updatedData } : null));
    }
  };

  // Delete node from workflow
  const handleDeleteNode = (nodeId: string) => {
    setWorkflowState((prev) => ({
      ...prev,
      [selectedWorkflowKey]: {
        ...currentWorkflow,
        nodes: currentWorkflow.nodes.filter((n) => n.id !== nodeId),
        edges: currentWorkflow.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      },
    }));
    setSelectedNodeData(null);
  };

  // Export DAG JSON
  const handleExportJson = () => {
    const dagSpec = {
      workflow_id: currentWorkflow.name,
      display_name: currentWorkflow.displayName,
      nodes: currentWorkflow.nodes.map((n) => ({
        id: n.id,
        type: n.type,
        data: n.data,
      })),
      edges: currentWorkflow.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };

    const str = JSON.stringify(dagSpec, null, 2);
    if (navigator.clipboard) {
      navigator.clipboard.writeText(str);
      setIsJsonCopied(true);
      setTimeout(() => setIsJsonCopied(false), 2000);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col -m-6 overflow-hidden bg-background">
      {/* Top Action Toolbar */}
      <div className="h-14 px-5 border-b border-border bg-card/90 backdrop-blur-md flex items-center justify-between shrink-0 z-10">
        {/* Left: Title & Workflow Selector */}
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Network className="size-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-foreground flex items-center gap-2">
              <span>DAG Studio</span>
              <span className="text-muted-foreground font-normal">•</span>
              <span className="text-xs text-primary font-medium">
                {currentWorkflow.displayName}
              </span>
            </h1>
            <p className="text-[10px] text-muted-foreground line-clamp-1">
              {currentWorkflow.category} — {currentWorkflow.nodes.length} nodes,{" "}
              {currentWorkflow.edges.length} connections
            </p>
          </div>

          {/* Workflow Selector Buttons */}
          <div className="hidden lg:flex items-center gap-1 ml-4 pl-4 border-l border-border">
            {Object.values(workflowState).map((wf) => (
              <button
                type="button"
                key={wf.code}
                onClick={() => handleSelectWorkflow(wf.code)}
                className={`text-xs px-2.5 py-1 rounded-control font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
                  selectedWorkflowKey === wf.code
                    ? "bg-primary text-primary-foreground shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                {wf.icon}
                <span>{wf.displayName.replace("Luồng ", "")}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Right: Actions (Add Node, Run Test, Export, Chat) */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8 text-xs font-semibold"
            onClick={() => setIsCatalogOpen((prev) => !prev)}
          >
            <Plus className="size-3.5 mr-1 text-primary" />
            <span>Thêm Node</span>
          </Button>

          <Button
            size="sm"
            className="h-8 text-xs font-semibold shadow-xs"
            onClick={() => setIsTestRunnerOpen(true)}
          >
            <Play className="size-3.5 mr-1 fill-primary-foreground" />
            <span>Chạy Thử Luồng</span>
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground hover:text-foreground"
            onClick={handleExportJson}
            title="Sao chép JSON đặc tả"
          >
            {isJsonCopied ? (
              <Check className="size-3.5 text-success" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground hover:text-foreground"
            onClick={handleResetWorkflow}
            title="Khôi phục sơ đồ mặc định"
          >
            <RotateCcw className="size-3.5" />
          </Button>

          {onNavigateToChat && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 text-xs ml-2 hidden sm:flex"
              onClick={() => onNavigateToChat(currentWorkflow.code)}
            >
              <MessageSquare className="size-3.5 mr-1 text-teal-600" />
              <span>Mở Studio Chat</span>
            </Button>
          )}
        </div>
      </div>

      {/* Main Interactive Canvas Area */}
      <div className="flex-1 relative overflow-hidden">
        <DAGCanvas
          initialNodes={currentWorkflow.nodes}
          initialEdges={currentWorkflow.edges}
          executionStates={executionStates}
          onNodeSelect={(node) => setSelectedNodeData(node)}
          workflowName={currentWorkflow.displayName}
          className="w-full h-full"
        />

        {/* Node Catalog Drawer (Left) */}
        <NodeCatalogDrawer
          isOpen={isCatalogOpen}
          onClose={() => setIsCatalogOpen(false)}
          onSelectNodeToAdd={handleAddNodeFromCatalog}
        />

        {/* Property Inspector (Right) */}
        <PropertyInspector
          node={selectedNodeData}
          onClose={() => setSelectedNodeData(null)}
          onUpdateNode={handleUpdateNode}
          onDeleteNode={handleDeleteNode}
        />

        {/* In-Canvas Test Runner (Bottom Right) */}
        <InCanvasTestRunner
          workflowId={currentWorkflow.name}
          workflowName={currentWorkflow.displayName}
          isOpen={isTestRunnerOpen}
          onClose={() => setIsTestRunnerOpen(false)}
          onUpdateExecutionState={(states) =>
            setExecutionStates((prev) => ({ ...prev, ...states }))
          }
          onResetCanvasStates={() => setExecutionStates({})}
        />
      </div>
    </div>
  );
};
