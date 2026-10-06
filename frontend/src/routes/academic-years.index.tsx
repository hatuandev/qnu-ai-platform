import { createFileRoute } from "@tanstack/react-router";
import { AlertTriangle, Plus } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import { AcademicYearFormDialog } from "@/features/academic-years/academic-year-form-dialog";
import { AcademicYearsTable } from "@/features/academic-years/academic-years-table";
import {
  useAcademicYearsQuery,
  useDeactivateAcademicYear,
  useDeleteAcademicYear,
} from "@/features/academic-years/api";
import type { AcademicYear } from "@/features/academic-years/types";
import { useRbac } from "@/rbac/context";

const searchSchema = z.object({
  q: z.union([z.string(), z.number()]).catch(""),
  isCurrent: z.enum(["current", "archived"]).optional().catch(undefined),
  page: z.coerce.number().int().min(1).catch(1),
  pageSize: z.coerce
    .number()
    .int()
    .refine((value) => [10, 20, 50].includes(value))
    .catch(10),
});
export const Route = createFileRoute("/academic-years/")({
  validateSearch: (search) => searchSchema.parse(search),
  component: AcademicYearsPage,
});
function AcademicYearsPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { can } = useRbac();
  const [formState, setFormState] = useState<AcademicYear | null | "create">();
  const [pendingDeactivate, setPendingDeactivate] =
    useState<AcademicYear | null>(null);
  const [pendingDelete, setPendingDelete] = useState<AcademicYear | null>(null);
  const deactivate = useDeactivateAcademicYear();
  const deleteAcademicYear = useDeleteAcademicYear();
  const params = useMemo(
    () => ({
      searchCodeOrName: String(search.q).trim() || undefined,
      isCurrent:
        search.isCurrent === undefined
          ? undefined
          : search.isCurrent === "current",
      page: search.page,
      pageSize: search.pageSize,
    }),
    [search.isCurrent, search.page, search.pageSize, search.q],
  );
  const query = useAcademicYearsQuery(params);
  const updateSearch = useCallback(
    (changes: Partial<typeof search>) =>
      void navigate({ search: (previous) => ({ ...previous, ...changes }) }),
    [navigate],
  );

  if (!can("ktx.academic_years.view")) return <AccessDenied />;

  const isPending = deleteAcademicYear.isPending;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Học vụ / Cấu hình"
        title="Năm học"
        description="Quản lý khoảng thời gian năm học và năm học hiện tại của hệ thống."
        actions={
          can("ktx.academic_years.create") ? (
            <Button className="gap-2" onClick={() => setFormState("create")}>
              <Plus className="size-4" />
              Thêm năm học
            </Button>
          ) : null
        }
      />
      <AcademicYearsTable
        data={query.data?.items ?? []}
        total={query.data?.total ?? 0}
        totalPages={query.data?.totalPages ?? 1}
        page={search.page}
        pageSize={search.pageSize}
        isLoading={query.isLoading}
        isError={query.isError}
        errorMessage={
          query.error instanceof Error ? query.error.message : undefined
        }
        hasAcademicYears={(query.data?.total ?? 0) > 0}
        hasActiveFilters={Boolean(search.q || search.isCurrent)}
        query={String(search.q)}
        isCurrent={params.isCurrent}
        canUpdate={can("ktx.academic_years.update")}
        canDeactivate={can("ktx.academic_years.deactivate")}
        canDelete={can("ktx.academic_years.deactivate")}
        onRetry={() => void query.refetch()}
        onQueryChange={(q) => updateSearch({ q, page: 1 })}
        onCurrentChange={(isCurrent) =>
          updateSearch({
            isCurrent:
              isCurrent === undefined
                ? undefined
                : isCurrent
                  ? "current"
                  : "archived",
            page: 1,
          })
        }
        onResetFilters={() =>
          updateSearch({ q: "", isCurrent: undefined, page: 1 })
        }
        onPageChange={(page) => updateSearch({ page })}
        onPageSizeChange={(pageSize) => updateSearch({ pageSize, page: 1 })}
        onView={(year) =>
          void navigate({
            to: "/academic-years/$academicYearId",
            params: { academicYearId: year.id },
          })
        }
        onEdit={setFormState}
        onDeactivate={setPendingDeactivate}
        onDelete={setPendingDelete}
      />
      <AcademicYearFormDialog
        key={`${formState === "create" ? "create" : (formState?.id ?? "closed")}`}
        open={Boolean(formState)}
        onOpenChange={(open) => {
          if (!open) setFormState(undefined);
        }}
        academicYear={formState === "create" ? null : formState}
      />

      <ConfirmDialog
        open={Boolean(pendingDeactivate)}
        onOpenChange={(open) => {
          if (!open && !deactivate.isPending) setPendingDeactivate(null);
        }}
        title="Ngừng kích hoạt năm học?"
        description={
          pendingDeactivate
            ? `Năm học “${pendingDeactivate.name}” (${pendingDeactivate.code}) sẽ chuyển sang trạng thái đã lưu trữ (không còn là năm học hiện tại). Thao tác này sẽ bị chặn nếu có đợt đăng ký đang mở hoặc ở trạng thái nháp.`
            : ""
        }
        confirmLabel="Lưu trữ năm học"
        isLoading={deactivate.isPending}
        onConfirm={() => {
          if (!pendingDeactivate) return;
          void deactivate
            .mutateAsync(pendingDeactivate.id)
            .then(() => {
              setPendingDeactivate(null);
              toast.success("Đã ngừng kích hoạt năm học thành công.");
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể ngừng kích hoạt năm học.",
              ),
            );
        }}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => {
          if (!open && !isPending) setPendingDelete(null);
        }}
        title="Xác nhận xóa năm học?"
        description={
          pendingDelete ? (
            pendingDelete.registrationPeriodCount > 0 ? (
              <div className="space-y-3 pt-1">
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-destructive">
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <AlertTriangle className="size-4 shrink-0 text-destructive" />
                    <span>Cảnh báo xóa năm học và dữ liệu liên quan</span>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-destructive/90">
                    Hành động xóa năm học{" "}
                    <strong>
                      “{pendingDelete.name}” ({pendingDelete.code})
                    </strong>{" "}
                    sẽ đồng thời{" "}
                    <strong>xóa toàn bộ các đợt đăng ký và các mức phí</strong>{" "}
                    trực thuộc năm học này!
                  </p>
                </div>

                <div className="rounded-md border bg-muted/40 p-3 text-xs space-y-1.5">
                  <p className="font-medium text-foreground">
                    Dữ liệu sẽ bị xóa đồng thời:
                  </p>
                  <ul className="list-disc list-inside space-y-0.5 text-muted-foreground ml-1">
                    <li>
                      <strong>
                        {pendingDelete.registrationPeriodCount} đợt đăng ký
                      </strong>{" "}
                      (kèm cấu hình quy tắc xếp phòng)
                    </li>
                    <li>
                      Các cấu hình <strong>Mức phí</strong> thiết lập cho năm
                      học này
                    </li>
                  </ul>
                </div>

                <p className="text-xs text-muted-foreground italic">
                  * Lưu ý: Hệ thống sẽ từ chối nếu có đợt đăng ký đã có sinh
                  viên nộp hồ sơ hoặc mức phí đã phát sinh hóa đơn thanh toán.
                </p>
              </div>
            ) : (
              `Bạn có chắc chắn muốn xóa năm học “${pendingDelete.name}” (${pendingDelete.code}) không? Hành động này không thể hoàn tác.`
            )
          ) : (
            ""
          )
        }
        confirmLabel={
          pendingDelete && pendingDelete.registrationPeriodCount > 0
            ? "Xác nhận xóa năm học và dữ liệu liên quan"
            : "Xóa năm học"
        }
        confirmVariant="destructive"
        isLoading={isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          void deleteAcademicYear
            .mutateAsync(pendingDelete.id)
            .then(() => {
              setPendingDelete(null);
              toast.success(
                "Đã xóa năm học và các thông tin liên quan thành công.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể xóa năm học.",
              ),
            );
        }}
      />
    </div>
  );
}
