import { useId } from "react";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { Input } from "@/components/ui/input";
import type { MetadataFilter } from "./types";
import { compactMetadataFilter } from "./types";

/**
 * Controlled metadata-scope fields.
 *
 * Years stay strings while typing so an empty box is "not set" instead of `0`.
 * `draftToFilter` drops empty entries, which keeps the backend inheritance rule
 * intact (an empty filter means "no explicit scope", not "match nothing").
 * Nonempty invalid years must be corrected before conversion or submission.
 */
export type MetadataFilterDraft = {
  data_year: string;
  issued_year: string;
  effective_on: string;
  program: string;
  intake: string;
};

export const EMPTY_METADATA_FILTER_DRAFT: MetadataFilterDraft = {
  data_year: "",
  issued_year: "",
  effective_on: "",
  program: "",
  intake: "",
};

export function validateMetadataFilterDraft(draft: MetadataFilterDraft) {
  const errors: Partial<Record<"data_year" | "issued_year", string>> = {};
  for (const key of ["data_year", "issued_year"] as const) {
    const text = draft[key].trim();
    const year = Number(text);
    if (text && (!Number.isInteger(year) || year < 1000 || year > 9999)) {
      errors[key] = "Năm phải là số nguyên từ 1000 đến 9999.";
    }
  }
  return errors;
}

export function draftToFilter(draft: MetadataFilterDraft): MetadataFilter {
  const errors = validateMetadataFilterDraft(draft);
  if (Object.keys(errors).length > 0) {
    throw new Error("Phạm vi có năm không hợp lệ. Hãy sửa trước khi gửi.");
  }
  return compactMetadataFilter({
    data_year: draft.data_year.trim() ? Number(draft.data_year) : null,
    issued_year: draft.issued_year.trim() ? Number(draft.issued_year) : null,
    effective_on: draft.effective_on.trim() || null,
    program: draft.program.trim() || null,
    intake: draft.intake.trim() || null,
  });
}

export function filterToDraft(
  filter: MetadataFilter | null | undefined,
): MetadataFilterDraft {
  return {
    data_year: filter?.data_year ? String(filter.data_year) : "",
    issued_year: filter?.issued_year ? String(filter.issued_year) : "",
    effective_on: filter?.effective_on ?? "",
    program: filter?.program ?? "",
    intake: filter?.intake ?? "",
  };
}

export function isMetadataFilterDraftEmpty(
  draft: MetadataFilterDraft,
): boolean {
  return Object.values(draft).every((value) => !value.trim());
}

export function MetadataFilterFields({
  value,
  onChange,
  disabled,
  columns = 2,
  showHint = true,
}: {
  value: MetadataFilterDraft;
  onChange: (next: MetadataFilterDraft) => void;
  disabled?: boolean;
  columns?: 2 | 3;
  showHint?: boolean;
}) {
  const dataYearId = useId();
  const issuedYearId = useId();
  const effectiveOnId = useId();
  const programId = useId();
  const intakeId = useId();
  const errors = validateMetadataFilterDraft(value);

  const patch = (part: Partial<MetadataFilterDraft>) =>
    onChange({ ...value, ...part });

  return (
    <div
      className={`grid grid-cols-1 gap-3 ${
        columns === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"
      }`}
    >
      <Field>
        <FieldLabel htmlFor={dataYearId}>Năm dữ liệu</FieldLabel>
        <Input
          id={dataYearId}
          type="number"
          min={1000}
          max={9999}
          inputMode="numeric"
          placeholder="Không giới hạn"
          value={value.data_year}
          disabled={disabled}
          aria-invalid={Boolean(errors.data_year)}
          aria-describedby={
            errors.data_year ? `${dataYearId}-error` : undefined
          }
          onChange={(event) => patch({ data_year: event.target.value })}
          className="text-xs"
        />
        {errors.data_year ? (
          <FieldError id={`${dataYearId}-error`}>{errors.data_year}</FieldError>
        ) : null}
      </Field>

      <Field>
        <FieldLabel htmlFor={issuedYearId}>Năm ban hành</FieldLabel>
        <Input
          id={issuedYearId}
          type="number"
          min={1000}
          max={9999}
          inputMode="numeric"
          placeholder="Không giới hạn"
          value={value.issued_year}
          disabled={disabled}
          aria-invalid={Boolean(errors.issued_year)}
          aria-describedby={
            errors.issued_year ? `${issuedYearId}-error` : undefined
          }
          onChange={(event) => patch({ issued_year: event.target.value })}
          className="text-xs"
        />
        {errors.issued_year ? (
          <FieldError id={`${issuedYearId}-error`}>
            {errors.issued_year}
          </FieldError>
        ) : null}
      </Field>

      <Field>
        <FieldLabel htmlFor={effectiveOnId}>Hiệu lực tại ngày</FieldLabel>
        <Input
          id={effectiveOnId}
          type="date"
          value={value.effective_on}
          disabled={disabled}
          onChange={(event) => patch({ effective_on: event.target.value })}
          className="text-xs"
        />
        {showHint ? (
          <FieldDescription className="text-[11px]">
            Chỉ khớp tài liệu có đủ cả ngày bắt đầu và kết thúc hiệu lực.
          </FieldDescription>
        ) : null}
      </Field>

      <Field>
        <FieldLabel htmlFor={programId}>Ngành</FieldLabel>
        <Input
          id={programId}
          maxLength={160}
          placeholder="VD: Kỹ thuật phần mềm"
          value={value.program}
          disabled={disabled}
          onChange={(event) => patch({ program: event.target.value })}
          className="text-xs"
        />
      </Field>

      <Field>
        <FieldLabel htmlFor={intakeId}>Đợt</FieldLabel>
        <Input
          id={intakeId}
          maxLength={160}
          placeholder="VD: Đợt 1 - 2026"
          value={value.intake}
          disabled={disabled}
          onChange={(event) => patch({ intake: event.target.value })}
          className="text-xs"
        />
      </Field>
    </div>
  );
}
