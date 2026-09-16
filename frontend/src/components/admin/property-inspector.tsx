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
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";

export interface PropertyInspectorProps {
  node: WorkflowNodeData | null;
  onClose: () => void;
  onUpdateNode: (nodeId: string, updatedData: Partial<WorkflowNodeData>) => void;
  onDeleteNode: (nodeId: string) => void;
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

    try {
      const parsed = {
        id: node.id,
        category: node.category,
        config: node.configSummary ? { raw: node.configSummary } : {},
        policy: { timeout_seconds: node.timeoutSeconds || 30, max_attempts: 2 },
      };
      setJsonConfig(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch {
      setJsonConfig("{}");
    }
  }, [node]);

  if (!node) return null;

  const handleSaveVisual = () => {
    onUpdateNode(node.id, {
      label: label.trim(),
      description: description.trim(),
      timeoutSeconds: Number(timeoutSeconds) || 30,
      configSummary: configSummary.trim(),
    });
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleSaveJson = () => {
    try {
      const parsed = JSON.parse(jsonConfig);
      setJsonError(null);
      onUpdateNode(node.id, {
        label: parsed.label || label,
        timeoutSeconds: parsed.policy?.timeout_seconds || timeoutSeconds,
        configSummary: JSON.stringify(parsed.config || {}),
      });
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 2000);
    } catch (err: unknown) {
      setJsonError((err as Error).message || "Định dạng JSON không hợp lệ");
    }
  };

  return (
    <aside
      aria-label="Bảng Thuộc Tính Node"
      className="absolute top-14 right-4 z-20 w-84 max-h-[85vh] flex flex-col rounded-surface bg-card/95 backdrop-blur-md border border-border shadow-xl overflow-hidden animate-in fade-in slide-in-from-right-3 duration-200"
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

            {/* Parameters & Configuration */}
            <div className="space-y-2">
              <span className="font-bold text-foreground text-[11px] flex items-center gap-1.5">
                <Sparkles className="size-3 text-primary" />
                <span>Cấu hình tham số (Parameters):</span>
              </span>

              {node.category === "rag" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Top K chunks:</span>
                    <span className="font-mono font-bold text-foreground">8</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Similarity Score:</span>
                    <span className="font-mono font-bold text-foreground">&ge; 0.65</span>
                  </div>
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-muted-foreground">Fusion:</span>
                    <span className="font-mono font-bold text-primary">RRF k=60</span>
                  </div>
                </div>
              )}

              {node.category === "route" && (
                <div className="space-y-2 p-2.5 rounded-control bg-muted/40 border border-border/80 text-[11px]">
                  <span className="text-muted-foreground font-semibold">
                    Quy tắc rẽ nhánh (Routing Rules):
                  </span>
                  <div className="space-y-1 font-mono text-[10px] text-foreground">
                    <div className="p-1 rounded-micro bg-background border border-border">
                      • intent == "greeting" ➔ greeting_output
                    </div>
                    <div className="p-1 rounded-micro bg-background border border-border">
                      • intent == "query" ➔ knowledge_answer
                    </div>
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label
                  htmlFor="node-config-summary"
                  className="text-[10px] text-muted-foreground uppercase font-semibold"
                >
                  Tóm tắt cấu hình:
                </label>
                <input
                  id="node-config-summary"
                  type="text"
                  value={configSummary}
                  onChange={(e) => setConfigSummary(e.target.value)}
                  className="w-full h-8 px-2.5 rounded-control border border-border bg-background text-foreground font-mono text-[10px] focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
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
