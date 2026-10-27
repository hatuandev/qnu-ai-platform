import { Badge } from "@/components/ui/badge";
import type { CapacityStatus } from "@/features/modelops/types";

const LABELS: Record<CapacityStatus, string> = {
  unknown: "Chưa khai báo",
  configured: "Đã khai báo",
  stale: "Cần khai báo lại",
};

const VARIANTS = {
  unknown: "secondary",
  configured: "success",
  stale: "warning",
} as const;

/**
 * `unknown` never means "unlimited": it means the operator has not declared a
 * limit, so no capacity can be assumed.
 */
export function CapacityBadge({ status }: { status: CapacityStatus }) {
  return <Badge variant={VARIANTS[status]}>{LABELS[status]}</Badge>;
}

export function capacityLabel(status: CapacityStatus): string {
  return LABELS[status];
}
