import {
  AlertTriangle,
  Check,
  Clock,
  Code2,
  Save,
  Sliders,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import type React from "react";
import { useEffect, useState } from "react";
import type { WorkflowNodeData } from "../ai/dag-canvas";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Separator } from "../ui/separator";
import { Switch } from "../ui/switch";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

export interface PropertyInspectorProps {
  node: WorkflowNodeData | null;
  onClose: () => void;
  onUpdateNode: (nodeId: string, updatedData: Partial<WorkflowNodeData>) => void;
  onDeleteNode: (nodeId: string) => void;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(node: WorkflowNodeData, key: string): Record<string, unknown> {
  const value = node[key];
  return isRecord(value) ? value : {};
}

export const PropertyInspector: React.FC<PropertyInspectorProps> = ({
  node,
  onClose,
  onUpdateNode,
  onDeleteNode,
}) => {
  const [label, setLabel] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [timeoutSeconds, setTimeoutSeconds] = useState<number>(30);
  const [configSummary, setConfigSummary] = useState<string>("");
  const [configState, setConfigState] = useState<Record<string, unknown>>({});
  const [jsonConfig, setJsonConfig] = useState<string>("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("visual");
  const [isSaved, setIsSaved] = useState<boolean>(false);

  useEffect(() => {
    if (!node) return;
    setLabel(node.label || "");
    setDescription(node.description || "");
    setTimeoutSeconds(node.timeoutSeconds || 30);
    setConfigSummary(node.configSummary || "");

    const currentConfig = readRecord(node, "workflowConfig");
    setConfigState(currentConfig);

    try {
      const parsed = {
        id: node.id,
        type: typeof node.workflowNodeType === "string" ? node.workflowNodeType : "llm.generate",
        display_name: node.label,
        category: node.category,
        config: currentConfig,
        policy: readRecord(node, "workflowPolicy"),
      };
      setJsonConfig(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch {
      setJsonConfig("{}");
    }
  }, [node]);

  if (!node) return null;

  const updateConfigField = (field: string, value: unknown) => {
    setConfigState((previous) => {
      const updated = { ...previous, [field]: value };
      try {
        const parsed = JSON.parse(jsonConfig || "{}");
        parsed.config = updated;
        setJsonConfig(JSON.stringify(parsed, null, 2));
      } catch {
        // preserve jsonConfig
      }
      return updated;
    });
  };

  const handleSaveVisual = () => {
    const workflowPolicy = {
      ...readRecord(node, "workflowPolicy"),
      timeout_seconds: Number(timeoutSeconds) || 30,
    };
    const summary = Object.entries(configState)
      .slice(0, 3)
      .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
      .join(", ");

    onUpdateNode(node.id, {
      label: label.trim(),
      description: description.trim(),
      timeoutSeconds: Number(timeoutSeconds) || 30,
      configSummary: summary || configSummary.trim(),
      workflowConfig: configState,
      workflowPolicy,
    });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleSaveJson = () => {
    try {
      const parsed: unknown = JSON.parse(jsonConfig);
      if (!isRecord(parsed)) {
        throw new Error("Cấu hình JSON phải là một đối tượng.");
      }
      const config = isRecord(parsed.config) ? parsed.config : {};
      const policy = isRecord(parsed.policy) ? parsed.policy : {};
      setJsonError(null);
      setConfigState(config);

      onUpdateNode(node.id, {
        label: typeof parsed.display_name === "string" ? parsed.display_name : label,
        timeoutSeconds:
          typeof policy.timeout_seconds === "number" ? policy.timeout_seconds : timeoutSeconds,
        configSummary: JSON.stringify(config),
        workflowNodeType: typeof parsed.type === "string" ? parsed.type : node.workflowNodeType,
        workflowConfig: config,
        workflowPolicy: policy,
      });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch (err: unknown) {
      setJsonError(err instanceof Error ? err.message : "Định dạng JSON không hợp lệ");
    }
  };

  const nodeType = typeof node.workflowNodeType === "string" ? node.workflowNodeType : "";

  return (
    <aside
      aria-label="Bảng Thuộc Tính Node"
      className="absolute top-14 right-4 z-20 w-88 max-h-[85vh] flex flex-col rounded-surface bg-card/95 backdrop-blur-md border border-border shadow-xl overflow-hidden animate-in fade-in slide-in-from-right-3 duration-200"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted/40">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-control bg-primary/10 text-primary">
            <Sliders className="size-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">Thuộc Tính Node</h3>
            <p className="text-[10px] font-mono text-muted-foreground">{node.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="text-[10px] font-mono uppercase text-primary">
            {node.category}
          </Badge>
          <Button variant="ghost" size="icon" className="size-7" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
      </div>

      {/* Tabs List */}
      <div className="px-4 pt-2 border-b border-border bg-muted/20">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full h-8 grid grid-cols-2 p-0.5">
            <TabsTrigger value="visual" className="text-xs h-7">
              Trực Quan
            </TabsTrigger>
            <TabsTrigger value="json" className="text-xs h-7">
              JSON Schema
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[calc(85vh-160px)]">
        {activeTab === "visual" && (
          <div className="space-y-3.5 text-xs">
            {/* Display Name */}
            <div className="space-y-1">
              <label
                htmlFor="node-display-name"
                className="text-[11px] font-semibold text-foreground"
              >
                Tên hiển thị (Label):
              </label>
              <input
                id="node-display-name"
                type="text"
                value={label}
                onChange={(e) => setLabel(e.target.value)}
                className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            {/* Description */}
            <div className="space-y-1">
              <label
                htmlFor="node-description"
                className="text-[11px] font-semibold text-foreground"
              >
                Mô tả chức năng:
              </label>
              <textarea
                id="node-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
                className="w-full p-2 rounded-control border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary resize-none text-[11px]"
              />
            </div>

            <Separator />

            {/* Dynamic Schema Parameters Section */}
            <div className="space-y-2.5">
              <span className="font-bold text-foreground text-[11px] flex items-center gap-1.5">
                <Sparkles className="size-3 text-primary" />
                <span>Cấu hình tham số thực tế (Parameters):</span>
              </span>

              {/* RAG Knowledge Node */}
              {(node.category === "rag" || nodeType.includes("knowledge")) && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label htmlFor="rag-module-code" className="text-muted-foreground font-medium">
                      Phân hệ (module_code):
                    </label>
                    <input
                      id="rag-module-code"
                      type="text"
                      value={String(configState.module_code || "admissions")}
                      onChange={(e) => updateConfigField("module_code", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label htmlFor="rag-profile" className="text-muted-foreground font-medium">
                        Profile truy xuất:
                      </label>
                      <input
                        id="rag-profile"
                        type="text"
                        value={String(configState.profile || "rag_fast")}
                        onChange={(e) => updateConfigField("profile", e.target.value)}
                        className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                      />
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="rag-top-k" className="text-muted-foreground font-medium">
                        Top K chunks:
                      </label>
                      <input
                        id="rag-top-k"
                        type="number"
                        min={1}
                        max={50}
                        value={Number(configState.retrieval_limit || 10)}
                        onChange={(e) =>
                          updateConfigField("retrieval_limit", Number(e.target.value))
                        }
                        className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                      />
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <label htmlFor="rag-citations" className="text-muted-foreground font-medium">
                      Bắt buộc trích dẫn (Citations):
                    </label>
                    <Switch
                      id="rag-citations"
                      checked={configState.require_citations !== false}
                      onCheckedChange={(checked) => updateConfigField("require_citations", checked)}
                    />
                  </div>
                </div>
              )}

              {/* Tool / API Caller Node */}
              {(node.category === "tool" || nodeType.includes("api_caller")) && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label htmlFor="tool-id-input" className="text-muted-foreground font-medium">
                      Mã công cụ (tool_id):
                    </label>
                    <input
                      id="tool-id-input"
                      type="text"
                      placeholder="uis_admissions_query"
                      value={String(configState.tool_id || configState.tool_name || "")}
                      onChange={(e) => updateConfigField("tool_id", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label htmlFor="tool-method" className="text-muted-foreground font-medium">
                        Phương thức:
                      </label>
                      <select
                        id="tool-method"
                        value={String(configState.http_method || "GET")}
                        onChange={(e) => updateConfigField("http_method", e.target.value)}
                        className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground text-[11px]"
                      >
                        <option value="GET">GET</option>
                        <option value="POST">POST</option>
                        <option value="PUT">PUT</option>
                      </select>
                    </div>
                    <div className="space-y-1">
                      <label htmlFor="tool-timeout" className="text-muted-foreground font-medium">
                        Timeout (giây):
                      </label>
                      <input
                        id="tool-timeout"
                        type="number"
                        min={1}
                        max={60}
                        value={Number(configState.timeout_seconds || 15)}
                        onChange={(e) =>
                          updateConfigField("timeout_seconds", Number(e.target.value))
                        }
                        className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Routing Node */}
              {node.category === "route" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label
                      htmlFor="route-default-node"
                      className="text-muted-foreground font-medium"
                    >
                      Node mặc định (default_node):
                    </label>
                    <input
                      id="route-default-node"
                      type="text"
                      placeholder="knowledge_answer"
                      value={String(configState.default_node || "")}
                      onChange={(e) => updateConfigField("default_node", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                  <span className="text-[10px] text-muted-foreground">
                    Số quy tắc định tuyến:{" "}
                    {Array.isArray(configState.rules) ? configState.rules.length : 0} quy tắc
                  </span>
                </div>
              )}

              {/* Output Chat / Artifact Node */}
              {node.category === "output" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label htmlFor="output-format" className="text-muted-foreground font-medium">
                      Định dạng đầu ra:
                    </label>
                    <select
                      id="output-format"
                      value={String(configState.format || "markdown")}
                      onChange={(e) => updateConfigField("format", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground text-[11px]"
                    >
                      <option value="markdown">Markdown</option>
                      <option value="plain_text">Văn bản thuần (Plain Text)</option>
                      <option value="json">JSON</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <label htmlFor="output-citations" className="text-muted-foreground font-medium">
                      Kèm trích dẫn (Citations):
                    </label>
                    <Switch
                      id="output-citations"
                      checked={configState.include_citations !== false}
                      onCheckedChange={(checked) => updateConfigField("include_citations", checked)}
                    />
                  </div>
                </div>
              )}

              {/* LLM Generate / Drafting Node */}
              {node.category === "llm" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label htmlFor="llm-module-code" className="text-muted-foreground font-medium">
                      Mã phân hệ (module_code):
                    </label>
                    <input
                      id="llm-module-code"
                      type="text"
                      placeholder="drafting"
                      value={String(configState.module_code || "drafting")}
                      onChange={(e) => updateConfigField("module_code", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                  <div className="space-y-1">
                    <label htmlFor="llm-doc-type" className="text-muted-foreground font-medium">
                      Loại văn bản:
                    </label>
                    <input
                      id="llm-doc-type"
                      type="text"
                      placeholder="quyet_dinh"
                      value={String(configState.document_type || "")}
                      onChange={(e) => updateConfigField("document_type", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                </div>
              )}

              {/* Human Approval Node */}
              {node.category === "human" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="space-y-1">
                    <label htmlFor="appr-permission" className="text-muted-foreground font-medium">
                      Quyền duyệt (Permission):
                    </label>
                    <input
                      id="appr-permission"
                      type="text"
                      placeholder="run.resume"
                      value={String(configState.required_permission || "run.resume")}
                      onChange={(e) => updateConfigField("required_permission", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <label htmlFor="appr-separation" className="text-muted-foreground font-medium">
                      Tách biệt nhiệm vụ (Separation of duties):
                    </label>
                    <Switch
                      id="appr-separation"
                      checked={configState.separation_of_duties !== false}
                      onCheckedChange={(checked) =>
                        updateConfigField("separation_of_duties", checked)
                      }
                    />
                  </div>
                </div>
              )}

              {/* Citation Guard Node */}
              {node.category === "guard" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <div className="flex items-center justify-between pt-1">
                    <label
                      htmlFor="guard-require-cite"
                      className="text-muted-foreground font-medium"
                    >
                      Bắt buộc có trích dẫn mới trả lời:
                    </label>
                    <Switch
                      id="guard-require-cite"
                      checked={configState.require_citation_for_answer !== false}
                      onCheckedChange={(checked) =>
                        updateConfigField("require_citation_for_answer", checked)
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <label
                      htmlFor="guard-invalid-route"
                      className="text-muted-foreground font-medium"
                    >
                      Nhánh rẽ khi vi phạm:
                    </label>
                    <input
                      id="guard-invalid-route"
                      type="text"
                      placeholder="ungrounded"
                      value={String(configState.invalid_route || "ungrounded")}
                      onChange={(e) => updateConfigField("invalid_route", e.target.value)}
                      className="w-full h-7 px-2 rounded-control border border-border bg-background text-foreground font-mono text-[11px]"
                    />
                  </div>
                </div>
              )}
            </div>

            <Separator />

            {/* Execution Policy */}
            <div className="space-y-2">
              <span className="font-bold text-foreground text-[11px] flex items-center gap-1.5">
                <Clock className="size-3 text-warning" />
                <span>Chính sách thực thi (Execution Policy):</span>
              </span>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <label htmlFor="node-timeout-sec" className="text-[10px] text-muted-foreground">
                    Timeout (giây):
                  </label>
                  <input
                    id="node-timeout-sec"
                    type="number"
                    value={timeoutSeconds}
                    onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                    min={1}
                    max={86400}
                    className="w-full h-8 px-2 rounded-control border border-border bg-background text-foreground font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] text-muted-foreground">Max Retries:</span>
                  <div className="h-8 px-2 flex items-center rounded-control bg-muted/60 border border-border/80 font-mono text-muted-foreground">
                    2 lần
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2">
              <Button className="w-full h-8 text-xs font-semibold" onClick={handleSaveVisual}>
                {isSaved ? (
                  <>
                    <Check className="size-3 mr-1 text-success" />
                    <span>Đã lưu thành công!</span>
                  </>
                ) : (
                  <>
                    <Save className="size-3 mr-1" />
                    <span>Lưu Cấu Hình Node</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {activeTab === "json" && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1 font-mono">
                <Code2 className="size-3 text-primary" />
                <span>DAG Node JSON Schema</span>
              </span>
            </div>

            <textarea
              value={jsonConfig}
              onChange={(e) => setJsonConfig(e.target.value)}
              rows={12}
              className="w-full p-2 rounded-control border border-border bg-muted/90 text-foreground font-mono text-[10px] focus:outline-none focus:ring-1 focus:ring-primary resize-none leading-relaxed"
            />

            {jsonError && (
              <div className="p-2 rounded-control bg-destructive/10 border border-destructive/30 text-destructive text-[11px] flex items-center gap-1.5">
                <AlertTriangle className="size-3.5 shrink-0" />
                <span>{jsonError}</span>
              </div>
            )}

            <Button className="w-full h-8 text-xs font-semibold" onClick={handleSaveJson}>
              <Save className="size-3 mr-1" />
              <span>Áp Dụng JSON Cấu Hình</span>
            </Button>
          </div>
        )}

        <Separator />

        {/* Delete Node Action */}
        <div className="pt-1">
          <Button
            variant="outline"
            className="w-full h-8 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive border-destructive/30"
            onClick={() => onDeleteNode(node.id)}
          >
            <Trash2 className="size-3 mr-1" />
            <span>Xóa Node Khỏi Canvas</span>
          </Button>
        </div>
      </div>
    </aside>
  );
};
