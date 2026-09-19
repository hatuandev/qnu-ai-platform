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
        <Field htmlFor="detail-primary-model" label="Mô hình chính (Primary)">
          <Select
            value={form.primary_model}
            onValueChange={(val) => onChange({ ...form, primary_model: val })}
          >
            <SelectTrigger id="detail-primary-model">
              <SelectValue placeholder="Chọn mô hình chính" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <Field htmlFor="detail-fallback-model" label="Mô hình dự phòng (Fallback)">
          <Select
            value={form.fallback_model}
            onValueChange={(val) => onChange({ ...form, fallback_model: val })}
          >
            <SelectTrigger id="detail-fallback-model">
              <SelectValue placeholder="Chọn mô hình dự phòng" />
            </SelectTrigger>
            <SelectContent>
              {availableModels.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
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
      </CardContent>
    </Card>
  );
}
