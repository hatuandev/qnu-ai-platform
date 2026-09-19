import { useQuery } from "@tanstack/react-query";
import {
  Bot,
  GitBranch,
  Layers,
  MessageSquare,
  Plus,
  Search,
  Send,
  ShieldCheck,
  UserCheck,
  Wrench,
  X,
} from "lucide-react";
import type React from "react";
import { useMemo, useState } from "react";
import { systemApi } from "../../services/system-api";
import type { NodeManifest } from "../../types/common";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";

export interface NodeCatalogItem {
  type: string;
  category: "input" | "route" | "rag" | "llm" | "tool" | "guard" | "human" | "output";
  label: string;
  description: string;
  defaultConfigSummary: string;
  defaultConfig?: Record<string, unknown>;
  timeoutSeconds: number;
  status?: string;
  version?: string;
  manifest?: NodeManifest;
}

function toCatalogCategory(cat: string): NodeCatalogItem["category"] {
  const normalized = cat.toLowerCase();
  if (normalized === "input") return "input";
  if (normalized === "route" || normalized === "router") return "route";
  if (normalized === "rag" || normalized === "knowledge") return "rag";
  if (normalized === "llm" || normalized === "drafting") return "llm";
  if (normalized === "tool" || normalized === "export") return "tool";
  if (normalized === "guard") return "guard";
  if (normalized === "human") return "human";
  if (normalized === "output") return "output";
  return "llm";
}

function summarizeConfigSchema(configSchema: Record<string, unknown> | undefined): string {
  if (!configSchema || typeof configSchema !== "object") return "Mặc định chuẩn";
  const props = configSchema.properties as Record<string, unknown> | undefined;
  if (!props || typeof props !== "object") return "Mặc định chuẩn";
  const keys = Object.keys(props).slice(0, 3);
  return keys.length > 0 ? keys.join(", ") : "Mặc định chuẩn";
}

function extractDefaultConfig(
  configSchema: Record<string, unknown> | undefined
): Record<string, unknown> {
  if (!configSchema || typeof configSchema !== "object") return {};
  const props = configSchema.properties as Record<string, Record<string, unknown>> | undefined;
  if (!props || typeof props !== "object") return {};
  const defaults: Record<string, unknown> = {};
  for (const [key, propSpec] of Object.entries(props)) {
    if (propSpec && typeof propSpec === "object" && "default" in propSpec) {
      defaults[key] = propSpec.default;
    }
  }
  return defaults;
}

export const CATALOG_NODE_ITEMS: NodeCatalogItem[] = [
  {
    type: "input.chat",
    category: "input",
    label: "Đầu Vào Trò Chuyện (Chat Input)",
    description:
      "Tiếp nhận và tiền xử lý câu hỏi từ người dùng (loại bỏ ký tự đặc biệt, trim, kiểm tra độ dài).",
    defaultConfigSummary: "trim: true, max_length: 10000",
    defaultConfig: { trim: true, max_length: 10000 },
    timeoutSeconds: 2,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "condition.route",
    category: "route",
    label: "Rẽ Nhánh Điều Kiện (Intent Route)",
    description:
      "Phân loại ý định hội thoại (intent matching / regex keyword) để chuyển tiếp tới nhánh RAG, Tool hoặc Chào hỏi.",
    defaultConfigSummary: "rules: greeting -> greeting_output",
    defaultConfig: {
      rules: [
        { id: "greeting_rule", match: { intent: "xin chào|hello|chào" }, to: "greeting_output" },
      ],
      default_node: "knowledge_answer",
    },
    timeoutSeconds: 5,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "core.knowledge.answer",
    category: "rag",
    label: "Truy Xuất Tri Thức (Hybrid RAG)",
    description:
      "Truy vấn Qdrant Dense Vector 1024D kết hợp PostgreSQL FTS Lexical Search và thuật toán RRF k=60.",
    defaultConfigSummary: "module_code: admissions, profile: rag_fast",
    defaultConfig: {
      module_code: "admissions",
      profile: "rag_fast",
      require_citations: true,
      retrieval_limit: 10,
    },
    timeoutSeconds: 30,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "core.drafting.compose",
    category: "llm",
    label: "Soạn Thảo Văn Bản LLM (Drafting)",
    description:
      "Tổng hợp dữ liệu và soạn thảo văn bản hành chính theo Nghị định 30/2020/NĐ-CP hoặc ngân hàng câu hỏi.",
    defaultConfigSummary: "module_code: drafting, document_type: quyet_dinh",
    defaultConfig: {
      module_code: "drafting",
      document_type: "quyet_dinh",
    },
    timeoutSeconds: 45,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "tool.api_caller",
    category: "tool",
    label: "Gọi Công Cụ Ngoại Vi (API Caller)",
    description:
      "Truy vấn dữ liệu thời gian thực từ Cổng UIS Đào tạo, Trích xuất biểu mẫu Word NĐ 30, Excel Bloom.",
    defaultConfigSummary: "tool_id: uis_admissions_query, method: GET",
    defaultConfig: {
      tool_id: "uis_admissions_query",
      http_method: "GET",
      timeout_seconds: 15,
    },
    timeoutSeconds: 15,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "guard.citation_policy",
    category: "guard",
    label: "Kiểm Định Trích Dẫn (Citation Guard)",
    description:
      "Đối soát câu trả lời với tài liệu gốc của ĐH Quy Nhơn, chống bịa đặt (Anti-Hallucination) và No-Answer Policy.",
    defaultConfigSummary: "require_citation_for_answer: true",
    defaultConfig: {
      require_citation_for_answer: true,
      invalid_route: "ungrounded",
    },
    timeoutSeconds: 10,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "human.approval",
    category: "human",
    label: "Phê Duyệt Nhân Sự (Human Checkpoint)",
    description:
      "Điểm dừng chờ cán bộ chuyên trách duyệt trước khi xuất văn bản chính thức hoặc cấp phát tài liệu mật.",
    defaultConfigSummary: "required_permission: run.resume, separation: true",
    defaultConfig: {
      required_permission: "run.resume",
      separation_of_duties: true,
      wait_timeout_seconds: 86400,
    },
    timeoutSeconds: 86400,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "artifact.export",
    category: "tool",
    label: "Kết Xuất Tệp Tài Liệu (Artifact Export)",
    description:
      "Đóng gói và kết xuất văn bản kết quả thành các định dạng tệp tải về như DOCX, PDF, XLSX.",
    defaultConfigSummary: "format: docx, filename_template: qnu-{run_id}.docx",
    defaultConfig: {
      format: "docx",
      filename_template: "qnu-van-ban-{run_id}.docx",
    },
    timeoutSeconds: 30,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "output.chat",
    category: "output",
    label: "Đầu Ra Trò Chuyện (Chat Output)",
    description:
      "Định dạng câu trả lời chuẩn Markdown, gắn thẻ bảng biểu, checklist và trích dẫn Điều/Khoản gốc.",
    defaultConfigSummary: "format: markdown, include_citations: true",
    defaultConfig: {
      format: "markdown",
      include_citations: true,
    },
    timeoutSeconds: 5,
    status: "active",
    version: "1.0.0",
  },
  {
    type: "output.no_answer",
    category: "output",
    label: "Phản Hồi Từ Chối (No Answer)",
    description:
      "Thông báo chính sách No-Answer khi thiếu căn cứ tài liệu và điều hướng tới hotline/phòng ban phụ trách.",
    defaultConfigSummary: "status: insufficient_context",
    defaultConfig: {
      status: "insufficient_context",
      message: "Thông tin này hiện chưa có trong văn bản chính thức của Trường Đại học Quy Nhơn.",
    },
    timeoutSeconds: 5,
    status: "active",
    version: "1.0.0",
  },
];

export interface NodeCatalogDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectNodeToAdd: (nodeItem: NodeCatalogItem) => void;
}

export const NodeCatalogDrawer: React.FC<NodeCatalogDrawerProps> = ({
  isOpen,
  onClose,
  onSelectNodeToAdd,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  const catalogQuery = useQuery({
    queryKey: ["node-catalog-manifests"],
    queryFn: () => systemApi.getNodeCatalog(),
    staleTime: 5 * 60 * 1000,
  });

  const allItems = useMemo<NodeCatalogItem[]>(() => {
    if (catalogQuery.data && catalogQuery.data.length > 0) {
      return catalogQuery.data.map((m: NodeManifest) => ({
        type: m.type,
        category: toCatalogCategory(m.category),
        label: m.display_name || m.type,
        description: m.description || "",
        defaultConfigSummary: summarizeConfigSchema(m.config_schema),
        defaultConfig: extractDefaultConfig(m.config_schema),
        timeoutSeconds: 30,
        status: m.status,
        version: m.version,
        manifest: m,
      }));
    }
    return CATALOG_NODE_ITEMS;
  }, [catalogQuery.data]);

  const filteredItems = useMemo(() => {
    return allItems.filter((item) => {
      const matchQuery =
        item.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.type.toLowerCase().includes(searchQuery.toLowerCase());
      const matchCat = selectedCategory === "all" || item.category === selectedCategory;
      return matchQuery && matchCat;
    });
  }, [allItems, searchQuery, selectedCategory]);

  if (!isOpen) return null;

  return (
    <aside
      aria-label="Thư Viện Nodes"
      className="absolute top-14 left-4 z-20 w-80 max-h-[80vh] flex flex-col rounded-surface bg-card/95 backdrop-blur-md border border-border shadow-xl overflow-hidden animate-in fade-in slide-in-from-left-3 duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Layers className="size-3.5" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h3 className="text-xs font-bold text-foreground">Thư Viện Nodes (Catalog)</h3>
              <Badge variant="outline" className="text-[9px] px-1 py-0">
                {allItems.length} nodes
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground">Kéo thả hoặc thêm Node vào đồ thị</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
          <X className="size-4" />
        </Button>
      </div>

      {/* Search & Filter */}
      <div className="p-3 border-b border-border space-y-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 size-3.5 text-muted-foreground" />
          <input
            type="text"
            placeholder="Tìm kiếm node..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-xs rounded-control border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap gap-1">
          {["all", "input", "route", "rag", "llm", "tool", "guard", "human", "output"].map(
            (cat) => (
              <button
                type="button"
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`text-[10px] px-2 py-0.5 rounded-micro border transition-all cursor-pointer ${
                  selectedCategory === cat
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted/60 text-muted-foreground border-border hover:bg-muted"
                }`}
              >
                {cat === "all" ? "Tất cả" : cat.toUpperCase()}
              </button>
            )
          )}
        </div>
      </div>

      {/* Nodes List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 max-h-[calc(80vh-140px)]">
        {filteredItems.map((item) => (
          <div
            key={item.type}
            data-testid={`catalog-item-${item.type}`}
            className="p-2.5 rounded-control border border-border bg-card hover:border-primary/50 transition-all space-y-1.5 group"
          >
            <div className="flex items-center justify-between">
              <span className="font-semibold text-xs text-foreground group-hover:text-primary transition-colors flex items-center gap-1.5">
                {item.category === "input" && <MessageSquare className="size-3 text-teal-500" />}
                {item.category === "route" && <GitBranch className="size-3 text-amber-500" />}
                {item.category === "rag" && <Search className="size-3 text-blue-500" />}
                {item.category === "llm" && <Bot className="size-3 text-purple-500" />}
                {item.category === "tool" && <Wrench className="size-3 text-cyan-500" />}
                {item.category === "guard" && <ShieldCheck className="size-3 text-indigo-500" />}
                {item.category === "human" && <UserCheck className="size-3 text-orange-500" />}
                {item.category === "output" && <Send className="size-3 text-emerald-500" />}
                <span>{item.label}</span>
              </span>
              <div className="flex items-center gap-1">
                {item.status === "active" && (
                  <Badge variant="success" className="text-[8px] px-1 py-0">
                    Active
                  </Badge>
                )}
                <Badge variant="outline" className="text-[9px] font-mono">
                  {item.type}
                </Badge>
              </div>
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed line-clamp-2">
              {item.description}
            </p>

            <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[10px] text-muted-foreground">
              <span>Timeout: {item.timeoutSeconds}s</span>
              <Button
                size="sm"
                variant="outline"
                className="h-6 text-[10px] px-2"
                onClick={() => onSelectNodeToAdd(item)}
              >
                <Plus className="size-3 mr-1" />
                <span>Thêm Node</span>
              </Button>
            </div>
          </div>
        ))}

        {filteredItems.length === 0 && (
          <div className="py-6 text-center text-xs text-muted-foreground">
            Không tìm thấy Node nào khớp với từ khóa.
          </div>
        )}
      </div>
    </aside>
  );
};
