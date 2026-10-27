import { useForm } from "@tanstack/react-form";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { ConfirmDialog } from "@/components/admin/confirm-dialog";
import { PageHeader } from "@/components/admin/page-header";
import { SettingsRow } from "@/components/admin/settings-row";
import { SettingsSaveBar } from "@/components/admin/settings-save-bar";
import { SettingsSection as AdminSettingsSection } from "@/components/admin/settings-section";
import { StatusBadge } from "@/components/admin/status-badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { getFormErrorMessage } from "@/lib/form-errors";
import { useRbac } from "@/rbac/context";

const sectionLabels = {
  General: "Chung",
  Notifications: "Thông báo",
  Security: "Bảo mật",
} as const;

const generalSchema = z.object({
  workspaceName: z
    .string()
    .trim()
    .min(2, "Tên không gian làm việc phải có ít nhất 2 ký tự.")
    .max(80, "Tên không gian làm việc tối đa 80 ký tự."),
  workspaceSlug: z
    .string()
    .trim()
    .regex(
      /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
      "Slug chỉ dùng chữ thường, số và dấu gạch ngang.",
    ),
  timezone: z.string().min(1, "Chọn múi giờ."),
  language: z.string().min(1, "Chọn ngôn ngữ."),
  dateFormat: z.string().min(1, "Chọn định dạng ngày."),
});

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Nhập mật khẩu hiện tại."),
    newPassword: z.string().min(8, "Mật khẩu mới phải có ít nhất 8 ký tự."),
    confirmPassword: z.string().min(1, "Xác nhận mật khẩu mới."),
  })
  .refine((value) => value.newPassword === value.confirmPassword, {
    path: ["confirmPassword"],
    message: "Mật khẩu xác nhận không khớp.",
  });

function fieldError(errors: unknown[]) {
  return getFormErrorMessage(errors[0]) ?? null;
}

export function SettingsSection({
  section,
}: {
  section: "General" | "Notifications" | "Security";
}) {
  const { can } = useRbac();
  const label = sectionLabels[section];
  const canUpdate = can("settings.update");
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Quản trị / Hệ thống / Cài đặt"
        title={section === "General" ? "Cài đặt" : label}
        description={
          section === "General"
            ? "Quản lý tùy chọn chung của không gian làm việc."
            : section === "Notifications"
              ? "Kiểm soát cách không gian làm việc gửi các thông báo quan trọng."
              : "Quản lý các tùy chọn bảo mật đại diện cho không gian làm việc."
        }
      />
      {!canUpdate ? (
        <div className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
          Bạn đang xem ở chế độ chỉ đọc. Cần quyền{" "}
          <span className="font-mono text-xs">settings.update</span> để chỉnh
          sửa.
        </div>
      ) : null}
      {section === "General" ? <GeneralSettings canUpdate={canUpdate} /> : null}
      {section === "Notifications" ? (
        <NotificationSettings canUpdate={canUpdate} />
      ) : null}
      {section === "Security" ? (
        <SecuritySettings canUpdate={canUpdate} />
      ) : null}
    </div>
  );
}

function GeneralSettings({ canUpdate }: { canUpdate: boolean }) {
  const form = useForm({
    defaultValues: {
      workspaceName: "ProjectHub Workspace",
      workspaceSlug: "projecthub-workspace",
      timezone: "Asia/Ho_Chi_Minh",
      language: "vi-VN",
      dateFormat: "dd/MM/yyyy",
    },
    validators: { onSubmit: generalSchema },
    onSubmit: async ({ value, formApi }) => {
      toast.success("Đã lưu cài đặt chung");
      formApi.reset(value);
    },
  });
  const field = (name: "workspaceName" | "workspaceSlug") => (
    <form.Field name={name}>
      {(current) => {
        const error = fieldError(current.state.meta.errors);
        return (
          <div className="grid gap-2">
            <Label htmlFor={`settings-${name}`}>
              {name === "workspaceName"
                ? "Tên không gian làm việc"
                : "Workspace slug"}
            </Label>
            <Input
              id={`settings-${name}`}
              value={current.state.value}
              disabled={!canUpdate}
              onBlur={current.handleBlur}
              onChange={(event) =>
                current.handleChange(
                  name === "workspaceSlug"
                    ? event.target.value.toLowerCase().replace(/\s+/g, "-")
                    : event.target.value,
                )
              }
            />
            <p className="type-supporting text-muted-foreground">
              {name === "workspaceName"
                ? "Tên hiển thị trong thanh điều hướng và lời mời."
                : "Định danh thân thiện dùng trong các liên kết nội bộ."}
            </p>
            {error ? (
              <p className="type-supporting text-destructive">{error}</p>
            ) : null}
          </div>
        );
      }}
    </form.Field>
  );
  return (
    <form
      className="max-w-2xl space-y-6"
      onSubmit={(event) => {
        event.preventDefault();
        event.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <AdminSettingsSection
        title="Thông tin không gian làm việc"
        description="Những giá trị này được dùng trong các màn hình quản trị."
      >
        <div className="space-y-5">
          {field("workspaceName")}
          {field("workspaceSlug")}
        </div>
      </AdminSettingsSection>
      <AdminSettingsSection
        title="Tùy chọn khu vực"
        description="Chọn múi giờ, ngôn ngữ và cách hiển thị ngày."
      >
        <div className="grid gap-5 sm:grid-cols-2">
          <form.Field name="timezone">
            {(current) => (
              <div className="grid gap-2">
                <Label>Múi giờ mặc định</Label>
                <Select
                  value={current.state.value}
                  disabled={!canUpdate}
                  onValueChange={current.handleChange}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Asia/Ho_Chi_Minh">
                      Việt Nam (UTC+07:00)
                    </SelectItem>
                    <SelectItem value="Asia/Singapore">
                      Singapore (UTC+08:00)
                    </SelectItem>
                    <SelectItem value="UTC">UTC</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </form.Field>
          <form.Field name="language">
            {(current) => (
              <div className="grid gap-2">
                <Label>Ngôn ngữ mặc định</Label>
                <Select
                  value={current.state.value}
                  disabled={!canUpdate}
                  onValueChange={current.handleChange}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="vi-VN">Tiếng Việt</SelectItem>
                    <SelectItem value="en-US">English</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </form.Field>
          <form.Field name="dateFormat">
            {(current) => (
              <div className="grid gap-2 sm:col-span-2">
                <Label>Định dạng ngày</Label>
                <Select
                  value={current.state.value}
                  disabled={!canUpdate}
                  onValueChange={current.handleChange}
                >
                  <SelectTrigger className="sm:max-w-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dd/MM/yyyy">31/12/2025</SelectItem>
                    <SelectItem value="MM/dd/yyyy">12/31/2025</SelectItem>
                    <SelectItem value="yyyy-MM-dd">2025-12-31</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </form.Field>
        </div>
      </AdminSettingsSection>
      <form.Subscribe selector={(state) => [state.isDirty, state.isSubmitting]}>
        {([dirty, isSaving]) => (
          <SettingsSaveBar
            dirty={dirty}
            canUpdate={canUpdate}
            isSaving={isSaving}
            onCancel={() => form.reset()}
            onSave={() => void form.handleSubmit()}
          />
        )}
      </form.Subscribe>
    </form>
  );
}

type NotificationValues = Record<
  "email" | "security" | "product" | "weekly",
  boolean
>;
const notificationDefaults: NotificationValues = {
  email: true,
  security: true,
  product: false,
  weekly: true,
};

function NotificationSettings({ canUpdate }: { canUpdate: boolean }) {
  const [values, setValues] = useState(notificationDefaults);
  const [savedValues, setSavedValues] = useState(notificationDefaults);
  const dirty = Object.keys(values).some(
    (key) =>
      values[key as keyof NotificationValues] !==
      savedValues[key as keyof NotificationValues],
  );
  const update = (key: keyof NotificationValues, checked: boolean) =>
    setValues((current) => ({ ...current, [key]: checked }));
  const save = () => {
    setSavedValues(values);
    toast.success("Đã lưu tùy chọn thông báo");
  };
  return (
    <div className="max-w-2xl space-y-6">
      <AdminSettingsSection
        title="Tài khoản"
        description="Các thông báo liên quan trực tiếp đến tài khoản của bạn."
      >
        <div className="border-t">
          <SettingsRow
            title="Thông báo email"
            description="Nhận các thông báo quan trọng về tài khoản qua email."
            control={
              <Switch
                id="notification-email"
                checked={values.email}
                disabled={!canUpdate}
                onCheckedChange={(checked) => update("email", checked)}
                aria-label="Bật thông báo email"
              />
            }
          />
          <SettingsRow
            title="Cảnh báo bảo mật"
            description="Thông báo khi có thay đổi nhạy cảm hoặc hoạt động bất thường."
            control={
              <Switch
                id="notification-security"
                checked={values.security}
                disabled={!canUpdate}
                onCheckedChange={(checked) => update("security", checked)}
                aria-label="Bật cảnh báo bảo mật"
              />
            }
          />
        </div>
      </AdminSettingsSection>
      <AdminSettingsSection
        title="Không gian làm việc"
        description="Điều chỉnh các cập nhật sản phẩm và hoạt động của workspace."
      >
        <div className="border-t">
          <SettingsRow
            title="Cập nhật sản phẩm"
            description="Nhận thông tin về tính năng mới và thay đổi quan trọng."
            control={
              <Switch
                id="notification-product"
                checked={values.product}
                disabled={!canUpdate}
                onCheckedChange={(checked) => update("product", checked)}
                aria-label="Bật cập nhật sản phẩm"
              />
            }
          />
        </div>
      </AdminSettingsSection>
      <AdminSettingsSection
        title="Báo cáo"
        description="Nhận bản tổng hợp định kỳ về không gian làm việc."
      >
        <div className="border-t">
          <SettingsRow
            title="Tóm tắt hàng tuần"
            description="Một email ngắn gọn về hoạt động và các chỉ số trong tuần."
            control={
              <Switch
                id="notification-weekly"
                checked={values.weekly}
                disabled={!canUpdate}
                onCheckedChange={(checked) => update("weekly", checked)}
                aria-label="Bật tóm tắt hàng tuần"
              />
            }
          />
        </div>
      </AdminSettingsSection>
      <SettingsSaveBar
        dirty={dirty}
        canUpdate={canUpdate}
        onCancel={() => setValues(savedValues)}
        onSave={save}
      />
    </div>
  );
}

function SecuritySettings({ canUpdate }: { canUpdate: boolean }) {
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [confirmSessions, setConfirmSessions] = useState(false);
  const [twoFactor, setTwoFactor] = useState(false);
  return (
    <div className="max-w-2xl space-y-6">
      <AdminSettingsSection
        title="Mật khẩu"
        description="Thay đổi mật khẩu đại diện cho tài khoản hiện tại."
      >
        <Alert variant="warning">
          <AlertTitle>Chỉ là thao tác demo</AlertTitle>
          <AlertDescription>
            Mật khẩu không được lưu hoặc gửi đi trong phiên bản frontend này.
          </AlertDescription>
        </Alert>
        <div className="flex flex-col gap-3 border-t pt-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium">Đổi mật khẩu</p>
            <p className="type-supporting mt-1 text-muted-foreground">
              Thông tin nhập trong hộp thoại chỉ dùng cho demo và không được
              lưu.
            </p>
          </div>
          <Button
            variant="outline"
            disabled={!canUpdate}
            onClick={() => setPasswordOpen(true)}
          >
            Đổi mật khẩu
          </Button>
        </div>
      </AdminSettingsSection>
      <AdminSettingsSection
        title="Phiên đăng nhập"
        description="Kiểm tra phiên hiện tại và đăng xuất các phiên khác."
      >
        <div className="border-t pt-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium">Chrome trên Windows</p>
              <p className="type-supporting mt-1 text-muted-foreground">
                Quy Nhơn, Việt Nam · Hoạt động ngay lúc này
              </p>
            </div>
            <StatusBadge status="active" />
          </div>
          <Button
            variant="outline"
            className="mt-4"
            disabled={!canUpdate}
            onClick={() => setConfirmSessions(true)}
          >
            Đăng xuất các phiên khác
          </Button>
        </div>
      </AdminSettingsSection>
      <AdminSettingsSection
        title="Xác thực hai yếu tố"
        description="Thêm một lớp bảo vệ bổ sung cho tài khoản."
      >
        <SettingsRow
          title="Xác thực hai yếu tố"
          description="TOTP/QR sẽ được kết nối ở giai đoạn authentication backend."
          control={
            <div className="flex items-center gap-3">
              <Badge variant={twoFactor ? "success" : "secondary"}>
                {twoFactor ? "Đã bật" : "Đã tắt"}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                disabled={!canUpdate}
                onClick={() => setTwoFactor((current) => !current)}
              >
                {twoFactor ? "Tắt" : "Bật"}
              </Button>
            </div>
          }
        />
      </AdminSettingsSection>
      <ChangePasswordDialog
        open={passwordOpen}
        onOpenChange={setPasswordOpen}
      />
      <ConfirmDialog
        open={confirmSessions}
        onOpenChange={setConfirmSessions}
        title="Đăng xuất các phiên khác?"
        description="Tất cả phiên demo khác sẽ được đánh dấu đã đăng xuất. Phiên hiện tại vẫn được giữ lại."
        confirmLabel="Đăng xuất"
        onConfirm={() => {
          setConfirmSessions(false);
          toast.success("Đã đăng xuất các phiên khác");
        }}
      />
    </div>
  );
}

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const form = useForm({
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    },
    validators: { onSubmit: passwordSchema },
    onSubmit: async () => {
      toast.success("Đã xác nhận thay đổi mật khẩu trong demo");
      form.reset();
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Đổi mật khẩu</DialogTitle>
          <DialogDescription>
            Đây là luồng minh họa. Không có mật khẩu nào được lưu hoặc gửi đi.
          </DialogDescription>
        </DialogHeader>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            event.stopPropagation();
            void form.handleSubmit();
          }}
        >
          {(["currentPassword", "newPassword", "confirmPassword"] as const).map(
            (name) => (
              <form.Field key={name} name={name}>
                {(field) => {
                  const error = fieldError(field.state.meta.errors);
                  const labels = {
                    currentPassword: "Mật khẩu hiện tại",
                    newPassword: "Mật khẩu mới",
                    confirmPassword: "Xác nhận mật khẩu mới",
                  };
                  return (
                    <div className="grid gap-2">
                      <Label htmlFor={`password-${name}`}>{labels[name]}</Label>
                      <Input
                        id={`password-${name}`}
                        type="password"
                        value={field.state.value}
                        onBlur={field.handleBlur}
                        onChange={(event) =>
                          field.handleChange(event.target.value)
                        }
                      />
                      {error ? (
                        <p className="type-supporting text-destructive">
                          {error}
                        </p>
                      ) : null}
                    </div>
                  );
                }}
              </form.Field>
            ),
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                form.reset();
                onOpenChange(false);
              }}
            >
              Hủy
            </Button>
            <form.Subscribe
              selector={(state) => [state.canSubmit, state.isSubmitting]}
            >
              {([canSubmit, isSubmitting]) => (
                <Button type="submit" disabled={!canSubmit || isSubmitting}>
                  {isSubmitting ? "Đang kiểm tra..." : "Xác nhận"}
                </Button>
              )}
            </form.Subscribe>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
