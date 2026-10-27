import { useForm } from "@tanstack/react-form";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, CircleHelp, LoaderCircle, Send } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError } from "@/app/api/client";
import { AccessDenied } from "@/components/admin/access-denied";
import { EmptyState } from "@/components/admin/empty-state";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/admin/field";
import { PageHeader } from "@/components/admin/page-header";
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogDescription,
  ResponsiveDialogFooter,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
} from "@/components/admin/responsive-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  useAddSupportComment,
  useProcessSupportRequest,
  useSupportCommentsQuery,
  useSupportDetailQuery,
  useSupportHistoryQuery,
} from "@/features/support/api";
import type { SupportStatus } from "@/features/support/types";
import { formatDateTime } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

const statuses: SupportStatus[] = ["processing", "resolved", "rejected"];
const statusLabels: Record<SupportStatus, string> = {
  submitted: "Mới gửi",
  processing: "Đang xử lý",
  resolved: "Đã giải quyết",
  rejected: "Từ chối",
  cancelled: "Đã hủy",
};
const requestTypeLabels = {
  change_room: "Đổi phòng",
  extend: "Gia hạn",
  check_out: "Trả phòng",
  other: "Khác",
} as const;

export const Route = createFileRoute("/support/$supportRequestId")({
  component: () => (
    <SupportDetail requestId={Route.useParams().supportRequestId} />
  ),
});

function SupportDetail({ requestId }: { requestId: string }) {
  const navigate = useNavigate({ from: "/support/$supportRequestId" });
  const { can } = useRbac();
  const canView = can("ktx.support.view");
  const query = useSupportDetailQuery(requestId, { enabled: canView });
  const comments = useSupportCommentsQuery(requestId, { enabled: canView });
  const history = useSupportHistoryQuery(requestId, { enabled: canView });
  const [processOpen, setProcessOpen] = useState(false);

  if (!canView) return <AccessDenied />;
  if (query.isLoading) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-2 rounded-lg border text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Đang tải yêu cầu...
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={CircleHelp}
        title="Không thể tải yêu cầu"
        description="Yêu cầu có thể không tồn tại hoặc bạn không có quyền xem."
        action={{
          label: "Quay lại danh sách",
          onClick: () =>
            void navigate({
              to: "/support",
              search: { q: "", page: 1, pageSize: 10 },
            }),
        }}
      />
    );
  }

  const item = query.data;
  const canProcess =
    can("ktx.support.process") &&
    (item.status === "submitted" || item.status === "processing");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Trao đổi / Yêu cầu hỗ trợ"
        title={item.title}
        description={`${item.studentName} · ${statusLabels[item.status]}`}
        actions={
          <Button
            variant="outline"
            onClick={() =>
              void navigate({
                to: "/support",
                search: { q: "", page: 1, pageSize: 10 },
              })
            }
          >
            <ArrowLeft />
            Quay lại
          </Button>
        }
      />

      <section className="rounded-lg border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-4">
          <div>
            <p className="text-sm text-muted-foreground">Trạng thái hiện tại</p>
            <Badge className="mt-2" variant={statusVariant(item.status)}>
              {statusLabels[item.status]}
            </Badge>
          </div>
          {canProcess ? (
            <Button onClick={() => setProcessOpen(true)}>Cập nhật xử lý</Button>
          ) : null}
        </div>
        <dl className="grid gap-x-6 gap-y-4 pt-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <Info
            label="Sinh viên"
            value={`${item.studentName} (${item.studentCode})`}
          />
          <Info
            label="Loại yêu cầu"
            value={requestTypeLabels[item.requestType]}
          />
          <Info
            label="Ngày gửi"
            value={formatDateTime(new Date(item.created))}
          />
          <Info
            label="Cập nhật gần nhất"
            value={formatDateTime(new Date(item.lastModified))}
          />
        </dl>
      </section>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <section className="rounded-lg border bg-card p-5">
            <h2 className="font-semibold">Nội dung yêu cầu</h2>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground/90">
              {item.content}
            </p>
          </section>
          <section className="rounded-lg border bg-card p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold">Trao đổi</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Ghi lại thông tin trao đổi với sinh viên hoặc bộ phận xử lý.
                </p>
              </div>
              <Badge variant="secondary">{item.commentCount} trao đổi</Badge>
            </div>
            <div className="mt-5 space-y-3">
              {comments.isLoading ? (
                <p className="text-sm text-muted-foreground">
                  Đang tải trao đổi...
                </p>
              ) : comments.data?.length ? (
                comments.data.map((entry) => (
                  <article
                    key={entry.id}
                    className="rounded-md border bg-muted/20 p-3"
                  >
                    <p className="whitespace-pre-wrap text-sm leading-6">
                      {entry.comment}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      {entry.createdBy} ·{" "}
                      {formatDateTime(new Date(entry.createdAt))}
                    </p>
                  </article>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">
                  Chưa có trao đổi.
                </p>
              )}
            </div>
            {can("ktx.support.comment") ? (
              <CommentForm requestId={requestId} />
            ) : null}
          </section>
        </div>

        <aside className="rounded-lg border bg-card p-5">
          <h2 className="font-semibold">Lịch sử xử lý</h2>
          <div className="mt-5 space-y-4">
            {history.isLoading ? (
              <p className="text-sm text-muted-foreground">
                Đang tải lịch sử...
              </p>
            ) : history.data?.length ? (
              history.data.map((entry) => (
                <div
                  key={entry.id}
                  className="relative border-l-2 border-border pl-4 text-sm"
                >
                  <span className="absolute -left-[5px] top-1 size-2 rounded-full bg-primary" />
                  <p className="font-medium">
                    {entry.fromStatus
                      ? `${statusLabels[entry.fromStatus]} → `
                      : ""}
                    {statusLabels[entry.toStatus]}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {formatDateTime(new Date(entry.changedAt))}
                    {entry.note ? ` · ${entry.note}` : ""}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-sm text-muted-foreground">
                Chưa có lịch sử xử lý.
              </p>
            )}
          </div>
        </aside>
      </div>

      <ProcessDialog
        open={processOpen}
        onOpenChange={setProcessOpen}
        requestId={requestId}
      />
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 truncate font-medium">{value}</dd>
    </div>
  );
}

function CommentForm({ requestId }: { requestId: string }) {
  const addComment = useAddSupportComment();
  const form = useForm({
    defaultValues: { comment: "" },
    validators: {
      onSubmit: z.object({
        comment: z
          .string()
          .trim()
          .min(1, "Nội dung trao đổi là bắt buộc.")
          .max(2000, "Nội dung tối đa 2.000 ký tự."),
      }),
    },
    onSubmit: async ({ value }) => {
      try {
        await addComment.mutateAsync({
          id: requestId,
          comment: value.comment.trim(),
        });
        form.reset();
        toast.success("Đã thêm trao đổi.");
      } catch (error) {
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể thêm trao đổi.",
        );
      }
    },
  });
  return (
    <form
      className="mt-5 border-t pt-4"
      onSubmit={(event) => {
        event.preventDefault();
        event.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <form.Field name="comment">
        {(field) => {
          const error = field.state.meta.errors[0];
          return (
            <Field>
              <FieldLabel htmlFor="support-comment">Thêm trao đổi</FieldLabel>
              <Textarea
                id="support-comment"
                value={field.state.value}
                onBlur={field.handleBlur}
                onChange={(event) => field.handleChange(event.target.value)}
                aria-invalid={Boolean(error)}
                placeholder="Nhập nội dung trao đổi..."
                className="min-h-24"
                maxLength={2000}
              />
              <FieldDescription>Tối đa 2.000 ký tự.</FieldDescription>
              {error ? <FieldError>{String(error)}</FieldError> : null}
            </Field>
          );
        }}
      </form.Field>
      <form.Subscribe
        selector={(state) => [state.canSubmit, state.isSubmitting]}
      >
        {([canSubmit, isSubmitting]) => (
          <Button
            className="mt-3"
            type="submit"
            disabled={!canSubmit || isSubmitting || addComment.isPending}
          >
            <Send />
            {addComment.isPending ? "Đang gửi..." : "Gửi trao đổi"}
          </Button>
        )}
      </form.Subscribe>
    </form>
  );
}

type ProcessStatus = "processing" | "resolved" | "rejected";
type ProcessFormValues = { newStatus: ProcessStatus; note: string };
const processSchema = z.object({
  newStatus: z.enum(["processing", "resolved", "rejected"]),
  note: z.string().max(2000, "Ghi chú tối đa 2.000 ký tự."),
});

function ProcessDialog({
  open,
  onOpenChange,
  requestId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  requestId: string;
}) {
  const process = useProcessSupportRequest();
  const form = useForm({
    defaultValues: {
      newStatus: "processing" as ProcessStatus,
      note: "",
    } satisfies ProcessFormValues,
    validators: { onSubmit: processSchema },
    onSubmit: async ({ value }) => {
      try {
        await process.mutateAsync({
          id: requestId,
          newStatus: value.newStatus,
          note: value.note.trim() || undefined,
        });
        form.reset();
        onOpenChange(false);
        toast.success("Đã cập nhật yêu cầu.");
      } catch (error) {
        toast.error(
          error instanceof ApiError
            ? error.message
            : "Không thể xử lý yêu cầu.",
        );
      }
    },
  });
  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="max-w-md">
        <ResponsiveDialogHeader>
          <ResponsiveDialogTitle>Cập nhật xử lý</ResponsiveDialogTitle>
          <ResponsiveDialogDescription>
            Chuyển trạng thái và ghi lại ghi chú để người tiếp theo nắm được
            tiến độ.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          <div className="grid gap-5 px-1 py-4 sm:px-2">
            <form.Field name="newStatus">
              {(field) => (
                <Field>
                  <FieldLabel>Trạng thái mới</FieldLabel>
                  <Select
                    value={field.state.value}
                    onValueChange={(value) =>
                      field.handleChange(value as ProcessStatus)
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {statuses.map((status) => (
                        <SelectItem key={status} value={status}>
                          {statusLabels[status]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </form.Field>
            <form.Field name="note">
              {(field) => {
                const error = field.state.meta.errors[0];
                return (
                  <Field>
                    <FieldLabel htmlFor="support-process-note">
                      Ghi chú xử lý
                    </FieldLabel>
                    <Textarea
                      id="support-process-note"
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(event) =>
                        field.handleChange(event.target.value)
                      }
                      aria-invalid={Boolean(error)}
                      placeholder="Ghi chú (không bắt buộc)"
                      className="min-h-24"
                      maxLength={2000}
                    />
                    {error ? <FieldError>{String(error)}</FieldError> : null}
                  </Field>
                );
              }}
            </form.Field>
          </div>
          <ResponsiveDialogFooter className="border-t px-1 pt-4 sm:px-2">
            <Button
              type="button"
              variant="outline"
              disabled={process.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, isSubmitting]) => (
                <Button
                  type="submit"
                  disabled={!canSubmit || isSubmitting || process.isPending}
                >
                  {process.isPending ? "Đang lưu..." : "Lưu trạng thái"}
                </Button>
              )}
            </form.Subscribe>
          </ResponsiveDialogFooter>
        </form>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}

function statusVariant(status: SupportStatus) {
  if (status === "resolved") return "success" as const;
  if (status === "rejected" || status === "cancelled")
    return "destructive" as const;
  return "secondary" as const;
}
