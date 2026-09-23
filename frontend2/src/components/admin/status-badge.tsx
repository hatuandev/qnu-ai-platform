import { Badge } from "@/components/ui/badge";

type Status =
  | "active"
  | "inactive"
  | "pending"
  | "suspended"
  | "success"
  | "warning";
const map: Record<
  Status,
  {
    label: string;
    variant: "success" | "secondary" | "info" | "destructive" | "warning";
  }
> = {
  active: { label: "Đang hoạt động", variant: "success" },
  inactive: { label: "Không hoạt động", variant: "secondary" },
  pending: { label: "Đang chờ", variant: "info" },
  suspended: { label: "Tạm khóa", variant: "destructive" },
  success: { label: "Thành công", variant: "success" },
  warning: { label: "Cảnh báo", variant: "warning" },
};
export function StatusBadge({ status }: { status: Status }) {
  const item = map[status];
  return <Badge variant={item.variant}>{item.label}</Badge>;
}
