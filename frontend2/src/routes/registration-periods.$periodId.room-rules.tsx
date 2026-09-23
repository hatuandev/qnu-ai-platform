import { createFileRoute } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useRegistrationPeriodQuery } from "@/features/registration-periods/api";
import { RegistrationPeriodRoomRulesDialog } from "@/features/registration-periods/room-rules-dialog";
import { useRbac } from "@/rbac/context";

export const Route = createFileRoute(
  "/registration-periods/$periodId/room-rules",
)({
  component: RegistrationPeriodRoomRulesRoute,
});

function RegistrationPeriodRoomRulesRoute() {
  const { periodId } = Route.useParams();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const query = useRegistrationPeriodQuery(periodId);
  const goBack = () =>
    void navigate({
      to: "/registration-periods",
      search: { q: "", page: 1, pageSize: 10 },
    });

  if (!can("ktx.registration_periods.view")) return <AccessDenied />;

  if (query.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="HỌC VỤ / CẤU HÌNH"
          title="Phân bổ phòng đợt nội trú"
          description="Cấu hình phạm vi phòng và chính sách giới tính cho đợt đăng ký."
        />
        <div className="rounded-xl border bg-card p-12 text-center text-xs text-muted-foreground shadow-2xs">
          Đang tải thông tin đợt đăng ký...
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="HỌC VỤ / CẤU HÌNH"
          title="Phân bổ phòng đợt nội trú"
          description="Cấu hình phạm vi phòng và chính sách giới tính cho đợt đăng ký."
          actions={
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs"
              onClick={goBack}
            >
              <ArrowLeft className="size-3.5" />
              <span>Quay lại</span>
            </Button>
          }
        />
        <Alert variant="destructive" className="rounded-xl shadow-2xs">
          <AlertTitle>Không thể tải đợt đăng ký</AlertTitle>
          <AlertDescription className="text-xs mt-1">
            {query.error instanceof Error
              ? query.error.message
              : "Đợt đăng ký không tồn tại hoặc đã bị xóa."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const period = query.data;
  const canManageRooms =
    period.status === "closed" || period.status === "archived";
  const canEdit =
    period.status === "closed" && can("ktx.registration_periods.update");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="HỌC VỤ / CẤU HÌNH"
        title="Phân bổ phòng đợt nội trú"
        description="Chọn các phòng được mở trong đợt và thiết lập chính sách giới tính Nam/Nữ theo tầng hoặc theo phòng."
        actions={
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-1.5 text-xs font-medium"
            onClick={goBack}
          >
            <ArrowLeft className="size-3.5" />
            <span>Quay lại</span>
          </Button>
        }
      />

      {canManageRooms ? (
        <RegistrationPeriodRoomRulesDialog
          layout="page"
          period={period}
          canEdit={canEdit}
          onClose={goBack}
        />
      ) : (
        <Alert variant="warning" className="rounded-xl shadow-2xs">
          <AlertTitle>Chưa thể phân bổ phòng</AlertTitle>
          <AlertDescription className="text-xs mt-1">
            Chỉ có thể phân bổ phòng sau khi cán bộ đóng đợt nhận hồ sơ. Hãy
            quay lại danh sách đợt để kiểm tra trạng thái và đóng đợt trước.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
