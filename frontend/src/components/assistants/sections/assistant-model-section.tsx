import { Field } from "@/components/admin/field";
import { OptionSelect } from "@/components/admin/option-select";
import type { AssistantEditForm } from "@/components/assistants/types";
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
  type AssistantModelOption,
  selectedModelValue,
} from "@/features/assistants/model-options";

interface AssistantModelSectionProps {
  form: AssistantEditForm;
  onChange: (updated: AssistantEditForm) => void;
  availableModels: AssistantModelOption[];
  hasUnsavedChanges?: boolean;
  savedPrimaryModel?: string | null;
  isSaving?: boolean;
}

export function AssistantModelSection({
  form,
  onChange,
  availableModels,
  hasUnsavedChanges = false,
  savedPrimaryModel,
  isSaving = false,
}: AssistantModelSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-bold">
          ModelOps & Phân Tuyến Dự Phòng
        </CardTitle>
        <CardDescription className="text-xs">
          Cấu hình mô hình ngôn ngữ chính, mô hình dự phòng khi 429/timeout và
          tham số sinh.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2">
        <p className="col-span-full text-xs text-muted-foreground">
          Chọn LLM từ các provider đang hoạt động trong ModelOps. Lựa chọn chỉ
          có hiệu lực với lượt chat mới sau khi lưu. Khi dùng provider ngoài,
          câu hỏi và các đoạn tài liệu liên quan sẽ được gửi đến provider đó.
        </p>
        {hasUnsavedChanges && (
          <div
            role="status"
            className="col-span-full flex flex-col items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-3 text-sm sm:flex-row sm:items-center sm:justify-between"
          >
            <p>
              Chưa lưu thay đổi model. Model chính đã lưu:{" "}
              {savedPrimaryModel || "Mặc định"}.
            </p>
            <Button
              type="submit"
              size="sm"
              disabled={isSaving}
              className="shrink-0"
            >
              {isSaving ? "Đang lưu…" : "Lưu thay đổi"}
            </Button>
          </div>
        )}
        {availableModels.length === 0 && (
          <div className="col-span-full rounded-control border border-warning/30 bg-warning/10 p-2.5 text-xs text-warning-foreground">
            Chưa có Nhà cung cấp AI nào đang hoạt động. Vui lòng bật ít nhất một
            Provider trong danh mục ModelOps để chọn mô hình chính và dự phòng.
          </div>
        )}
        <Field htmlFor="detail-primary-model" label="Mô hình chính (Primary)">
          {(control) => (
            <OptionSelect
              triggerProps={control}
              options={[
                { value: "__none__", label: "Chưa có mô hình" },
                ...availableModels,
              ]}
              placeholder="Chưa có mô hình"
              value={selectedModelValue(
                availableModels,
                form.primary_model,
                form.preferred_provider_id,
              )}
              onValueChange={(val) =>
                onChange({
                  ...form,
                  primary_model:
                    availableModels.find((m) => m.value === val)?.model ?? "",
                  preferred_provider_id:
                    availableModels.find((m) => m.value === val)?.providerId ??
                    "",
                })
              }
            />
          )}
        </Field>

        <Field
          htmlFor="detail-fallback-model"
          label="Mô hình dự phòng (Fallback)"
        >
          {(control) => (
            <OptionSelect
              triggerProps={control}
              options={[
                { value: "__none__", label: "Chưa có mô hình" },
                ...availableModels,
              ]}
              placeholder="Chưa có mô hình"
              value={selectedModelValue(
                availableModels,
                form.fallback_model,
                form.fallback_provider_id,
              )}
              onValueChange={(val) =>
                onChange({
                  ...form,
                  fallback_model:
                    availableModels.find((m) => m.value === val)?.model ?? "",
                  fallback_provider_id:
                    availableModels.find((m) => m.value === val)?.providerId ??
                    "",
                })
              }
            />
          )}
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
            onChange={(e) =>
              onChange({ ...form, temperature: Number(e.target.value) })
            }
          />
        </Field>

        <Field
          htmlFor="detail-max-tokens"
          label="Max Tokens (Hạn mức sinh)"
          hint="Độ dài tối đa cho mỗi phản hồi; phụ thuộc khả năng của model. Không phải quota sử dụng."
        >
          <Input
            id="detail-max-tokens"
            min="128"
            type="number"
            value={form.max_tokens}
            onChange={(e) =>
              onChange({ ...form, max_tokens: Number(e.target.value) })
            }
          />
        </Field>

        <Field
          htmlFor="detail-thinking-budget"
          label="Thinking Budget (Suy nghĩ ngầm)"
          hint="0: không yêu cầu ngân sách suy luận riêng. Giá trị lớn hơn chỉ có tác dụng nếu provider/model hỗ trợ."
        >
          <Input
            id="detail-thinking-budget"
            max="4096"
            min="0"
            step="128"
            type="number"
            value={form.thinking_budget ?? 0}
            onChange={(e) =>
              onChange({ ...form, thinking_budget: Number(e.target.value) })
            }
          />
        </Field>
      </CardContent>
    </Card>
  );
}
