import { Field } from "@/components/admin/field";
import type { AssistantEditForm } from "@/components/assistants/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface AssistantModelSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  availableModels: { value: string; label: string; providerName: string }[];
}

export function AssistantModelSection({
  form,
  onChange,
  availableModels,
}: AssistantModelSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-bold">ModelOps & Phân Tuyến Dự Phòng</CardTitle>
        <CardDescription className="text-xs">
          Cấu hình mô hình ngôn ngữ chính, mô hình dự phòng khi 429/timeout và tham số sinh.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        {availableModels.length === 0 && (
          <div className="col-span-full rounded-control border border-warning/30 bg-warning/10 p-2.5 text-xs text-warning-foreground">
            Chưa có Nhà cung cấp AI nào đang hoạt động. Vui lòng bật ít nhất một Provider trong danh
            mục ModelOps để chọn mô hình chính và dự phòng.
          </div>
        )}
        <Field htmlFor="detail-primary-model" label="Mô hình chính (Primary)">
          <Select
            value={form.primary_model}
            onValueChange={(val) => onChange({ ...form, primary_model: val })}
          >
            <SelectTrigger id="detail-primary-model">
              <SelectValue
                placeholder={availableModels.length > 0 ? "Chọn mô hình chính" : "Không có mô hình"}
              />
            </SelectTrigger>
            <SelectContent>
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))
              ) : (
                <div className="p-2 text-center text-xs text-muted-foreground">
                  Chưa có mô hình nào khả dụng
                </div>
              )}
            </SelectContent>
          </Select>
        </Field>

        <Field htmlFor="detail-fallback-model" label="Mô hình dự phòng (Fallback)">
          <Select
            value={form.fallback_model}
            onValueChange={(val) => onChange({ ...form, fallback_model: val })}
          >
            <SelectTrigger id="detail-fallback-model">
              <SelectValue
                placeholder={
                  availableModels.length > 0 ? "Chọn mô hình dự phòng" : "Không có mô hình"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {availableModels.length > 0 ? (
                availableModels.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))
              ) : (
                <div className="p-2 text-center text-xs text-muted-foreground">
                  Chưa có mô hình nào khả dụng
                </div>
              )}
            </SelectContent>
          </Select>
        </Field>

        <Field
          htmlFor="detail-temperature"
          label="Temperature (Nhiệt độ sáng tạo)"
          hint="0.1-0.2: quy chế, tuyển sinh; 0.5-0.7: soạn thảo, sáng tạo"
        >
          <Input
            id="detail-temperature"
            max="2"
            min="0"
            step="0.1"
            type="number"
            value={form.temperature}
            onChange={(e) => onChange({ ...form, temperature: Number(e.target.value) })}
          />
        </Field>

        <Field
          htmlFor="detail-max-tokens"
          label="Max Tokens (Hạn mức sinh)"
          hint="Số lượng token tối đa cho mỗi phản hồi (500 - 4000)"
        >
          <Input
            id="detail-max-tokens"
            min="128"
            type="number"
            value={form.max_tokens}
            onChange={(e) => onChange({ ...form, max_tokens: Number(e.target.value) })}
          />
        </Field>

        <Field
          htmlFor="detail-thinking-budget"
          label="Thinking Budget (Suy nghĩ ngầm)"
          hint="0 = Tắt suy nghĩ ngầm (phản hồi siêu tốc 1-2s). > 0: Bật suy luận sâu cho Gemini 2.5 (0 - 4096 tokens)"
        >
          <Input
            id="detail-thinking-budget"
            max="4096"
            min="0"
            step="128"
            type="number"
            value={form.thinking_budget ?? 0}
            onChange={(e) => onChange({ ...form, thinking_budget: Number(e.target.value) })}
          />
        </Field>
      </CardContent>
    </Card>
  );
}
