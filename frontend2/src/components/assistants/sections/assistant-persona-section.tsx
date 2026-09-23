import { Loader2, Plus, Sparkles, Trash2 } from "lucide-react";
import { Field } from "@/components/admin/field";
import {
  type AssistantEditForm,
  CATEGORY_OPTIONS,
} from "@/components/assistants/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

interface AssistantPersonaSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  onGeneratePrompt: () => void;
  isGeneratingPrompt: boolean;
}

export function AssistantPersonaSection({
  form,
  onChange,
  onGeneratePrompt,
  isGeneratingPrompt,
}: AssistantPersonaSectionProps) {
  const handleAddQuestion = () => {
    onChange({
      ...form,
      sample_questions: [
        ...form.sample_questions,
        {
          id: `sq-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          text: "",
        },
      ],
    });
  };

  const handleUpdateQuestion = (id: string, text: string) => {
    onChange({
      ...form,
      sample_questions: form.sample_questions.map((q) =>
        q.id === id ? { ...q, text } : q,
      ),
    });
  };

  const handleRemoveQuestion = (id: string) => {
    onChange({
      ...form,
      sample_questions: form.sample_questions.filter((q) => q.id !== id),
    });
  };

  return (
    <div className="space-y-6">
      {/* Thông tin & Persona Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-bold">
            Thông tin & Persona
          </CardTitle>
          <CardDescription className="text-xs">
            Cấu hình nhận diện, phạm vi chuyên môn và system prompt của Trợ lý.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <Field htmlFor="detail-assistant-name" label="Tên trợ lý" required>
            <Input
              id="detail-assistant-name"
              required
              value={form.name}
              onChange={(e) => onChange({ ...form, name: e.target.value })}
            />
          </Field>

          <Field
            htmlFor="detail-assistant-category"
            label="Lĩnh vực chuyên môn"
            required
          >
            <Select
              value={form.category}
              onValueChange={(val) => onChange({ ...form, category: val })}
            >
              <SelectTrigger id="detail-assistant-category">
                <SelectValue placeholder="Chọn lĩnh vực" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            className="sm:col-span-2"
            htmlFor="detail-assistant-description"
            label="Mô tả chức năng"
          >
            <Textarea
              id="detail-assistant-description"
              rows={2}
              value={form.description}
              onChange={(e) =>
                onChange({ ...form, description: e.target.value })
              }
            />
          </Field>

          <div className="sm:col-span-2 space-y-1.5">
            <div className="flex items-center justify-between">
              <label
                htmlFor="detail-assistant-prompt"
                className="text-xs font-semibold text-foreground"
              >
                System Prompt (Chỉ thị hệ thống)
              </label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-primary hover:bg-primary/10 gap-1 font-medium"
                disabled={
                  isGeneratingPrompt ||
                  (!form.name.trim() && !form.description.trim())
                }
                onClick={onGeneratePrompt}
              >
                {isGeneratingPrompt ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Sparkles className="size-3" />
                )}
                Viết hộ tôi
              </Button>
            </div>
            <Textarea
              className="min-h-40 font-mono text-xs leading-relaxed"
              id="detail-assistant-prompt"
              value={form.system_prompt}
              onChange={(e) =>
                onChange({ ...form, system_prompt: e.target.value })
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Editable Sample Questions */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm font-bold">
              Câu Hỏi Gợi Ý Cho Người Dùng
            </CardTitle>
            <CardDescription className="text-xs">
              Các câu hỏi mẫu hiển thị trên khung chat giúp sinh viên / giảng
              viên tra cứu nhanh.
            </CardDescription>
          </div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 text-xs gap-1"
            onClick={handleAddQuestion}
          >
            <Plus className="size-3.5 text-primary" />
            Thêm câu hỏi
          </Button>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {form.sample_questions.length === 0 ? (
            <p className="p-4 text-center text-xs text-muted-foreground border border-dashed rounded-md">
              Chưa có câu hỏi gợi ý nào. Nhấn “Thêm câu hỏi” để bổ sung.
            </p>
          ) : (
            form.sample_questions.map((questionItem, idx) => (
              <div key={questionItem.id} className="flex items-center gap-2">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-bold text-muted-foreground">
                  {idx + 1}
                </span>
                <Input
                  value={questionItem.text}
                  onChange={(e) =>
                    handleUpdateQuestion(questionItem.id, e.target.value)
                  }
                  placeholder="Nhập nội dung câu hỏi gợi ý…"
                  className="h-9 text-xs"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-8 shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => handleRemoveQuestion(questionItem.id)}
                  aria-label={`Xóa câu hỏi gợi ý số ${idx + 1}`}
                  title="Xóa câu hỏi này"
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
