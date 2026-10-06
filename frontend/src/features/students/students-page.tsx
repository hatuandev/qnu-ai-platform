import { useNavigate } from "@tanstack/react-router";
import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError } from "@/app/api/client";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Button } from "@/components/ui/button";
import {
  useDeactivateStudent,
  useStudentsQuery,
} from "@/features/students/api";
import { StudentFormDialog } from "@/features/students/student-form-dialog";
import { StudentsTable } from "@/features/students/students-table";
import type { Student, StudentStatus } from "@/features/students/types";
import { useRbac } from "@/rbac/context";

export type StudentsSearch = {
  q: string;
  faculty: string;
  status?: StudentStatus;
  page: number;
  pageSize: number;
  create: boolean;
};

export function StudentsPage({
  search,
  onSearchChange,
}: {
  search: StudentsSearch;
  onSearchChange: (changes: Partial<StudentsSearch>) => void;
}) {
  const { can } = useRbac();
  const navigate = useNavigate({ from: "/students/" });
  const query = useStudentsQuery({
    search: search.q || undefined,
    faculty: search.faculty || undefined,
    status: search.status,
    page: search.page,
    pageSize: search.pageSize,
  });
  const deactivate = useDeactivateStudent();
  const [editing, setEditing] = useState<Student | null>(null);
  const [deactivating, setDeactivating] = useState<Student | null>(null);
  const dialogOpen = search.create || Boolean(editing);

  const closeForm = (open: boolean) => {
    if (open) return;
    setEditing(null);
    onSearchChange({ create: false });
  };

  const resetFilters = () =>
    onSearchChange({ q: "", faculty: "", status: undefined, page: 1 });

  const confirmDeactivate = () => {
    if (!deactivating) return;
    void deactivate
      .mutateAsync(deactivating.id)
      .then(() => {
        toast.success("Đã ngừng hồ sơ sinh viên.");
        setDeactivating(null);
      })
      .catch((error: unknown) => {
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể ngừng hồ sơ sinh viên.",
        );
      });
  };

  return (
    <div className="space-y-5 pb-10">
      <PageHeader
        eyebrow="Ký túc xá / Danh mục sinh viên"
        title="Sinh viên"
        description="Quản lý hồ sơ sinh viên và trạng thái học tập."
        actions={
          can("ktx.students.create") ? (
            <Button onClick={() => onSearchChange({ create: true })}>
              <Plus className="size-4 mr-1.5" />
              Thêm sinh viên
            </Button>
          ) : null
        }
      />

      <StudentsTable
        data={query.data?.items ?? []}
        query={search.q}
        faculty={search.faculty}
        status={search.status}
        page={search.page}
        pageSize={search.pageSize}
        total={query.data?.total ?? 0}
        totalPages={query.data?.totalPages ?? 1}
        isLoading={query.isLoading}
        isError={query.isError}
        errorMessage={
          query.error instanceof Error ? query.error.message : undefined
        }
        hasStudents={(query.data?.total ?? 0) > 0}
        hasFilters={Boolean(search.q || search.faculty || search.status)}
        canUpdate={can("ktx.students.update")}
        canDeactivate={can("ktx.students.deactivate")}
        onRetry={() => void query.refetch()}
        onQueryChange={(value) => onSearchChange({ q: value, page: 1 })}
        onFacultyChange={(value) => onSearchChange({ faculty: value, page: 1 })}
        onStatusChange={(value) => onSearchChange({ status: value, page: 1 })}
        onReset={resetFilters}
        onPageChange={(page) => onSearchChange({ page })}
        onPageSizeChange={(pageSize) => onSearchChange({ page: 1, pageSize })}
        onView={(student) => {
          void navigate({
            to: "/students/$studentId",
            params: { studentId: student.id },
          });
        }}
        onEdit={(student) => {
          setEditing(student);
        }}
        onDeactivate={setDeactivating}
      />

      <StudentFormDialog
        key={`${editing?.id ?? "new"}-${dialogOpen ? "open" : "closed"}`}
        open={dialogOpen}
        onOpenChange={closeForm}
        student={editing}
      />

      <ConfirmDialog
        open={Boolean(deactivating)}
        onOpenChange={(open) => {
          if (!open) setDeactivating(null);
        }}
        title="Ngừng hồ sơ sinh viên?"
        description={`Hồ sơ của ${deactivating?.fullName ?? "sinh viên này"} sẽ không còn xuất hiện trong danh sách đang hoạt động.`}
        confirmLabel="Ngừng hồ sơ"
        isLoading={deactivate.isPending}
        onConfirm={confirmDeactivate}
      />
    </div>
  );
}
