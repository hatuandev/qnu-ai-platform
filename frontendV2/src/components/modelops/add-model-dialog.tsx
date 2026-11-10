import { Cpu, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAddModelMutation } from "@/api/modelops/queries";
import type { Capability, Connection } from "@/api/modelops/types";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { CAPABILITY_LABELS } from "./constants";

export function AddModelDialog({
  open,
  onOpenChange,
  connection,
  prefillModelName,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  connection: Connection;
  prefillModelName?: string;
}) {
  const addModelMutation = useAddModelMutation(connection.id);

  const [modelName, setModelName] = useState("");
  const [capabilities, setCapabilities] = useState<Capability[]>(["chat"]);
  const [contextWindow, setContextWindow] = useState<number | "">("");
  const [maxOutput, setMaxOutput] = useState<number | "">("");
  const [embeddingDimension, setEmbeddingDimension] = useState<number | "">("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setModelName(prefillModelName || "");
      // Auto-detect sensible capabilities based on model name
      const lower = (prefillModelName || "").toLowerCase();
      if (lower.includes("embed") || lower.includes("bge")) {
        setCapabilities(["embedding"]);
        setEmbeddingDimension(1536);
      } else if (lower.includes("rerank")) {
        setCapabilities(["rerank"]);
      } else if (lower.includes("ocr") || lower.includes("mineru")) {
        setCapabilities(["ocr"]);
      } else {
        setCapabilities(["chat"]);
      }
      setContextWindow("");
      setMaxOutput("");
    }
  }, [open, prefillModelName]);

  const toggleCapability = (cap: Capability) => {
    setCapabilities((prev) =>
      prev.includes(cap) ? prev.filter((c) => c !== cap) : [...prev, cap],
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modelName.trim()) {
      toast.error("Vui lòng nhập tên định danh mô hình");
      return;
    }
    if (capabilities.length === 0) {
      toast.error("Vui lòng chọn ít nhất một năng lực cho mô hình");
      return;
    }

    setIsSubmitting(true);
    try {
      const tokenLimits =
        typeof contextWindow === "number" || typeof maxOutput === "number"
          ? {
              context_window_tokens:
                typeof contextWindow === "number" ? contextWindow : null,
              max_output_tokens:
                typeof maxOutput === "number" ? maxOutput : null,
            }
          : undefined;

      await addModelMutation.mutateAsync({
        model_name: modelName.trim(),
        capabilities,
        token_limits: tokenLimits,
        embedding_dimension:
          capabilities.includes("embedding") &&
          typeof embeddingDimension === "number"
            ? embeddingDimension
            : undefined,
      });

      toast.success(`Đã thêm mô hình "${modelName}" thành công`);
      onOpenChange(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Thêm mô hình thất bại";
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Cpu className="size-5 text-primary" />
              <span>Đăng ký mô hình AI mới</span>
            </DialogTitle>
            <DialogDescription>
              Đăng ký mô hình thuộc nhà cung cấp{" "}
              <span className="font-semibold text-foreground">
                {connection.name}
              </span>
              .
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Field>
              <FieldLabel htmlFor="model-name">
                Tên định danh mô hình (Model Name) *
              </FieldLabel>
              <Input
                id="model-name"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="VD: gpt-4o, qwen2.5-coder:32b, text-embedding-3-small..."
                className="font-mono text-xs"
                required
              />
              <FieldDescription>
                Tên chính xác của mô hình khi gửi yêu cầu qua API của nhà cung
                cấp.
              </FieldDescription>
            </Field>

            <Field>
              <FieldLabel>Năng lực xử lý (Capabilities) *</FieldLabel>
              <div className="grid grid-cols-2 gap-2 pt-1">
                {(Object.keys(CAPABILITY_LABELS) as Capability[]).map((cap) => {
                  const meta = CAPABILITY_LABELS[cap];
                  const checked = capabilities.includes(cap);
                  return (
                    <label
                      key={cap}
                      htmlFor={`cap-${cap}`}
                      className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                        checked
                          ? "border-primary/40 bg-primary/5"
                          : "border-border/60 hover:bg-muted/30"
                      }`}
                    >
                      <Checkbox
                        id={`cap-${cap}`}
                        checked={checked}
                        onCheckedChange={() => toggleCapability(cap)}
                        className="mt-0.5"
                      />
                      <div className="min-w-0">
                        <span className="font-semibold block">
                          {meta.label}
                        </span>
                        <span className="text-[11px] text-muted-foreground line-clamp-2">
                          {meta.description}
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>
            </Field>

            <div className="grid grid-cols-2 gap-4">
              <Field>
                <FieldLabel htmlFor="model-context">
                  Ngữ cảnh tối đa (tokens)
                </FieldLabel>
                <Input
                  id="model-context"
                  type="number"
                  min={512}
                  value={contextWindow}
                  onChange={(e) =>
                    setContextWindow(
                      e.target.value ? Number(e.target.value) : "",
                    )
                  }
                  placeholder="VD: 32768, 128000"
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="model-output">
                  Đầu ra tối đa (tokens)
                </FieldLabel>
                <Input
                  id="model-output"
                  type="number"
                  min={128}
                  value={maxOutput}
                  onChange={(e) =>
                    setMaxOutput(e.target.value ? Number(e.target.value) : "")
                  }
                  placeholder="VD: 4096, 8192"
                />
              </Field>
            </div>

            {capabilities.includes("embedding") && (
              <Field>
                <FieldLabel htmlFor="model-dim">
                  Số chiều Vector (Dimension)
                </FieldLabel>
                <Input
                  id="model-dim"
                  type="number"
                  min={128}
                  max={65536}
                  value={embeddingDimension}
                  onChange={(e) =>
                    setEmbeddingDimension(
                      e.target.value ? Number(e.target.value) : "",
                    )
                  }
                  placeholder="VD: 1536 (OpenAI), 1024 (BGE), 768"
                />
                <FieldDescription>
                  Số chiều của vector embedding cho các kho tri thức.
                </FieldDescription>
              </Field>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={isSubmitting}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="submit"
              disabled={
                isSubmitting || !modelName.trim() || capabilities.length === 0
              }
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="size-3.5 animate-spin mr-1.5" />
                  <span>Đang đăng ký...</span>
                </>
              ) : (
                "Đăng ký mô hình"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
