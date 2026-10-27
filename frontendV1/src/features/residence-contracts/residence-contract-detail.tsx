import {
  ArrowLeft,
  FilePenLine,
  Send,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  contractStatusLabels,
  paymentPlanLabels,
  useActivateResidenceContract,
  useCancelResidenceContract,
  useResidenceContractQuery,
  useSubmitResidenceContract,
  useUpdateResidenceContract,
} from "@/features/residence-contracts/api";
import { ResidenceContractDialog } from "@/features/residence-contracts/residence-contract-dialog";
import { formatDateTimeValue } from "@/lib/date-utils";
import { useRbac } from "@/rbac/context";

function formatDate(value?: string | null) {
  if (!value) return "—";
  const [year, month, day] = value.slice(0, 10).split("-");
  return `${day}/${month}/${year}`;
}

function formatDateTime(value?: string | null) {
  return formatDateTimeValue(value) || "—";
}

function formatAmount(value: number, currency: string) {
  return `${new Intl.NumberFormat("vi-VN").format(value)} ${currency}`;
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="space-y-1">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{value || "—"}</p>
    </div>
  );
}

type DetailAction = "submit" | "activate" | "cancel";

export function ResidenceContractDetail({ id }: { id: string }) {
  const { can } = useRbac();
  const query = useResidenceContractQuery(id);
  const update = useUpdateResidenceContract();
  const submit = useSubmitResidenceContract();
  const activate = useActivateResidenceContract();
  const cancel = useCancelResidenceContract();
  const [editOpen, setEditOpen] = useState(false);
  const [action, setAction] = useState<DetailAction | null>(null);

  if (query.isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-12 w-96" />
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-28" />
          ))}
        </div>
      </div>
    );
  }

  if (query.isError || !query.data) {
    return (
      <div className="rounded-lg border border-dashed p-10 text-center">
        <p className="font-medium">Không thể tải hợp đồng.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {query.error instanceof Error
            ? query.error.message
            : "Hợp đồng không tồn tại hoặc bạn không có quyền truy cập."}
        </p>
        <Button
          className="mt-4"
          variant="outline"
          onClick={() => void query.refetch()}
        >
          Thử lại
        </Button>
      </div>
    );
  }

  const contract = query.data;
  const canEdit = can("ktx.contracts.update");
  const isDraft = contract.status === "draft";
  const isPending = contract.status === "pending_signature";
  const actionTitle =
    action === "submit"
      ? "Gửi hợp đồng chờ ký?"
      : action === "activate"
        ? "Kích hoạt hợp đồng?"
        : "Hủy hợp đồng?";
  const actionDescription =
    action === "submit"
      ? "Sau khi gửi, bản nháp sẽ chuyển sang chờ ký và không còn chỉnh sửa được."
      : action === "activate"
        ? "Chỉ xác nhận khi hợp đồng đã được ký và có thể bắt đầu hiệu lực."
        : "Hợp đồng sẽ chuyển sang trạng thái đã hủy và không thể kích hoạt lại.";

  return (
    <div className="space-y-6">
      <Button
        variant="ghost"
        className="-ml-3"
        onClick={() => window.history.back()}
      >
        <ArrowLeft /> Quay lại danh sách
      </Button>
      <PageHeader
        eyebrow="Ký túc xá / Hợp đồng nội trú"
        title={contract.contractNumber}
        description={`${contract.studentName} · ${contract.studentCode}`}
        actions={
          <div className="flex flex-wrap gap-2">
            {canEdit && isDraft ? (
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <FilePenLine /> Chỉnh sửa
              </Button>
            ) : null}
            {canEdit && isDraft ? (
              <Button variant="outline" onClick={() => setAction("submit")}>
                <Send /> Gửi chờ ký
              </Button>
            ) : null}
            {canEdit && isPending ? (
              <Button onClick={() => setAction("activate")}>
                <ShieldCheck /> Kích hoạt
              </Button>
            ) : null}
            {canEdit && (isDraft || isPending) ? (
              <Button variant="outline" onClick={() => setAction("cancel")}>
                <Trash2 /> Hủy hợp đồng
              </Button>
            ) : null}
          </div>
        }
      />
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Trạng thái
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge
              variant={
                contract.status === "active"
                  ? "success"
                  : contract.status === "cancelled"
                    ? "secondary"
                    : contract.status === "pending_signature"
                      ? "warning"
                      : "outline"
              }
            >
              {contractStatusLabels[contract.status]}
            </Badge>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Giá trị hợp đồng
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold tabular-nums">
            {formatAmount(contract.totalAmount, contract.currency)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Hiệu lực từ
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">
            {formatDate(contract.effectiveFrom)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Hiệu lực đến
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xl font-semibold">
            {formatDate(contract.effectiveTo)}
          </CardContent>
        </Card>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Thông tin sinh viên</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <Info label="Họ và tên" value={contract.studentName} />
            <Info label="Mã sinh viên" value={contract.studentCode} />
            <Info
              label="Ngày sinh"
              value={formatDate(contract.studentDateOfBirth)}
            />
            <Info label="Giới tính" value={contract.studentGender} />
            <Info
              label="Khoa / lớp"
              value={[contract.studentFaculty, contract.studentClassName]
                .filter(Boolean)
                .join(" · ")}
            />
            <Info label="Số điện thoại" value={contract.studentPhoneNumber} />
            <div className="sm:col-span-2">
              <Info
                label="Địa chỉ thường trú"
                value={contract.studentPermanentAddress}
              />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Thông tin chỗ ở</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <Info label="Tòa nhà" value={contract.buildingName} />
            <Info
              label="Phòng"
              value={`${contract.roomCode} · ${contract.roomName}`}
            />
            <Info
              label="Thanh toán"
              value={
                paymentPlanLabels[contract.paymentPlan] ?? contract.paymentPlan
              }
            />
            <div className="sm:col-span-2">
              <Info label="Ghi chú" value={contract.note} />
            </div>
          </CardContent>
        </Card>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Lịch sử hợp đồng</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm sm:grid-cols-2">
          <Info label="Ngày tạo" value={formatDateTime(contract.created)} />
          <Info
            label="Cập nhật gần nhất"
            value={formatDateTime(contract.lastModified)}
          />
          <Info label="Ngày ký" value={formatDateTime(contract.signedAt)} />
          <Info
            label="Ngày thanh lý"
            value={formatDateTime(contract.liquidatedAt)}
          />
        </CardContent>
      </Card>
      <ResidenceContractDialog
        open={editOpen}
        contract={contract}
        residences={[]}
        onOpenChange={setEditOpen}
        onCreate={async () => undefined}
        onUpdate={async (contractId, input) => {
          await update.mutateAsync({ id: contractId, input });
          toast.success("Đã cập nhật hợp đồng.");
          setEditOpen(false);
        }}
        isSubmitting={update.isPending}
      />
      <ConfirmDialog
        open={action !== null}
        onOpenChange={(open) => {
          if (
            !open &&
            !submit.isPending &&
            !activate.isPending &&
            !cancel.isPending
          ) {
            setAction(null);
          }
        }}
        title={actionTitle ?? "Xác nhận thao tác"}
        description={actionDescription ?? ""}
        confirmLabel={action === "cancel" ? "Hủy hợp đồng" : "Xác nhận"}
        confirmVariant={action === "cancel" ? "destructive" : "default"}
        isLoading={submit.isPending || activate.isPending || cancel.isPending}
        onConfirm={() => {
          if (!action) return;
          const mutation =
            action === "submit"
              ? submit
              : action === "activate"
                ? activate
                : cancel;
          void mutation
            .mutateAsync(contract.id)
            .then(() => {
              setAction(null);
              toast.success(
                action === "submit"
                  ? "Đã chuyển hợp đồng sang chờ ký."
                  : action === "activate"
                    ? "Đã kích hoạt hợp đồng."
                    : "Đã hủy hợp đồng.",
              );
            })
            .catch((error: unknown) =>
              toast.error(
                error instanceof Error
                  ? error.message
                  : "Không thể thực hiện thao tác.",
              ),
            );
        }}
      />
    </div>
  );
}
