import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ExternalLink, ShieldCheck, Sparkles } from "lucide-react";

interface AssistantGuardrailsSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  assistantCode: string;
  onNavigate: (path: string) => void;
}

export function AssistantGuardrailsSection({
  form,
  onChange,
  assistantCode,
  onNavigate,
}: AssistantGuardrailsSectionProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldCheck className="size-4 text-primary" />
          <CardTitle className="text-sm font-bold">Chốt An Toàn Guardrails & Đánh Giá</CardTitle>
        </div>
        <CardDescription className="text-xs">
          Chính sách bảo vệ an ninh và chuẩn mực chống bịa đặt (Anti-Hallucination).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2.5">
          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Ngăn Chặn Prompt Injection</p>
              <p className="text-xs text-muted-foreground">Khử lệnh can thiệp độc hại</p>
            </div>
            <Switch
              checked={form.block_prompt_injection}
              onCheckedChange={(val) => onChange({ ...form, block_prompt_injection: val })}
              aria-label="Ngăn chặn Prompt Injection"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Che Dữ Liệu Cá Nhân (PII)</p>
              <p className="text-xs text-muted-foreground">Tự động ẩn CCCD, SĐT, Email</p>
            </div>
            <Switch
              checked={form.mask_pii}
              onCheckedChange={(val) => onChange({ ...form, mask_pii: val })}
              aria-label="Che giấu dữ liệu cá nhân PII"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Chống Bịa Đặt (Groundedness)</p>
              <p className="text-xs text-muted-foreground">Chỉ trả lời khi có căn cứ RAG</p>
            </div>
            <Switch
              checked={form.require_grounded_answer}
              onCheckedChange={(val) => onChange({ ...form, require_grounded_answer: val })}
              aria-label="Chống bịa đặt Groundedness"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Bảo Vệ System Prompt</p>
              <p className="text-xs text-muted-foreground">Chống rò rỉ chỉ thị nội bộ</p>
            </div>
            <Switch
              checked={form.protect_system_prompt}
              onCheckedChange={(val) => onChange({ ...form, protect_system_prompt: val })}
              aria-label="Bảo vệ System Prompt"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Phê Duyệt Thủ Công (HITL)</p>
              <p className="text-xs text-muted-foreground">Cán bộ duyệt tác vụ nhạy cảm</p>
            </div>
            <Switch
              checked={form.human_approval_required}
              onCheckedChange={(val) => onChange({ ...form, human_approval_required: val })}
              aria-label="Phê duyệt thủ công Human-in-the-loop"
            />
          </div>

          <div className="flex items-center justify-between rounded-md border p-2.5 text-xs">
            <div>
              <p className="font-semibold text-foreground">Bắt Buộc Trích Dẫn Nguồn</p>
              <p className="text-xs text-muted-foreground">Kèm Điều, Khoản, Tên Văn Bản</p>
            </div>
            <Switch
              checked={form.require_citations}
              onCheckedChange={(val) => onChange({ ...form, require_citations: val })}
              aria-label="Bắt buộc trích dẫn nguồn"
            />
          </div>
        </div>

        <Field htmlFor="detail-no-answer" label="Thông Điệp Từ Chối (No-Answer Policy)">
          <Textarea
            id="detail-no-answer"
            rows={3}
            className="text-xs"
            value={form.no_answer_message}
            onChange={(e) => onChange({ ...form, no_answer_message: e.target.value })}
          />
        </Field>

        {/* TM-08 Quality Evaluation Panel */}
        <div className="rounded-md border border-primary/20 bg-primary/5 p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <Sparkles className="size-3.5 text-primary" />
              Chuẩn Kiểm Định Ragas TM-08
            </span>
            <Badge variant="success" className="text-xs">
              Đạt Chuẩn
            </Badge>
          </div>

          <div className="grid grid-cols-3 gap-1.5 text-center text-xs">
            <div className="rounded bg-card p-2 border border-border">
              <span className="text-muted-foreground block text-xs">Faithfulness</span>
              <span className="font-bold text-success font-mono">≥ 0.90</span>
            </div>
            <div className="rounded bg-card p-2 border border-border">
              <span className="text-muted-foreground block text-xs">Relevance</span>
              <span className="font-bold text-success font-mono">≥ 0.85</span>
            </div>
            <div className="rounded bg-card p-2 border border-border">
              <span className="text-muted-foreground block text-xs">Precision</span>
              <span className="font-bold text-success font-mono">≥ 0.80</span>
            </div>
          </div>

          <Button
            className="w-full h-8 text-xs gap-1"
            size="sm"
            type="button"
            variant="outline"
            onClick={() => onNavigate(`/evaluation?assistant=${encodeURIComponent(assistantCode)}`)}
          >
            <ShieldCheck className="size-3.5 text-primary" />
            Xem báo cáo kiểm định benchmark
            <ExternalLink className="size-3 ml-auto opacity-50" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
