import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAssignmentQuery } from "@/features/assignments/api";
import type { AssignmentStatus } from "@/features/assignments/types";

const labels: Record<AssignmentStatus, string> = {
  selected: "Đang giữ chỗ",
  assigned: "Đã xếp",
  checked_in: "Đã nhận phòng",
  cancelled: "Đã hủy",
};

export function AssignmentDetail({ assignmentId }: { assignmentId: string }) {
  const query = useAssignmentQuery(assignmentId);

  if (query.isLoading) {
    return <div className="h-64 animate-pulse rounded-lg border bg-card" />;
  }

  if (query.isError || !query.data) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        Không thể tải thông tin phân phòng.
        <br />
        <Button
          className="mt-3"
          variant="outline"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const item = query.data;
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ký túc xá / Xếp phòng"
        title={item.applicationCode}
        description={`${item.studentName} · ${labels[item.status]}`}
        actions={
          <Button variant="outline" onClick={() => window.history.back()}>
            Quay lại
          </Button>
        }
      />
      <section className="grid gap-4 rounded-lg border bg-card p-5 sm:grid-cols-2 lg:grid-cols-3">
        <Info
          label="Sinh viên"
          value={`${item.studentName} (${item.studentCode})`}
        />
        <Info label="Tòa nhà" value={item.buildingCode} />
        <Info label="Phòng" value={`${item.roomCode} · ${item.roomName}`} />
        <Info
          label="Trạng thái"
          value={labels[item.status]}
          badge={item.status !== "cancelled"}
        />
        <Info
          label="Ngày xếp"
          value={new Date(item.assignedAt).toLocaleString("vi-VN")}
        />
        <Info label="Ghi chú" value={item.note} />
      </section>
    </div>
  );
}

function Info({
  label,
  value,
  badge,
}: {
  label: string;
  value?: string | null;
  badge?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      {badge ? (
        <Badge className="mt-1">{value || "—"}</Badge>
      ) : (
        <p className="mt-1 text-sm">{value || "—"}</p>
      )}
    </div>
  );
}
