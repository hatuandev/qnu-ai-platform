import { CreditCard, Pencil, Plus, QrCode, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  usePaymentConfigurationsQuery,
  useSavePaymentConfiguration,
} from "./api";
import type { PaymentConfiguration, PaymentConfigurationInput } from "./types";

const emptyInput: PaymentConfigurationInput = {
  name: "",
  isEnabled: true,
  qrMode: "uploaded",
  bankCode: "",
  accountNumber: "",
  accountName: "",
  contentTemplate: "{StudentName} + {StudentCode} + KTX {AcademicYearCode}",
  instructionText: "",
};

export function PaymentConfigurationsPage() {
  const query = usePaymentConfigurationsQuery();
  const [editing, setEditing] = useState<PaymentConfiguration | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="TÀI CHÍNH / CẤU HÌNH"
        title="Cấu hình thanh toán"
        description="Quản lý mã QR và hướng dẫn chuyển khoản dùng chung cho các đợt đăng ký."
        actions={
          <Button
            size="sm"
            className="gap-1.5 text-xs font-semibold"
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="size-3.5" />
            <span>Tạo cấu hình</span>
          </Button>
        }
      />

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm sm:text-base font-bold text-foreground">
              Danh sách cấu hình thanh toán
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Cấu hình đang kích hoạt sẽ xuất hiện trong danh mục chọn khi tạo
              đợt đăng ký nội trú mới.
            </p>
          </div>
        </div>

        {query.isLoading ? (
          <div className="rounded-xl border bg-card p-10 text-center text-xs text-muted-foreground shadow-2xs">
            Đang tải danh sách cấu hình...
          </div>
        ) : query.isError ? (
          <div className="rounded-xl border border-dashed bg-card p-10 text-center text-xs text-destructive shadow-2xs">
            Không thể tải cấu hình thanh toán.
          </div>
        ) : query.data?.length ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {query.data.map((item) => (
              <div
                key={item.id}
                className="flex flex-col justify-between rounded-xl border bg-card p-5 shadow-2xs hover:border-foreground/20 hover:shadow-xs transition-all space-y-4"
              >
                {/* Header: Name, Status, and Edit Button */}
                <div className="flex items-start justify-between gap-3 border-b pb-3.5">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-foreground text-base truncate">
                        {item.name}
                      </h3>
                      <Badge
                        variant={item.isEnabled ? "success" : "secondary"}
                        className="gap-1 text-[11px] font-medium shrink-0"
                      >
                        <span
                          className={`size-1.5 rounded-full ${
                            item.isEnabled
                              ? "bg-success"
                              : "bg-muted-foreground/60"
                          }`}
                        />
                        {item.isEnabled ? "Đang sử dụng" : "Đang tắt"}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {item.qrMode === "uploaded"
                        ? "QR tĩnh đã tải lên"
                        : "QR động theo hóa đơn (VietQR)"}
                    </p>
                  </div>

                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1.5 text-xs shrink-0 font-medium"
                    onClick={() => {
                      setEditing(item);
                      setDialogOpen(true);
                    }}
                  >
                    <Pencil className="size-3.5" />
                    <span>Chỉnh sửa</span>
                  </Button>
                </div>

                {/* 1. Top Section: 2-Column Split (Left: Banking Info, Right: QR Code) */}
                <div className="grid grid-cols-[1fr_auto] gap-4 items-center">
                  <div className="space-y-2.5 text-xs min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-muted-foreground w-22 shrink-0">
                        Ngân hàng:
                      </span>
                      <span className="font-semibold text-foreground font-mono truncate">
                        {item.bankCode || "—"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-muted-foreground w-22 shrink-0">
                        Số tài khoản:
                      </span>
                      <span className="font-semibold text-foreground font-mono text-sm truncate">
                        {item.accountNumber || "—"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-muted-foreground w-22 shrink-0">
                        Chủ tài khoản:
                      </span>
                      <span
                        className="font-semibold text-foreground uppercase truncate"
                        title={item.accountName}
                      >
                        {item.accountName || "—"}
                      </span>
                    </div>
                  </div>

                  {/* Right: QR Code Box */}
                  <div className="flex flex-col items-center justify-center p-2 rounded-xl border bg-muted/15 shrink-0 self-center">
                    {item.hasQrImage && item.qrImageUrl ? (
                      <img
                        alt={`Mã QR của ${item.name}`}
                        className="size-20 rounded-lg border bg-background object-contain p-1 shadow-2xs"
                        src={item.qrImageUrl}
                      />
                    ) : (
                      <div className="flex size-20 flex-col items-center justify-center rounded-lg border border-dashed bg-background text-muted-foreground">
                        <QrCode className="size-6 stroke-1" />
                        <span className="mt-1 text-[10px]">Chưa có QR</span>
                      </div>
                    )}
                    <span className="mt-1 text-[10px] text-muted-foreground font-medium">
                      Mã QR
                    </span>
                  </div>
                </div>

                {/* 2. Bottom Section: Full-Width Cú pháp chuyển khoản */}
                <div className="space-y-1.5 pt-1 border-t text-xs">
                  <div className="text-[11px] font-medium text-muted-foreground">
                    Cú pháp chuyển khoản:
                  </div>
                  <div className="rounded-md border bg-muted/30 px-3 py-1.5 font-mono text-[11px] text-foreground break-words select-all">
                    {item.contentTemplate}
                  </div>
                </div>

                {/* Hướng dẫn chuyển khoản nếu có */}
                {item.instructionText ? (
                  <div className="text-[11px] text-muted-foreground line-clamp-2 italic pt-2 border-t">
                    "{item.instructionText}"
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed bg-card p-10 text-center text-xs text-muted-foreground shadow-2xs">
            Chưa có cấu hình thanh toán nào. Hãy bấm{" "}
            <strong>Tạo cấu hình</strong> để thêm mới.
          </div>
        )}
      </section>

      <PaymentConfigurationDialog
        configuration={editing}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}

function PaymentConfigurationDialog({
  configuration,
  open,
  onOpenChange,
}: {
  configuration: PaymentConfiguration | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const save = useSavePaymentConfiguration();
  const [values, setValues] = useState<PaymentConfigurationInput>(emptyInput);
  const [selectedQrPreviewUrl, setSelectedQrPreviewUrl] = useState<
    string | null
  >(null);
  const [isQrCleared, setIsQrCleared] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setIsQrCleared(false);
    setValues(
      configuration
        ? {
            name: configuration.name,
            isEnabled: configuration.isEnabled,
            qrMode: configuration.qrMode === "dynamic" ? "dynamic" : "uploaded",
            bankCode: configuration.bankCode,
            accountNumber: configuration.accountNumber,
            accountName: configuration.accountName,
            contentTemplate: configuration.contentTemplate,
            instructionText: configuration.instructionText,
          }
        : emptyInput,
    );
  }, [configuration, open]);

  useEffect(() => {
    if (!values.qrImage) {
      setSelectedQrPreviewUrl(null);
      return;
    }

    const previewUrl = URL.createObjectURL(values.qrImage);
    setSelectedQrPreviewUrl(previewUrl);

    return () => URL.revokeObjectURL(previewUrl);
  }, [values.qrImage]);

  const update = <K extends keyof PaymentConfigurationInput>(
    key: K,
    value: PaymentConfigurationInput[K],
  ) => setValues((current) => ({ ...current, [key]: value }));

  const handleClearQr = () => {
    update("qrImage", undefined);
    setSelectedQrPreviewUrl(null);
    setIsQrCleared(true);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const currentPreviewUrl = isQrCleared
    ? null
    : (selectedQrPreviewUrl ?? configuration?.qrImageUrl);

  const submit = async () => {
    if (!values.name.trim()) {
      toast.error("Vui lòng nhập tên cấu hình");
      return;
    }
    if (
      values.qrMode === "uploaded" &&
      (!configuration?.hasQrImage || isQrCleared) &&
      !values.qrImage
    ) {
      toast.error("Vui lòng tải lên ảnh mã QR");
      return;
    }
    try {
      await save.mutateAsync({ id: configuration?.id, input: values });
      toast.success(configuration ? "Đã cập nhật cấu hình" : "Đã tạo cấu hình");
      onOpenChange(false);
    } catch (error) {
      toast.error(
        error instanceof Error ? error.message : "Không thể lưu cấu hình",
      );
    }
  };

  return (
    <ResponsiveDialog onOpenChange={onOpenChange} open={open}>
      <ResponsiveDialogContent className="flex max-h-[min(820px,calc(100vh-2rem))] w-full max-w-2xl flex-col overflow-hidden p-0 gap-0 shadow-xl">
        <ResponsiveDialogHeader className="border-b bg-muted/20 px-6 py-4 pr-12">
          <ResponsiveDialogTitle className="flex items-center gap-2.5 text-base sm:text-lg font-bold">
            <div className="flex size-8 items-center justify-center rounded-lg bg-muted text-muted-foreground shrink-0">
              <CreditCard className="size-4" />
            </div>
            <span>
              {configuration
                ? "Chỉnh sửa cấu hình thanh toán"
                : "Tạo cấu hình thanh toán"}
            </span>
          </ResponsiveDialogTitle>
          <ResponsiveDialogDescription className="text-xs text-muted-foreground mt-0.5">
            Cấu hình thông tin tài khoản ngân hàng và mã QR dùng cho các đợt
            đăng ký nội trú.
          </ResponsiveDialogDescription>
        </ResponsiveDialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto space-y-4 px-6 py-5 text-xs">
          {/* Row 1: Tên cấu hình & Phương thức mã QR (2 cột chuẩn 50/50 cân đối) */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label
                htmlFor="payment-config-name"
                className="text-xs font-medium"
              >
                Tên cấu hình <span className="text-destructive">*</span>
              </Label>
              <Input
                id="payment-config-name"
                className="text-xs"
                placeholder="VD: BIDV - Tài khoản KTX"
                value={values.name}
                onChange={(event) => update("name", event.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Phương thức mã QR</Label>
              <Select
                value={values.qrMode}
                onValueChange={(value) =>
                  update("qrMode", value as "dynamic" | "uploaded")
                }
              >
                <SelectTrigger className="text-xs">
                  <SelectValue placeholder="Chọn phương thức" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="uploaded">
                    Ảnh QR tải lên (Ảnh tĩnh thủ công)
                  </SelectItem>
                  <SelectItem value="dynamic">
                    QR động theo hóa đơn (Sinh tự động VietQR)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Row 2: Khung upload ảnh QR (nếu qrMode === "uploaded") */}
          {values.qrMode === "uploaded" ? (
            <div className="rounded-xl border bg-muted/15 p-4 space-y-3">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-0.5">
                  <Label className="text-xs font-semibold text-foreground">
                    Ảnh mã QR thanh toán{" "}
                    {configuration?.hasQrImage && !isQrCleared ? (
                      ""
                    ) : (
                      <span className="text-destructive">*</span>
                    )}
                  </Label>
                  <p className="text-[11px] text-muted-foreground">
                    Định dạng PNG, JPG hoặc WEBP. Mã QR này sẽ hiển thị cho sinh
                    viên khi xem hóa đơn.
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
                {currentPreviewUrl ? (
                  <div className="relative group shrink-0">
                    <img
                      src={currentPreviewUrl}
                      alt="Xem trước mã QR thanh toán"
                      className="size-24 rounded-lg border bg-background object-contain p-1 shadow-2xs"
                    />
                    <button
                      type="button"
                      title="Xóa ảnh QR này"
                      onClick={handleClearQr}
                      className="absolute -top-2 -right-2 flex size-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm hover:scale-110 transition-transform cursor-pointer"
                    >
                      <X className="size-3.5" />
                    </button>
                    <span className="mt-1 block text-[10px] text-center text-muted-foreground font-medium">
                      {values.qrImage ? "Ảnh mới chọn" : "Ảnh hiện tại"}
                    </span>
                  </div>
                ) : (
                  <div className="flex size-24 shrink-0 flex-col items-center justify-center rounded-lg border border-dashed bg-background text-muted-foreground">
                    <QrCode className="size-7 stroke-1" />
                    <span className="mt-1 text-[10px]">Chưa có QR</span>
                  </div>
                )}

                <div className="flex-1 space-y-2 w-full">
                  <div className="flex items-center gap-2">
                    <Input
                      ref={fileInputRef}
                      type="file"
                      id="payment-config-qr"
                      accept="image/png,image/jpeg,image/webp"
                      className="text-xs file:text-xs file:font-medium file:bg-muted file:text-foreground file:border-0 file:rounded-md file:px-2.5 file:py-1 cursor-pointer"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) {
                          update("qrImage", file);
                          setIsQrCleared(false);
                        }
                      }}
                    />
                    {currentPreviewUrl ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-9 px-2.5 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive shrink-0 gap-1"
                        onClick={handleClearQr}
                      >
                        <Trash2 className="size-3.5" />
                        <span>Xóa</span>
                      </Button>
                    ) : null}
                  </div>

                  {values.qrImage ? (
                    <p className="text-[11px] text-success font-medium">
                      ✓ Đã chọn: {values.qrImage.name} (
                      {(values.qrImage.size / 1024).toFixed(1)} KB)
                    </p>
                  ) : configuration?.hasQrImage && !isQrCleared ? (
                    <p className="text-[11px] text-muted-foreground">
                      ✓ Đang dùng ảnh QR hiện có. Chọn tệp mới để thay thế hoặc
                      bấm Xóa.
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}

          {/* Row 3: Mã ngân hàng & Số tài khoản (2 cột chuẩn 50/50 cân đối) */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label
                htmlFor="payment-config-bank"
                className="text-xs font-medium"
              >
                Mã ngân hàng (VietQR / Napas)
              </Label>
              <Input
                id="payment-config-bank"
                className="text-xs font-mono uppercase"
                placeholder="VD: BIDV, VCB, MB..."
                value={values.bankCode}
                onChange={(event) => update("bankCode", event.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <Label
                htmlFor="payment-config-account"
                className="text-xs font-medium"
              >
                Số tài khoản
              </Label>
              <Input
                id="payment-config-account"
                className="text-xs font-mono"
                placeholder="VD: 58010000123456"
                value={values.accountNumber}
                onChange={(event) =>
                  update("accountNumber", event.target.value)
                }
              />
            </div>
          </div>

          {/* Row 4: Tên chủ tài khoản */}
          <div className="space-y-1.5">
            <Label
              htmlFor="payment-config-account-name"
              className="text-xs font-medium"
            >
              Tên chủ tài khoản
            </Label>
            <Input
              id="payment-config-account-name"
              className="text-xs uppercase"
              placeholder="VD: TRUONG DAI HOC QUY NHON"
              value={values.accountName}
              onChange={(event) => update("accountName", event.target.value)}
            />
          </div>

          {/* Row 5: Cú pháp chuyển khoản */}
          <div className="space-y-1.5">
            <Label
              htmlFor="payment-config-template"
              className="text-xs font-medium"
            >
              Cú pháp nội dung chuyển khoản
            </Label>
            <Input
              id="payment-config-template"
              className="text-xs font-mono"
              placeholder="{StudentName} + {StudentCode} + KTX {AcademicYearCode}"
              value={values.contentTemplate}
              onChange={(event) =>
                update("contentTemplate", event.target.value)
              }
            />
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span className="text-[11px] text-muted-foreground mr-0.5">
                Chèn nhanh:
              </span>
              {[
                "{StudentName}",
                "{StudentCode}",
                "{AcademicYearCode}",
                "{InvoiceCode}",
              ].map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => {
                    if (!values.contentTemplate.includes(tag)) {
                      update(
                        "contentTemplate",
                        values.contentTemplate
                          ? `${values.contentTemplate} + ${tag}`
                          : tag,
                      );
                    }
                  }}
                  className="inline-flex items-center rounded-md border bg-muted/30 px-2 py-0.5 text-[11px] font-mono text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
                >
                  + {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Row 6: Hướng dẫn thanh toán */}
          <div className="space-y-1.5">
            <Label
              htmlFor="payment-config-instruction"
              className="text-xs font-medium"
            >
              Hướng dẫn thanh toán cho sinh viên
            </Label>
            <Textarea
              id="payment-config-instruction"
              className="text-xs"
              placeholder="Ví dụ: Chuyển khoản đúng số tiền và ghi đầy đủ cú pháp..."
              rows={2.5}
              value={values.instructionText}
              onChange={(event) =>
                update("instructionText", event.target.value)
              }
            />
          </div>

          {/* Row 7: Trạng thái kích hoạt (Thanh ngang liền mạch cân đối) */}
          <div className="flex items-center justify-between rounded-lg border bg-muted/15 px-4 py-3">
            <div className="space-y-0.5">
              <Label
                htmlFor="payment-config-status"
                className="text-xs font-semibold cursor-pointer"
              >
                Kích hoạt cấu hình
              </Label>
              <p className="text-[11px] text-muted-foreground">
                {values.isEnabled
                  ? "Cấu hình đang bật và sẽ xuất hiện để chọn khi tạo đợt đăng ký."
                  : "Cấu hình đang tạm tắt, sẽ không hiển thị khi tạo đợt mới."}
              </p>
            </div>
            <Switch
              id="payment-config-status"
              checked={values.isEnabled}
              onCheckedChange={(checked) => update("isEnabled", checked)}
            />
          </div>
        </div>

        <ResponsiveDialogFooter className="border-t bg-card px-4 py-3 sm:px-6 sm:py-3.5">
          <div className="grid grid-cols-2 gap-3 w-full sm:flex sm:w-auto sm:items-center sm:justify-end sm:gap-2.5">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs"
              disabled={save.isPending}
              onClick={() => onOpenChange(false)}
            >
              Hủy
            </Button>
            <Button
              type="button"
              size="sm"
              className="w-full sm:w-auto h-9 text-xs font-semibold"
              disabled={save.isPending}
              onClick={() => void submit()}
            >
              {save.isPending ? "Đang lưu..." : "Lưu cấu hình"}
            </Button>
          </div>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}
