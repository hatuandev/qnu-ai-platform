import { AlertCircle, Info } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  type BudgetSource,
  CAPABILITY_LABELS,
  type Capability,
  type CapacityBasis,
  type CapacityStatus,
  type CatalogItem,
  type OperationalBudget,
  type OperationalBudgetStatus,
  type Provider,
} from "@/features/modelops/types";

const LABELS: Record<CapacityStatus, string> = {
  unknown: "Chưa công bố",
  configured: "Đã khai báo",
  stale: "Cần cập nhật",
};

const VARIANTS = {
  unknown: "secondary",
  configured: "success",
  stale: "warning",
} as const;

export const BUDGET_STATUS_LABELS: Record<
  OperationalBudgetStatus | "missing_info",
  string
> = {
  declared: "Dùng thông số đã khai báo",
  provisional: "Đang dùng ngân sách tạm tính",
  blocked: "Cần bổ sung thông tin",
  missing_info: "Chưa có thông tin",
};

export const BUDGET_SOURCE_LABELS: Record<BudgetSource, string> = {
  server_reported: "Server công bố",
  operator_configured: "Khai báo thủ công",
  application_default: "Mặc định ứng dụng",
};

const BUDGET_STATUS_VARIANTS: Record<
  OperationalBudgetStatus | "missing_info",
  "success" | "secondary" | "warning" | "outline"
> = {
  declared: "success",
  provisional: "secondary",
  blocked: "warning",
  missing_info: "outline",
};

/**
 * `unknown` never means "unlimited": it means the operator or server has not
 * published a limit. Server-reported or operator-configured values are never
 * labelled "Đã kiểm chứng" (verified).
 */
export function CapacityBadge({
  status,
  basis,
}: {
  status: CapacityStatus;
  basis?: CapacityBasis | null;
}) {
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>
      {basis ? (
        <Badge variant="outline" className="text-[11px] font-normal">
          {BUDGET_SOURCE_LABELS[basis]}
        </Badge>
      ) : null}
    </span>
  );
}

export function capacityLabel(status: CapacityStatus): string {
  return LABELS[status];
}

export function capacityBasisLabel(
  basis: CapacityBasis | BudgetSource | null | undefined,
): string {
  if (!basis) return "Chưa công bố";
  return BUDGET_SOURCE_LABELS[basis];
}

/**
 * Formats a token limit value in tokens. Unknown/null values are always shown
 * as "Chưa công bố", never 0 or unlimited.
 */
export function formatTokenLimitValue(
  value: number | null | undefined,
): string {
  if (value === null || value === undefined) {
    return "Chưa công bố";
  }
  return `${value.toLocaleString("vi-VN")} token`;
}

export function describeBudgetReason(
  reasonCode: string | null | undefined,
  capability?: Capability,
  model?: Partial<
    Pick<
      Provider,
      | "capacity_status"
      | "embedding_dimension"
      | "embedding_dimension_status"
      | "token_limits"
    >
  >,
): string {
  switch (reasonCode) {
    case "model_token_limits_stale":
      return "Thông số giới hạn đã cũ do thay đổi endpoint hoặc model; cần lấy lại từ server hoặc cập nhật lại.";
    case "model_input_budget_unknown":
      return "Chưa có thông số giới hạn trang ảnh OCR (ocr_page_input) và giới hạn token của model.";
    case "embedding_dimension_unknown":
      return "Cần khai báo hoặc đồng bộ số chiều vector (embedding_dimension) đúng của model.";
    default:
      if (
        capability === "embedding" &&
        model?.embedding_dimension_status === "stale"
      ) {
        return "Số chiều vector (embedding_dimension) đã cũ do đổi cấu hình; cần kiểm tra hoặc cập nhật lại.";
      }
      if (capability === "embedding" && model?.embedding_dimension === null) {
        return "Cần khai báo hoặc đồng bộ số chiều vector (embedding_dimension) đúng của model.";
      }
      if (capability === "ocr") {
        return "Chưa có thông số giới hạn trang ảnh OCR (ocr_page_input) cho model này.";
      }
      return reasonCode
        ? `Cần bổ sung thông số cấu hình cho model (${reasonCode}).`
        : "Cần bổ sung thông số cấu hình trước khi sử dụng chức năng này.";
  }
}

export type ResolvedCapabilityBudget = {
  status: OperationalBudgetStatus | "missing_info";
  isBlocked: boolean;
  label: string;
  basisLabel: string | null;
  reasonCode: string | null;
  reason: string | null;
  budget: OperationalBudget | null;
};

function summarizeSources(
  sources: Partial<Record<string, BudgetSource>> | undefined,
): string | null {
  if (!sources) return null;
  const unique = Array.from(
    new Set(
      Object.values(sources).filter((v): v is BudgetSource => Boolean(v)),
    ),
  );
  if (unique.length === 0) return null;
  return unique.map((item) => BUDGET_SOURCE_LABELS[item]).join(" + ");
}

export function resolveCapabilityBudgetState(
  model: Partial<Provider & CatalogItem> | null | undefined,
  capability: Capability,
): ResolvedCapabilityBudget {
  if (!model) {
    return {
      status: "missing_info",
      isBlocked: false,
      label: BUDGET_STATUS_LABELS.missing_info,
      basisLabel: null,
      reasonCode: null,
      reason: null,
      budget: null,
    };
  }

  const budget = model.operational_budgets?.[capability] ?? null;

  if (budget) {
    if (budget.status === "blocked") {
      const reasonCode =
        budget.reason_code ??
        (model.capacity_status === "stale"
          ? "model_token_limits_stale"
          : capability === "ocr"
            ? "model_input_budget_unknown"
            : null);
      return {
        status: "blocked",
        isBlocked: true,
        label: BUDGET_STATUS_LABELS.blocked,
        basisLabel: summarizeSources(budget.sources),
        reasonCode,
        reason: describeBudgetReason(reasonCode, capability, model),
        budget,
      };
    }

    if (capability === "embedding") {
      if (model.embedding_dimension_status === "stale") {
        return {
          status: "blocked",
          isBlocked: true,
          label: BUDGET_STATUS_LABELS.blocked,
          basisLabel: summarizeSources(budget.sources),
          reasonCode: "model_token_limits_stale",
          reason: describeBudgetReason(
            "model_token_limits_stale",
            capability,
            model,
          ),
          budget,
        };
      }
      if (model.embedding_dimension === null) {
        return {
          status: "blocked",
          isBlocked: true,
          label: BUDGET_STATUS_LABELS.blocked,
          basisLabel: summarizeSources(budget.sources),
          reasonCode: "embedding_dimension_unknown",
          reason: describeBudgetReason(
            "embedding_dimension_unknown",
            capability,
            model,
          ),
          budget,
        };
      }
    }

    return {
      status: budget.status,
      isBlocked: false,
      label: BUDGET_STATUS_LABELS[budget.status],
      basisLabel:
        summarizeSources(budget.sources) ??
        (model.capacity_basis
          ? BUDGET_SOURCE_LABELS[model.capacity_basis]
          : null),
      reasonCode: budget.reason_code,
      reason: null,
      budget,
    };
  }

  // Fallback when server response does not include `operational_budgets` yet:
  // Never fabricate default numbers on the frontend.
  if (
    model.capacity_status === "stale" ||
    (capability === "embedding" && model.embedding_dimension_status === "stale")
  ) {
    return {
      status: "blocked",
      isBlocked: true,
      label: BUDGET_STATUS_LABELS.blocked,
      basisLabel: model.capacity_basis
        ? BUDGET_SOURCE_LABELS[model.capacity_basis]
        : null,
      reasonCode: "model_token_limits_stale",
      reason: describeBudgetReason(
        "model_token_limits_stale",
        capability,
        model,
      ),
      budget: null,
    };
  }

  if (
    capability === "ocr" &&
    model.token_limits !== undefined &&
    model.token_limits?.ocr_page_input == null
  ) {
    return {
      status: "blocked",
      isBlocked: true,
      label: BUDGET_STATUS_LABELS.blocked,
      basisLabel: model.capacity_basis
        ? BUDGET_SOURCE_LABELS[model.capacity_basis]
        : null,
      reasonCode: "model_input_budget_unknown",
      reason: describeBudgetReason(
        "model_input_budget_unknown",
        capability,
        model,
      ),
      budget: null,
    };
  }

  if (
    capability === "embedding" &&
    model.embedding_dimension !== undefined &&
    model.embedding_dimension === null
  ) {
    return {
      status: "blocked",
      isBlocked: true,
      label: BUDGET_STATUS_LABELS.blocked,
      basisLabel: model.capacity_basis
        ? BUDGET_SOURCE_LABELS[model.capacity_basis]
        : null,
      reasonCode: "embedding_dimension_unknown",
      reason: describeBudgetReason(
        "embedding_dimension_unknown",
        capability,
        model,
      ),
      budget: null,
    };
  }

  return {
    status: "missing_info",
    isBlocked: false,
    label: BUDGET_STATUS_LABELS.missing_info,
    basisLabel: model.capacity_basis
      ? BUDGET_SOURCE_LABELS[model.capacity_basis]
      : null,
    reasonCode: null,
    reason: null,
    budget: null,
  };
}

export function OperationalBudgetBadge({
  model,
  capability,
  showCapability = false,
  showBasis = true,
}: {
  model: Partial<Provider & CatalogItem>;
  capability: Capability;
  showCapability?: boolean;
  showBasis?: boolean;
}) {
  const resolved = resolveCapabilityBudgetState(model, capability);
  const capPrefix = showCapability ? `${CAPABILITY_LABELS[capability]}: ` : "";
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <Badge
        variant={BUDGET_STATUS_VARIANTS[resolved.status]}
        className="text-[11px] font-normal"
      >
        {capPrefix}
        {resolved.label}
      </Badge>
      {showBasis && resolved.basisLabel ? (
        <Badge variant="outline" className="text-[10px] font-normal">
          {resolved.basisLabel}
        </Badge>
      ) : null}
    </span>
  );
}

export function ProviderOperationalBudgetsSummary({
  provider,
  showBasis = false,
  compact = false,
}: {
  provider: Partial<Provider>;
  showBasis?: boolean;
  compact?: boolean;
}) {
  const caps = (provider.capabilities ?? []) as Capability[];
  if (caps.length === 0) {
    return (
      <Badge variant="outline" className="text-[11px] font-normal">
        {BUDGET_STATUS_LABELS.missing_info}
      </Badge>
    );
  }
  const showCapName = !compact && caps.length > 1;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {caps.map((cap) => (
        <OperationalBudgetBadge
          key={cap}
          model={provider}
          capability={cap}
          showCapability={showCapName}
          showBasis={showBasis}
        />
      ))}
    </div>
  );
}

export function ConsumerModelBudgetNotice({
  model,
  capability,
}: {
  model: Partial<Provider & CatalogItem> | null | undefined;
  capability: Capability;
}) {
  if (!model) return null;
  const resolved = resolveCapabilityBudgetState(model, capability);

  if (resolved.isBlocked) {
    return (
      <Alert variant="warning" className="py-2.5 px-3 text-xs">
        <AlertCircle className="size-4 text-warning" />
        <AlertTitle className="text-xs font-semibold">
          {BUDGET_STATUS_LABELS.blocked} ({CAPABILITY_LABELS[capability]})
        </AlertTitle>
        <AlertDescription className="text-xs space-y-1">
          <p>{resolved.reason}</p>
          {resolved.reasonCode ? (
            <p className="font-mono text-[11px] text-muted-foreground">
              Mã lý do: {resolved.reasonCode}
            </p>
          ) : null}
        </AlertDescription>
      </Alert>
    );
  }

  if (resolved.status === "provisional") {
    return (
      <div
        role="status"
        className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground pt-1"
      >
        <Info className="size-3.5 text-primary shrink-0" />
        <span>{BUDGET_STATUS_LABELS.provisional}</span>
        {resolved.basisLabel ? (
          <Badge variant="outline" className="text-[10px] font-normal">
            {resolved.basisLabel}
          </Badge>
        ) : null}
      </div>
    );
  }

  if (resolved.status === "declared") {
    return (
      <div
        role="status"
        className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground pt-1"
      >
        <span>{BUDGET_STATUS_LABELS.declared}</span>
        {resolved.basisLabel ? (
          <Badge variant="outline" className="text-[10px] font-normal">
            {resolved.basisLabel}
          </Badge>
        ) : null}
      </div>
    );
  }

  return null;
}

export type DiagnosticFailureCategory =
  | "quota_rate_limit"
  | "token_budget"
  | "malformed_response"
  | "timeout"
  | "auth"
  | "general";

export function describeDiagnosticFailure(input: {
  code?: string | null;
  http_status?: number | null;
  httpStatus?: number | null;
  detail?: string | null;
}): {
  category: DiagnosticFailureCategory;
  title: string;
  guidance: string;
  message: string;
  detail: string;
} {
  const code = (input.code ?? "").toLowerCase();
  const status = input.http_status ?? input.httpStatus ?? null;
  const rawDetail =
    input.detail?.trim() || "Máy chủ model báo lỗi khi thực hiện yêu cầu.";

  if (
    status === 429 ||
    code.includes("quota") ||
    code.includes("rate_limit") ||
    code === "provider_rate_limited"
  ) {
    const guidance =
      "Nhà cung cấp hoặc workspace đang chạm giới hạn tần suất/hạn mức token. Kiểm tra hạn mức hoặc thử lại sau thời gian chờ.";
    return {
      category: "quota_rate_limit",
      title: "Giới hạn tần suất hoặc vượt hạn mức (Quota / HTTP 429)",
      guidance,
      message: guidance,
      detail: rawDetail,
    };
  }

  if (
    code.includes("token_limit") ||
    code.includes("input_limit") ||
    code.includes("output_limit") ||
    code.includes("context_limit") ||
    code.includes("input_budget") ||
    code.includes("capacity")
  ) {
    const guidance =
      "Yêu cầu vượt quá ngân sách token đang áp dụng hoặc model cần bổ sung thông số giới hạn trước khi chạy.";
    return {
      category: "token_budget",
      title: "Vượt ngân sách token hoặc thiếu thông số giới hạn",
      guidance,
      message: guidance,
      detail: rawDetail,
    };
  }

  if (
    code.includes("malformed") ||
    code.includes("invalid_response") ||
    code.includes("schema") ||
    code.includes("json")
  ) {
    const guidance =
      "Máy chủ trả về dữ liệu không khớp hợp đồng giao thức (JSON/schema hoặc cấu trúc phản hồi không hợp lệ).";
    return {
      category: "malformed_response",
      title: "Phản hồi từ máy chủ không đúng định dạng (Malformed response)",
      guidance,
      message: guidance,
      detail: rawDetail,
    };
  }

  if (status === 408 || status === 504 || code.includes("timeout")) {
    const guidance =
      "Máy chủ model không phản hồi trong thời gian giới hạn. Kiểm tra kết nối mạng, trạng thái model hoặc thời gian chờ (timeout).";
    return {
      category: "timeout",
      title: "Quá thời gian chờ phản hồi (Timeout)",
      guidance,
      message: guidance,
      detail: rawDetail,
    };
  }

  if (status === 401 || status === 403 || code.includes("auth")) {
    const guidance =
      "Máy chủ từ chối API Key hoặc quyền truy cập model. Kiểm tra lại khóa API và địa chỉ Base URL.";
    return {
      category: "auth",
      title: "Lỗi xác thực khóa API hoặc quyền truy cập",
      guidance,
      message: guidance,
      detail: rawDetail,
    };
  }

  const guidance = "Máy chủ trả về lỗi trong quá trình kiểm tra.";
  return {
    category: "general",
    title: "Kiểm tra thất bại",
    guidance,
    message: rawDetail,
    detail: rawDetail,
  };
}
