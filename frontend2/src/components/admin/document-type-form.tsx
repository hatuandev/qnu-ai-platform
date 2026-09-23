import type { FormEvent } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  DocumentTypeCategory,
  DocumentTypeInput,
} from "@/services/document-types-api";

interface DocumentTypeFormProps {
  formId: string;
  value: DocumentTypeInput;
  isCodeEditable: boolean;
  isSubmitting: boolean;
  submitLabel: string;
  onChange: (value: DocumentTypeInput) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

const CATEGORY_OPTIONS: Array<{ value: DocumentTypeCategory; label: string }> =
  [
    { value: "legal_internal", label: "Quy phạm & Nội bộ" },
    { value: "administrative", label: "Hành chính Điều hành" },
    { value: "academic", label: "Đào tạo & Học thuật" },
    { value: "forms", label: "Biểu mẫu & Tiếp nhận" },
  ];

export function DocumentTypeForm({
  formId,
  value,
  isCodeEditable,
  isSubmitting,
  submitLabel,
  onChange,
  onSubmit,
}: DocumentTypeFormProps) {
  const updateField = <K extends keyof DocumentTypeInput>(
    field: K,
    fieldValue: DocumentTypeInput[K],
  ) => {
    onChange({ ...value, [field]: fieldValue });
  };

  return (
    <form id={formId} className="space-y-4" onSubmit={onSubmit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-foreground"
            htmlFor={`${formId}-code`}
          >
            Mã chuẩn
          </label>
          <input
            id={`${formId}-code`}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 font-mono text-xs shadow-2xs outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={!isCodeEditable || isSubmitting}
            maxLength={64}
            pattern="[a-z0-9]+(?:_[a-z0-9]+)*"
            required
            value={value.code}
            onChange={(event) => updateField("code", event.target.value)}
          />
          <p className="text-[11px] text-muted-foreground">
            Ví dụ: quyet_dinh, thong_bao
          </p>
        </div>
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-foreground"
            htmlFor={`${formId}-name`}
          >
            Tên hiển thị
          </label>
          <input
            id={`${formId}-name`}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-2xs outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            maxLength={255}
            required
            value={value.name}
            onChange={(event) => updateField("name", event.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-1.5 sm:col-span-2">
          <label
            className="text-xs font-medium text-foreground"
            htmlFor={`${formId}-category`}
          >
            Nhóm phân loại
          </label>
          <Select
            disabled={isSubmitting}
            value={value.category}
            onValueChange={(category) =>
              updateField("category", category as DocumentTypeCategory)
            }
          >
            <SelectTrigger id={`${formId}-category`}>
              <SelectValue placeholder="Chọn nhóm" />
            </SelectTrigger>
            <SelectContent>
              {CATEGORY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-foreground"
            htmlFor={`${formId}-priority`}
          >
            Độ ưu tiên
          </label>
          <input
            id={`${formId}-priority`}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-2xs outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            max={10}
            min={1}
            required
            type="number"
            value={value.priority}
            onChange={(event) =>
              updateField("priority", Number(event.target.value))
            }
          />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <label
            className="text-xs font-medium text-foreground"
            htmlFor={`${formId}-retention`}
          >
            Thời hạn lưu trữ
          </label>
          <input
            id={`${formId}-retention`}
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-2xs outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            maxLength={64}
            placeholder="Ví dụ: 10 năm hoặc Vĩnh viễn"
            value={value.retention_period}
            onChange={(event) =>
              updateField("retention_period", event.target.value)
            }
          />
        </div>
        <div className="flex items-end pb-1 text-xs text-muted-foreground">
          Mã NĐ30 được xác định tự động từ taxonomy chuẩn.
        </div>
      </div>

      <div className="space-y-1.5">
        <label
          className="text-xs font-medium text-foreground"
          htmlFor={`${formId}-description`}
        >
          Mô tả nghiệp vụ
        </label>
        <textarea
          id={`${formId}-description`}
          className="min-h-24 w-full resize-y rounded-md border border-input bg-background px-3 py-2 text-sm shadow-2xs outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          maxLength={4000}
          value={value.description}
          onChange={(event) => updateField("description", event.target.value)}
        />
      </div>

      <button className="sr-only" disabled={isSubmitting} type="submit">
        {submitLabel}
      </button>
    </form>
  );
}
