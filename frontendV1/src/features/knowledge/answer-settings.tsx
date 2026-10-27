import { useId } from "react";
import { Combobox } from "@/components/admin/combobox";
import { Field, FieldLabel } from "@/components/admin/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { CatalogItem } from "@/features/modelops/types";
import {
  RETRIEVAL_MODE_LABEL,
  VERIFICATION_MODE_LABEL,
} from "@/features/rag/types";
import type { AnswerSettings as Settings } from "./answer-request";

type NumberKey =
  | "top_k"
  | "max_output_tokens"
  | "candidate_k"
  | "rrf_k"
  | "context_window"
  | "context_max_bytes"
  | "verification_max_output_tokens";
type Props = {
  value: Settings;
  onChange: (value: Settings) => void;
  catalog: CatalogItem[];
  disabled: boolean;
};
function ProviderPicker({
  label,
  capability,
  value,
  catalog,
  disabled,
  onChange,
}: {
  label: string;
  capability: string;
  value: string | null;
  catalog: CatalogItem[];
  disabled: boolean;
  onChange: (id: string | null) => void;
}) {
  return (
    <section aria-label={label} className="space-y-2">
      <p className="text-sm font-medium">{label}</p>
      <Combobox
        disabled={disabled}
        options={[
          { value: "__default__", label: "Theo mặc định workspace" },
          ...catalog
            .filter((p) => p.capabilities.includes(capability))
            .map((p) => ({
              value: p.id,
              label: `${p.name} · ${p.model_name}`,
            })),
        ]}
        value={value ?? "__default__"}
        onValueChange={(id) =>
          onChange(id === "__default__" ? null : (id ?? null))
        }
        placeholder={label}
      />
    </section>
  );
}
function NumberSetting({
  name,
  label,
  min,
  max,
  value,
  disabled,
  onChange,
}: {
  name: NumberKey;
  label: string;
  min: number;
  max?: number;
  value: number;
  disabled: boolean;
  onChange: (n: number) => void;
}) {
  const id = useId();
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        name={name}
        type="number"
        min={min}
        max={max}
        step={1}
        value={Number.isNaN(value) ? "" : value}
        disabled={disabled}
        onChange={(e) =>
          onChange(e.target.value === "" ? Number.NaN : Number(e.target.value))
        }
      />
    </Field>
  );
}
export function AnswerSettings({ value, catalog, disabled, onChange }: Props) {
  const numeric = (
    name: NumberKey,
    label: string,
    min: number,
    max?: number,
  ) => (
    <NumberSetting
      key={name}
      name={name}
      label={label}
      min={min}
      max={max}
      value={value[name]}
      disabled={disabled}
      onChange={(n) => onChange({ ...value, [name]: n })}
    />
  );
  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <ProviderPicker
          label="Model trả lời"
          capability="chat"
          catalog={catalog}
          value={value.provider_id}
          disabled={disabled}
          onChange={(id) => onChange({ ...value, provider_id: id })}
        />
        {numeric("top_k", "Số đoạn truy xuất (Top K)", 1, 20)}
      </div>
      <details className="rounded-lg border p-3">
        <summary className="cursor-pointer text-sm font-medium">
          Cấu hình RAG
        </summary>
        <div className="mt-4 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <p className="text-sm font-medium">Cách truy xuất</p>
              <Select
                value={value.retrieval_mode}
                disabled={disabled}
                onValueChange={(mode) =>
                  onChange({
                    ...value,
                    retrieval_mode: mode as Settings["retrieval_mode"],
                    rerank_provider_id:
                      mode === "hybrid_rerank"
                        ? value.rerank_provider_id
                        : null,
                  })
                }
              >
                <SelectTrigger aria-label="Cách truy xuất">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(RETRIEVAL_MODE_LABEL).map(([id, label]) => (
                    <SelectItem key={id} value={id}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {numeric("max_output_tokens", "Token tối đa cho câu trả lời", 1)}
            {value.retrieval_mode !== "dense" ? (
              <>
                {numeric("candidate_k", "Số ứng viên", 1, 100)}
                {numeric("rrf_k", "Hệ số RRF", 1, 1000)}
              </>
            ) : null}
            {value.retrieval_mode === "hybrid_rerank" ? (
              <ProviderPicker
                label="Model rerank"
                capability="rerank"
                catalog={catalog}
                value={value.rerank_provider_id}
                disabled={disabled}
                onChange={(id) =>
                  onChange({ ...value, rerank_provider_id: id })
                }
              />
            ) : null}
            {numeric("context_window", "Đoạn lân cận mỗi phía", 0, 5)}
            {numeric(
              "context_max_bytes",
              "Giới hạn ngữ cảnh (byte)",
              256,
              128000,
            )}
            <div className="space-y-2">
              <p className="text-sm font-medium">Kiểm chứng với nguồn</p>
              <Select
                value={value.verification_mode}
                disabled={disabled}
                onValueChange={(mode) =>
                  onChange({
                    ...value,
                    verification_mode: mode as Settings["verification_mode"],
                    verification_provider_id:
                      mode === "off" ? null : value.verification_provider_id,
                  })
                }
              >
                <SelectTrigger aria-label="Kiểm chứng với nguồn">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(VERIFICATION_MODE_LABEL).map(
                    ([id, label]) => (
                      <SelectItem key={id} value={id}>
                        {label}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>
            {value.verification_mode !== "off" ? (
              <>
                <ProviderPicker
                  label="Model kiểm chứng"
                  capability="chat"
                  catalog={catalog}
                  value={value.verification_provider_id}
                  disabled={disabled}
                  onChange={(id) =>
                    onChange({ ...value, verification_provider_id: id })
                  }
                />
                {numeric(
                  "verification_max_output_tokens",
                  "Token tối đa cho kiểm chứng",
                  128,
                  16000,
                )}
              </>
            ) : null}
          </div>
          <p className="text-xs text-muted-foreground">
            Chỉ áp dụng cho lần hỏi thử này. Model được chọn từ danh sách
            workspace được phép dùng; cấu hình trợ lý được giữ nguyên.
          </p>
        </div>
      </details>
    </div>
  );
}
