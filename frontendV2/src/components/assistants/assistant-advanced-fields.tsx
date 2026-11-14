import type { RagPolicy } from "@/api/assistants";
import type { CatalogItem } from "@/api/modelops";
import { Field, FieldDescription, FieldLabel } from "@/components/admin/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { localityLabel, providerLabel } from "./model-label";

export const AUTO_POLICY_TARGET = "auto";

export type RagPolicyFormState = {
  retrievalMode: RagPolicy["retrieval_mode"];
  candidateK: string;
  rrfK: string;
  rerankProviderId: string;
  dataYear: string;
  issuedYear: string;
  effectiveOn: string;
  program: string;
  intake: string;
  scopeResolution: RagPolicy["scope_resolution"];
  contextWindow: string;
  contextMaxBytes: string;
  verificationMode: RagPolicy["verification_mode"];
  verificationProviderId: string;
  verificationMaxOutputTokens: string;
};

/** Creation defaults match `NewAssistantRagPolicy` in the backend schema. */
export const NEW_ASSISTANT_POLICY: RagPolicy = {
  retrieval_mode: "hybrid_rerank",
  candidate_k: 30,
  rrf_k: 60,
  rerank_provider_id: null,
  metadata_filter: {},
  scope_resolution: "catalog",
  context_window: 1,
  context_max_bytes: 32000,
  verification_mode: "off",
  verification_provider_id: null,
  verification_max_output_tokens: null,
};

type ChoiceOption<T extends string> = {
  value: T;
  label: string;
  hint: string;
};

export const RETRIEVAL_OPTIONS: ChoiceOption<RagPolicy["retrieval_mode"]>[] = [
  {
    value: "hybrid_rerank",
    label: "Kết hợp + xếp hạng lại",
    hint: "Ngữ nghĩa và từ khoá, rồi xếp hạng lại.",
  },
  {
    value: "hybrid",
    label: "Kết hợp",
    hint: "Ngữ nghĩa và từ khoá, không xếp hạng lại.",
  },
  {
    value: "dense",
    label: "Ngữ nghĩa",
    hint: "Chỉ tìm theo ngữ nghĩa.",
  },
];

export const SCOPE_OPTIONS: ChoiceOption<RagPolicy["scope_resolution"]>[] = [
  {
    value: "catalog",
    label: "Theo tài liệu",
    hint: "Mở rộng theo phạm vi của tài liệu tìm được.",
  },
  {
    value: "explicit",
    label: "Chỉ theo bộ lọc",
    hint: "Chỉ dùng tài liệu khớp đúng bộ lọc dữ kiện.",
  },
];

export const VERIFICATION_OPTIONS: ChoiceOption<
  RagPolicy["verification_mode"]
>[] = [
  {
    value: "off",
    label: "Tắt",
    hint: "Không chạy bước kiểm chứng.",
  },
  {
    value: "observe",
    label: "Theo dõi",
    hint: "Vẫn trả lời, ghi nhận cảnh báo.",
  },
  {
    value: "enforce",
    label: "Bắt buộc",
    hint: "Chặn câu trả lời thiếu căn cứ.",
  },
];

type MetadataFilterFields = {
  data_year?: number;
  issued_year?: number;
  effective_on?: string;
  program?: string;
  intake?: string;
};

export function ragPolicyToForm(policy: RagPolicy): RagPolicyFormState {
  const filter = policy.metadata_filter as MetadataFilterFields;
  return {
    retrievalMode: policy.retrieval_mode,
    candidateK: String(policy.candidate_k),
    rrfK: String(policy.rrf_k),
    rerankProviderId: policy.rerank_provider_id ?? AUTO_POLICY_TARGET,
    dataYear: filter.data_year != null ? String(filter.data_year) : "",
    issuedYear: filter.issued_year != null ? String(filter.issued_year) : "",
    effectiveOn: filter.effective_on ?? "",
    program: filter.program ?? "",
    intake: filter.intake ?? "",
    scopeResolution: policy.scope_resolution,
    contextWindow: String(policy.context_window),
    contextMaxBytes: String(policy.context_max_bytes),
    verificationMode: policy.verification_mode,
    verificationProviderId:
      policy.verification_provider_id ?? AUTO_POLICY_TARGET,
    verificationMaxOutputTokens:
      policy.verification_max_output_tokens != null
        ? String(policy.verification_max_output_tokens)
        : "",
  };
}

export function formToRagPolicy(
  form: RagPolicyFormState,
  base: RagPolicy,
): RagPolicy {
  const metadataFilter: Record<string, unknown> = {};
  if (form.dataYear.trim()) {
    metadataFilter.data_year = Number(form.dataYear);
  }
  if (form.issuedYear.trim()) {
    metadataFilter.issued_year = Number(form.issuedYear);
  }
  if (form.effectiveOn.trim()) {
    metadataFilter.effective_on = form.effectiveOn.trim();
  }
  if (form.program.trim()) {
    metadataFilter.program = form.program.trim();
  }
  if (form.intake.trim()) {
    metadataFilter.intake = form.intake.trim();
  }
  const attributes = base.metadata_filter.attributes;
  if (attributes != null) {
    metadataFilter.attributes = attributes;
  }
  return {
    retrieval_mode: form.retrievalMode,
    candidate_k: Number(form.candidateK),
    rrf_k: Number(form.rrfK),
    rerank_provider_id:
      form.retrievalMode === "hybrid_rerank" &&
      form.rerankProviderId !== AUTO_POLICY_TARGET
        ? form.rerankProviderId
        : null,
    metadata_filter: metadataFilter,
    scope_resolution: form.scopeResolution,
    context_window: Number(form.contextWindow),
    context_max_bytes: Number(form.contextMaxBytes),
    verification_mode: form.verificationMode,
    verification_provider_id:
      form.verificationMode !== "off" &&
      form.verificationProviderId !== AUTO_POLICY_TARGET
        ? form.verificationProviderId
        : null,
    verification_max_output_tokens: form.verificationMaxOutputTokens.trim()
      ? Number(form.verificationMaxOutputTokens)
      : null,
  };
}

function isYear(value: string): boolean {
  const year = Number(value);
  return Number.isInteger(year) && year >= 1000 && year <= 9999;
}

export function validateRagPolicy(
  form: RagPolicyFormState,
  topK: number,
): string | null {
  const candidateK = Number(form.candidateK);
  if (!Number.isInteger(candidateK) || candidateK < 1 || candidateK > 100) {
    return "Số ứng viên truy xuất phải là số nguyên từ 1 đến 100.";
  }
  if (form.retrievalMode !== "dense" && candidateK < topK) {
    return "Số ứng viên truy xuất phải lớn hơn hoặc bằng số đoạn trích dẫn.";
  }
  const rrfK = Number(form.rrfK);
  if (!Number.isInteger(rrfK) || rrfK < 1 || rrfK > 1000) {
    return "Hằng số RRF phải là số nguyên từ 1 đến 1000.";
  }
  if (form.dataYear.trim() && !isYear(form.dataYear)) {
    return "Năm dữ liệu phải là số nguyên từ 1000 đến 9999.";
  }
  if (form.issuedYear.trim() && !isYear(form.issuedYear)) {
    return "Năm ban hành phải là số nguyên từ 1000 đến 9999.";
  }
  if (form.effectiveOn.trim()) {
    const valid =
      /^\d{4}-\d{2}-\d{2}$/.test(form.effectiveOn) &&
      !Number.isNaN(Date.parse(form.effectiveOn));
    if (!valid) return "Ngày hiệu lực không hợp lệ.";
  }
  const window = Number(form.contextWindow);
  if (!Number.isInteger(window) || window < 0 || window > 5) {
    return "Số đoạn ngữ cảnh lân cận phải là số nguyên từ 0 đến 5.";
  }
  const bytes = Number(form.contextMaxBytes);
  if (!Number.isInteger(bytes) || bytes < 256 || bytes > 128000) {
    return "Ngân sách ngữ cảnh phải là số nguyên từ 256 đến 128000 byte.";
  }
  if (form.verificationMaxOutputTokens.trim()) {
    const tokens = Number(form.verificationMaxOutputTokens);
    if (!Number.isInteger(tokens) || tokens <= 0) {
      return "Giới hạn token kiểm chứng phải là số nguyên dương hoặc để trống.";
    }
  }
  return null;
}

export function ModelOption({ item }: { item: CatalogItem }) {
  return (
    <span className="flex flex-col items-start">
      <span>{item.model_name}</span>
      <span className="text-[11px] text-muted-foreground">
        {providerLabel(item)}
        {localityLabel(item.provider_type)
          ? ` · ${localityLabel(item.provider_type)}`
          : ""}
      </span>
    </span>
  );
}

function PolicySelect<T extends string>({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string;
  value: T;
  options: ChoiceOption<T>[];
  disabled?: boolean;
  onChange: (value: T) => void;
}) {
  return (
    <Select
      value={value}
      onValueChange={(next) => onChange(next as T)}
      disabled={disabled}
    >
      <SelectTrigger className="h-9 bg-background text-xs">
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        {options.map((option) => (
          <SelectItem key={option.value} value={option.value}>
            <div className="flex flex-col text-left py-0.5">
              <span className="text-xs font-medium text-foreground">
                {option.label}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {option.hint}
              </span>
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function RetrievalFields({
  form,
  onChange,
  rerankModels,
  disabled,
}: {
  form: RagPolicyFormState;
  onChange: (patch: Partial<RagPolicyFormState>) => void;
  rerankModels: CatalogItem[];
  disabled?: boolean;
}) {
  return (
    <div className="space-y-4">
      <Field>
        <FieldLabel className="text-xs font-medium">
          Cách tìm tri thức
        </FieldLabel>
        <PolicySelect
          label="Cách tìm tri thức"
          value={form.retrievalMode}
          options={RETRIEVAL_OPTIONS}
          disabled={disabled}
          onChange={(value) =>
            onChange({
              retrievalMode: value,
              ...(value !== "hybrid_rerank"
                ? { rerankProviderId: AUTO_POLICY_TARGET }
                : {}),
            })
          }
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field>
          <FieldLabel className="text-xs font-medium">
            Ứng viên trước xếp hạng lại
          </FieldLabel>
          <Input
            type="number"
            min={1}
            max={100}
            value={form.candidateK}
            onChange={(event) => onChange({ candidateK: event.target.value })}
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
          <FieldDescription>
            Số đoạn lấy ra trước khi chọn trích dẫn; tối thiểu bằng số đoạn
            trích dẫn.
          </FieldDescription>
        </Field>
        <Field>
          <FieldLabel className="text-xs font-medium">
            Ngưỡng hợp nhất thứ hạng
          </FieldLabel>
          <Input
            type="number"
            min={1}
            max={1000}
            value={form.rrfK}
            onChange={(event) => onChange({ rrfK: event.target.value })}
            className="h-9 bg-background text-xs"
            disabled={disabled || form.retrievalMode === "dense"}
          />
          <FieldDescription>
            Điều hoà thứ hạng giữa các nguồn tìm kiếm; chỉ dùng ở chế độ kết
            hợp.
          </FieldDescription>
        </Field>
      </div>

      {form.retrievalMode === "hybrid_rerank" && (
        <Field>
          <FieldLabel className="text-xs font-medium">
            Mô hình xếp hạng lại
          </FieldLabel>
          <Select
            value={form.rerankProviderId}
            onValueChange={(value) => onChange({ rerankProviderId: value })}
            disabled={disabled}
          >
            <SelectTrigger className="h-9 bg-background text-xs">
              <SelectValue placeholder="Chọn mô hình xếp hạng" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={AUTO_POLICY_TARGET}>
                <span className="flex flex-col items-start">
                  <span>Tự động theo hệ thống</span>
                  <span className="text-[11px] text-muted-foreground">
                    Dùng mô hình xếp hạng mặc định
                  </span>
                </span>
              </SelectItem>
              {rerankModels.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  <ModelOption item={item} />
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {rerankModels.length === 0 ? (
            <p className="rounded-md border border-warning/30 bg-warning/10 px-2.5 py-2 text-[11px] text-warning">
              Chưa có mô hình xếp hạng khả dụng: câu trả lời dùng truy xuất kết
              hợp và ghi nhận việc giảm cấp trong nhật ký.
            </p>
          ) : (
            <FieldDescription>
              Nếu mô hình xếp hạng tạm không khả dụng, câu trả lời chuyển về
              truy xuất kết hợp và ghi nhận trong nhật ký.
            </FieldDescription>
          )}
        </Field>
      )}
    </div>
  );
}

export function ContextFields({
  form,
  onChange,
  disabled,
}: {
  form: RagPolicyFormState;
  onChange: (patch: Partial<RagPolicyFormState>) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-4">
      <Field>
        <FieldLabel className="text-xs font-medium">Phạm vi dữ kiện</FieldLabel>
        <PolicySelect
          label="Phạm vi dữ kiện"
          value={form.scopeResolution}
          options={SCOPE_OPTIONS}
          disabled={disabled}
          onChange={(value) => onChange({ scopeResolution: value })}
        />
      </Field>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field>
          <FieldLabel className="text-xs font-medium">
            Đoạn liền kề mở rộng
          </FieldLabel>
          <Input
            type="number"
            min={0}
            max={5}
            value={form.contextWindow}
            onChange={(event) =>
              onChange({ contextWindow: event.target.value })
            }
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
          <FieldDescription>
            0 để hệ thống tự chọn theo loại câu hỏi.
          </FieldDescription>
        </Field>
        <Field>
          <FieldLabel className="text-xs font-medium">
            Ngân sách ngữ cảnh (byte)
          </FieldLabel>
          <Input
            type="number"
            min={256}
            max={128000}
            step={1}
            value={form.contextMaxBytes}
            onChange={(event) =>
              onChange({ contextMaxBytes: event.target.value })
            }
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
          <FieldDescription>
            Giới hạn bằng chứng gửi cho mô hình, từ 256 đến 128000 byte.
          </FieldDescription>
        </Field>
      </div>
    </div>
  );
}

export function MetadataScopeFields({
  form,
  onChange,
  disabled,
}: {
  form: RagPolicyFormState;
  onChange: (patch: Partial<RagPolicyFormState>) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-4">
      <p className="text-[11px] text-muted-foreground">
        Chỉ tài liệu đã gắn metadata khớp bộ lọc mới được dùng; tài liệu chưa
        xác định không khớp.
      </p>

      <div className="grid gap-3 sm:grid-cols-3">
        <Field>
          <FieldLabel className="text-xs font-medium">Năm dữ liệu</FieldLabel>
          <Input
            type="number"
            min={1000}
            max={9999}
            value={form.dataYear}
            onChange={(event) => onChange({ dataYear: event.target.value })}
            placeholder="Mọi năm"
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
        </Field>
        <Field>
          <FieldLabel className="text-xs font-medium">Năm ban hành</FieldLabel>
          <Input
            type="number"
            min={1000}
            max={9999}
            value={form.issuedYear}
            onChange={(event) => onChange({ issuedYear: event.target.value })}
            placeholder="Mọi năm"
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
        </Field>
        <Field>
          <FieldLabel className="text-xs font-medium">
            Hiệu lực đến ngày
          </FieldLabel>
          <Input
            type="date"
            value={form.effectiveOn}
            onChange={(event) => onChange({ effectiveOn: event.target.value })}
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
        </Field>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Field>
          <FieldLabel className="text-xs font-medium">Ngành</FieldLabel>
          <Input
            value={form.program}
            onChange={(event) => onChange({ program: event.target.value })}
            placeholder="Mọi ngành"
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
        </Field>
        <Field>
          <FieldLabel className="text-xs font-medium">Đợt</FieldLabel>
          <Input
            value={form.intake}
            onChange={(event) => onChange({ intake: event.target.value })}
            placeholder="Mọi đợt"
            className="h-9 bg-background text-xs"
            disabled={disabled}
          />
        </Field>
      </div>
    </div>
  );
}

export function VerificationFields({
  form,
  onChange,
  chatModels,
  disabled,
}: {
  form: RagPolicyFormState;
  onChange: (patch: Partial<RagPolicyFormState>) => void;
  chatModels: CatalogItem[];
  disabled?: boolean;
}) {
  return (
    <div className="space-y-4">
      <Field>
        <FieldLabel className="text-xs font-medium">
          Chế độ kiểm chứng
        </FieldLabel>
        <PolicySelect
          label="Chế độ kiểm chứng"
          value={form.verificationMode}
          options={VERIFICATION_OPTIONS}
          disabled={disabled}
          onChange={(value) =>
            onChange({
              verificationMode: value,
              ...(value === "off"
                ? { verificationProviderId: AUTO_POLICY_TARGET }
                : {}),
            })
          }
        />
      </Field>

      {form.verificationMode !== "off" && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Field>
            <FieldLabel className="text-xs font-medium">
              Mô hình kiểm chứng
            </FieldLabel>
            <Select
              value={form.verificationProviderId}
              onValueChange={(value) =>
                onChange({ verificationProviderId: value })
              }
              disabled={disabled}
            >
              <SelectTrigger className="h-9 bg-background text-xs">
                <SelectValue placeholder="Chọn mô hình kiểm chứng" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={AUTO_POLICY_TARGET}>
                  <span className="flex flex-col items-start">
                    <span>Mô hình trò chuyện của trợ lý</span>
                    <span className="text-[11px] text-muted-foreground">
                      Dùng chung mô hình đang trả lời
                    </span>
                  </span>
                </SelectItem>
                {chatModels.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    <ModelOption item={item} />
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field>
            <FieldLabel className="text-xs font-medium">
              Giới hạn kiểm chứng
            </FieldLabel>
            <Input
              type="number"
              min={1}
              value={form.verificationMaxOutputTokens}
              onChange={(event) =>
                onChange({
                  verificationMaxOutputTokens: event.target.value,
                })
              }
              placeholder="Tự động"
              className="h-9 bg-background text-xs"
              disabled={disabled}
            />
            <FieldDescription>
              Giới hạn token đầu ra riêng cho bước kiểm chứng.
            </FieldDescription>
          </Field>
        </div>
      )}
    </div>
  );
}

export function AssistantAdvancedFields({
  form,
  onChange,
  chatModels,
  rerankModels,
  disabled,
}: {
  form: RagPolicyFormState;
  onChange: (patch: Partial<RagPolicyFormState>) => void;
  chatModels: CatalogItem[];
  rerankModels: CatalogItem[];
  disabled?: boolean;
}) {
  return (
    <div className="space-y-5">
      <section className="space-y-3">
        <div>
          <h3 className="text-xs font-semibold text-foreground">Truy xuất</h3>
          <p className="text-[11px] text-muted-foreground">
            Cách hệ thống tìm và xếp hạng đoạn trích dẫn trong kho tri thức.
          </p>
        </div>
        <RetrievalFields
          form={form}
          onChange={onChange}
          rerankModels={rerankModels}
          disabled={disabled}
        />
      </section>

      <section className="space-y-3 border-t border-border/60 pt-4">
        <div>
          <h3 className="text-xs font-semibold text-foreground">
            Ngữ cảnh trả lời
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Lượng ngữ cảnh lân cận và giới hạn bằng chứng gửi cho mô hình.
          </p>
        </div>
        <ContextFields form={form} onChange={onChange} disabled={disabled} />
      </section>

      <section className="space-y-3 border-t border-border/60 pt-4">
        <div>
          <h3 className="text-xs font-semibold text-foreground">
            Phạm vi dữ kiện
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Chỉ tài liệu đã gắn metadata khớp bộ lọc mới được dùng.
          </p>
        </div>
        <MetadataScopeFields
          form={form}
          onChange={onChange}
          disabled={disabled}
        />
      </section>

      <section className="space-y-3 border-t border-border/60 pt-4">
        <div>
          <h3 className="text-xs font-semibold text-foreground">
            Kiểm chứng câu trả lời
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Đối chiếu câu trả lời với dẫn chứng bằng một mô hình ngôn ngữ.
          </p>
        </div>
        <VerificationFields
          form={form}
          onChange={onChange}
          chatModels={chatModels}
          disabled={disabled}
        />
      </section>
    </div>
  );
}
