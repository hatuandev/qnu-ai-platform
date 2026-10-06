import { Link } from "@tanstack/react-router";
import { ArrowLeft, Pencil, Power, RefreshCw } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AcademicYearFormDialog } from "@/features/academic-years/academic-year-form-dialog";
import {
  useAcademicYearQuery,
  useDeactivateAcademicYear,
} from "@/features/academic-years/api";
import { formatDateValue } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

function date(value: string) {
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}
export function AcademicYearDetail({ id }: { id: string }) {
  const { can } = useRbac();
  const query = useAcademicYearQuery(id);
  const deactivate = useDeactivateAcademicYear();
  const [formOpen, setFormOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  if (!can("ktx.academic_years.view")) return <AccessDenied />;
  if (query.isLoading)
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-12 w-72" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      </div>
    );
  if (query.isError || !query.data)
    return (
      <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-card text-center">
        <p className="font-medium">Không thể tải năm học</p>
        <p className="max-w-md text-sm text-muted-foreground">
          {query.error instanceof Error
            ? query.error.message
            : "Năm học không tồn tại hoặc bạn không có quyền truy cập."}
        </p>
        <Button variant="outline" onClick={() => void query.refetch()}>
          <RefreshCw />
          Thử lại
        </Button>
      </div>
    );
  const year = query.data;
  return (
    <div className="space-y-6">
      <Link
        to="/academic-years"
        search={{ q: "", isCurrent: undefined, page: 1, pageSize: 10 }}
        className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" />
        Quay lại danh sách năm học
      </Link>
      <PageHeader
        eyebrow="Học vụ / Năm học"
        title={year.name}
        description={`Mã năm học ${year.code}.`}
        actions={
          <div className="flex flex-wrap gap-2">
            {can("ktx.academic_years.update") ? (
              <Button variant="outline" onClick={() => setFormOpen(true)}>
                <Pencil />
                Chỉnh sửa
              </Button>
            ) : null}
            {can("ktx.academic_years.deactivate") && year.isCurrent ? (
              <Button variant="outline" onClick={() => setConfirmOpen(true)}>
                <Power />
                Ngừng năm học
              </Button>
            ) : null}
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Thời gian
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm">
            {date(year.startDate)} — {date(year.endDate)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Trạng thái
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant={year.isCurrent ? "success" : "secondary"}>
              {year.isCurrent ? "Hiện tại" : "Đã lưu trữ"}
            </Badge>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Thông tin hệ thống</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
          <div>
            <p className="text-muted-foreground">Số kỳ đăng ký</p>
            <p className="tabular-nums">{year.registrationPeriodCount}</p>
          </div>
          {year.created ? (
            <div>
              <p className="text-muted-foreground">Ngày tạo</p>
              <p>{formatDateValue(year.created)}</p>
            </div>
          ) : null}
          {year.lastModified ? (
            <div>
              <p className="text-muted-foreground">Cập nhật gần nhất</p>
              <p>{formatDateValue(year.lastModified)}</p>
            </div>
          ) : null}
        </CardContent>
      </Card>
      <AcademicYearFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        academicYear={year}
      />
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setConfirmOpen(false);
        }}
        title="Ngừng năm học?"
        description={
          year.registrationPeriodCount
            ? `Năm học đang có ${year.registrationPeriodCount} kỳ đăng ký. Máy chủ có thể từ chối thao tác này nếu còn kỳ đang mở.`
            : `Ngừng năm học “${year.name}”?`
        }
        confirmLabel="Ngừng năm học"
        isLoading={deactivate.isPending}
        onConfirm={() => {
          void deactivate
            .mutateAsync(year.id)
            .then(() => {
              setConfirmOpen(false);
              toast.success("Đã ngừng năm học.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng năm học.",
              ),
            );
        }}
      />
    </div>
  );
}
