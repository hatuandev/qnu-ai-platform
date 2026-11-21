import { Check, Loader2, RotateCcw, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  type PersonaCraftResponse,
  useCraftPersonaMutation,
} from "@/api/assistants";
import { ApiProblemError } from "@/api/client";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Badge } from "@/components/ui/badge";
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
import { Textarea } from "@/components/ui/textarea";

export type AssistantPersonaCraftDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  providerId?: string | null;
  currentName?: string;
  onApply: (crafted: {
    name?: string;
    description?: string;
    persona?: string;
    suggestedPrompts?: string[];
  }) => void;
};

const TOPIC_PRESETS = [
  "Tư vấn tuyển sinh ĐH Quy Nhơn 2026",
  "Hỗ trợ học vụ, khảo thí & đăng ký tín chỉ",
  "Cố vấn học tập & Kế hoạch đào tạo sinh viên",
  "Tư vấn hướng nghiệp, việc làm & doanh nghiệp",
];

export function AssistantPersonaCraftDialog({
  open,
  onOpenChange,
  workspaceId,
  providerId,
  currentName,
  onApply,
}: AssistantPersonaCraftDialogProps) {
  const [topic, setTopic] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [tone, setTone] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [result, setResult] = useState<PersonaCraftResponse | null>(null);

  // Selection states for applying to the form
  const [applyName, setApplyName] = useState(true);
  const [applyDescription, setApplyDescription] = useState(true);
  const [applyPersona, setApplyPersona] = useState(true);
  const [applyPrompts, setApplyPrompts] = useState(true);

  const craftMutation = useCraftPersonaMutation(workspaceId);

  useEffect(() => {
    if (open) {
      setError(null);
      if (!result) {
        if (currentName && !topic) {
          setTopic(currentName);
        }
      }
    }
  }, [open, currentName, result, topic]);

  const handleCraft = async () => {
    if (!topic.trim()) {
      setError("Vui lòng nhập chủ đề hoặc mục đích của trợ lý.");
      return;
    }
    setError(null);

    try {
      const response = await craftMutation.mutateAsync({
        topic: topic.trim(),
        name: currentName?.trim() || null,
        target_audience: targetAudience.trim() || null,
        tone: tone.trim() || null,
        provider_id: providerId || null,
      });
      setResult(response);
      setApplyName(!currentName || currentName === "Trợ lý mới" || currentName.trim() === "");
      setApplyDescription(true);
      setApplyPersona(true);
      setApplyPrompts(true);
    } catch (err) {
      if (err instanceof ApiProblemError) {
        setError(err.problem?.detail || err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Không thể tạo Persona từ AI. Vui lòng thử lại.");
      }
    }
  };

  const handleApply = () => {
    if (!result) return;

    onApply({
      ...(applyName ? { name: result.name } : {}),
      ...(applyDescription ? { description: result.description } : {}),
      ...(applyPersona ? { persona: result.persona } : {}),
      ...(applyPrompts && result.suggested_prompts?.length
        ? { suggestedPrompts: result.suggested_prompts }
        : {}),
    });

    toast.success("Đã áp dụng cấu hình và Persona từ AI!");
    onOpenChange(false);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col p-0 overflow-hidden">
        <DialogHeader className="p-5 pb-3 border-b border-border/50">
          <div className="flex items-center gap-2">
            <div className="size-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Sparkles className="size-4" />
            </div>
            <div>
              <DialogTitle className="text-base font-semibold">
                Soạn cấu hình Trợ lý bằng AI
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground mt-0.5">
                Nhập chủ đề hoặc mục đích hoạt động. AI sẽ tự động định hình trọn bộ Tên, Mô tả, Persona chuẩn mực và Câu hỏi gợi ý.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-xs">
          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-destructive text-xs leading-relaxed">
              {error}
            </div>
          )}

          {!result ? (
            /* Input Step */
            <div className="space-y-4">
              <Field>
                <FieldLabel required className="text-xs font-medium">
                  Chủ đề / Mục đích chính của trợ lý
                </FieldLabel>
                <Textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="VD: Tư vấn tuyển sinh đại học chính quy năm 2026 của Trường Đại học Quy Nhơn, giải đáp phương thức xét tuyển, điểm chuẩn..."
                  rows={3}
                  className="resize-none bg-background text-xs leading-relaxed"
                  disabled={craftMutation.isPending}
                  autoFocus
                />
                <FieldDescription>
                  Ghi rõ lĩnh vực, phạm vi giải đáp và dịch vụ nhà trường cần hỗ trợ.
                </FieldDescription>
              </Field>

              {/* Topic Preset Chips */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-medium text-muted-foreground">
                  Chủ đề gợi ý nhanh:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {TOPIC_PRESETS.map((preset) => (
                    <Badge
                      key={preset}
                      variant="outline"
                      className="cursor-pointer hover:bg-accent hover:text-accent-foreground text-[11px] py-1 px-2.5 font-normal transition-colors"
                      onClick={() => setTopic(preset)}
                    >
                      + {preset}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Optional Customizations */}
              <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-border/40">
                <Field>
                  <FieldLabel className="text-xs font-medium">
                    Đối tượng phục vụ (Tùy chọn)
                  </FieldLabel>
                  <Input
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder="VD: Thí sinh THPT, phụ huynh, sinh viên..."
                    className="h-8 bg-background text-xs"
                    disabled={craftMutation.isPending}
                  />
                </Field>

                <Field>
                  <FieldLabel className="text-xs font-medium">
                    Văn phong mong muốn (Tùy chọn)
                  </FieldLabel>
                  <Input
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    placeholder="VD: Thân thiện, chu đáo, chuẩn mực sư phạm..."
                    className="h-8 bg-background text-xs"
                    disabled={craftMutation.isPending}
                  />
                </Field>
              </div>
            </div>
          ) : (
            /* Result Preview Step */
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-border/40">
                <div className="flex items-center gap-2">
                  <Badge variant="default" className="gap-1 text-[11px] bg-primary/90">
                    <Check className="size-3" /> AI đã soạn thảo hoàn tất
                  </Badge>
                  <span className="text-[11px] text-muted-foreground">
                    Chọn các thông tin bạn muốn áp dụng vào Trợ lý:
                  </span>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs gap-1 text-muted-foreground hover:text-foreground"
                  onClick={handleReset}
                >
                  <RotateCcw className="size-3" /> Soạn lại
                </Button>
              </div>

              {/* Preview Cards */}
              <div className="space-y-3">
                {/* Name */}
                <div className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
                  <Checkbox
                    id="apply-name"
                    checked={applyName}
                    onCheckedChange={(c) => setApplyName(Boolean(c))}
                    className="mt-0.5"
                  />
                  <div className="flex-1 space-y-1">
                    <label
                      htmlFor="apply-name"
                      className="text-xs font-semibold cursor-pointer select-none"
                    >
                      Tên gợi ý
                    </label>
                    <p className="text-xs text-foreground font-medium">
                      {result.name}
                    </p>
                  </div>
                </div>

                {/* Description */}
                <div className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
                  <Checkbox
                    id="apply-description"
                    checked={applyDescription}
                    onCheckedChange={(c) => setApplyDescription(Boolean(c))}
                    className="mt-0.5"
                  />
                  <div className="flex-1 space-y-1">
                    <label
                      htmlFor="apply-description"
                      className="text-xs font-semibold cursor-pointer select-none"
                    >
                      Mô tả hoạt động
                    </label>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {result.description}
                    </p>
                  </div>
                </div>

                {/* Persona */}
                <div className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
                  <Checkbox
                    id="apply-persona"
                    checked={applyPersona}
                    onCheckedChange={(c) => setApplyPersona(Boolean(c))}
                    className="mt-0.5"
                  />
                  <div className="flex-1 space-y-1">
                    <label
                      htmlFor="apply-persona"
                      className="text-xs font-semibold cursor-pointer select-none"
                    >
                      Chỉ dẫn Persona (Định danh, Xưng hô & Quy tắc an toàn)
                    </label>
                    <div className="max-h-36 overflow-y-auto rounded border border-border/40 bg-background/80 p-2 text-[11px] leading-relaxed whitespace-pre-line text-foreground/90 font-mono">
                      {result.persona}
                    </div>
                  </div>
                </div>

                {/* Suggested Prompts */}
                {result.suggested_prompts?.length > 0 && (
                  <div className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/20 p-3">
                    <Checkbox
                      id="apply-prompts"
                      checked={applyPrompts}
                      onCheckedChange={(c) => setApplyPrompts(Boolean(c))}
                      className="mt-0.5"
                    />
                    <div className="flex-1 space-y-1.5">
                      <label
                        htmlFor="apply-prompts"
                        className="text-xs font-semibold cursor-pointer select-none"
                      >
                        Câu hỏi gợi ý mở đầu ({result.suggested_prompts.length} câu)
                      </label>
                      <div className="grid gap-1.5 sm:grid-cols-2">
                        {result.suggested_prompts.map((prompt, idx) => (
                          <div
                            key={idx}
                            className="rounded border border-border/40 bg-background/80 px-2 py-1.5 text-[11px] text-muted-foreground"
                          >
                            &ldquo;{prompt}&rdquo;
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="p-4 border-t border-border/50 bg-muted/10 gap-2">
          {!result ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onOpenChange(false)}
                disabled={craftMutation.isPending}
              >
                Hủy bỏ
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleCraft}
                disabled={craftMutation.isPending || !topic.trim()}
                className="gap-1.5 min-w-[130px]"
              >
                {craftMutation.isPending ? (
                  <>
                    <Loader2 className="size-3.5 animate-spin" />
                    Đang soạn thảo...
                  </>
                ) : (
                  <>
                    <Sparkles className="size-3.5" />
                    Soạn bằng AI
                  </>
                )}
              </Button>
            </>
          ) : (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleReset}
              >
                Quay lại sửa chủ đề
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleApply}
                disabled={!applyName && !applyDescription && !applyPersona && !applyPrompts}
                className="gap-1.5"
              >
                <Check className="size-3.5" />
                Áp dụng vào Trợ lý
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
