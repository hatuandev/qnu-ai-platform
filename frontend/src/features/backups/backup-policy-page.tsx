import { useForm } from "@tanstack/react-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { AccessDenied } from "@/components/admin/access-denied";
import { PageHeader } from "@/components/admin/page-header";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  type BackupPolicy,
  backupKeys,
  saveBackupPolicy,
  useBackupPolicy,
} from "@/features/backups/api";
import { useRbac } from "@/rbac/context";

const schema = z.object({
  schedule_enabled: z.boolean(),
  frequency: z.enum(["daily", "weekly"]),
  weekday: z.number().int().min(0).max(6),
  hour: z.number().int().min(0).max(23),
  minute: z.number().int().min(0).max(59),
  utc_offset_minutes: z.number().int().min(-720).max(840),
  next_run_at: z.string().nullable(),
  last_backup_id: z.string().nullable(),
  notice: z.string().nullable(),
  remote_enabled: z.boolean(),
  endpoint: z.string(),
  bucket: z.string(),
  prefix: z.string(),
  region: z.string(),
  retention_enabled: z.boolean(),
  keep_daily: z.number().int().min(1).max(365),
  keep_weekly: z.number().int().min(1).max(104),
  keep_monthly: z.number().int().min(1).max(120),
});

export function BackupPolicyPage() {
  const { can } = useRbac();
  return can("ai.system.backup") ? <PolicyLoader /> : <AccessDenied />;
}

function PolicyLoader() {
  const query = useBackupPolicy();
  return (
    <div className="space-y-6">
      <Link
        to="/settings/backups"
        className="inline-flex items-center gap-2 text-sm text-muted-foreground"
      >
        <ArrowLeft className="size-4" />
        Sao lưu
      </Link>
      <PageHeader
        title="Chính sách sao lưu"
        description="Tự động hóa chỉ hoạt động sau khi bạn bật và cấp bí mật cho máy chủ."
      />
      {query.isLoading && <Skeleton className="h-48 w-full" />}
      {query.isError && (
        <Alert variant="destructive">
          <AlertDescription>{query.error.message}</AlertDescription>
        </Alert>
      )}
      {query.data && (
        <PolicyForm
          key={query.data.next_run_at ?? "disabled"}
          policy={query.data}
        />
      )}
    </div>
  );
}

function PolicyForm({ policy }: { policy: BackupPolicy }) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: saveBackupPolicy,
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: backupKeys });
      toast.success("Đã lưu chính sách sao lưu.");
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const form = useForm({
    defaultValues: policy,
    validators: { onSubmit: schema },
    onSubmit: async ({ value }) => {
      await mutation.mutateAsync(value).catch(() => undefined);
    },
  });
  const toggle = (
    name: "schedule_enabled" | "remote_enabled" | "retention_enabled",
    label: string,
  ) => (
    <form.Field name={name}>
      {(field) => (
        <div className="flex items-center justify-between gap-3">
          <Label htmlFor={`policy-${name}`}>{label}</Label>
          <Switch
            id={`policy-${name}`}
            checked={field.state.value}
            onCheckedChange={field.handleChange}
            disabled={mutation.isPending}
          />
        </div>
      )}
    </form.Field>
  );
  const text = (
    name: "endpoint" | "bucket" | "prefix" | "region",
    label: string,
  ) => (
    <form.Field name={name}>
      {(field) => (
        <div className="space-y-2">
          <Label htmlFor={`policy-${name}`}>{label}</Label>
          <Input
            id={`policy-${name}`}
            value={field.state.value}
            onChange={(event) => field.handleChange(event.target.value)}
            disabled={mutation.isPending}
          />
        </div>
      )}
    </form.Field>
  );
  const number = (
    name:
      | "hour"
      | "minute"
      | "weekday"
      | "utc_offset_minutes"
      | "keep_daily"
      | "keep_weekly"
      | "keep_monthly",
    label: string,
  ) => (
    <form.Field name={name}>
      {(field) => (
        <div className="space-y-2">
          <Label htmlFor={`policy-${name}`}>{label}</Label>
          <Input
            id={`policy-${name}`}
            type="number"
            value={field.state.value}
            onBlur={field.handleBlur}
            onChange={(event) => field.handleChange(Number(event.target.value))}
            disabled={mutation.isPending}
          />
          {field.state.meta.errors.length > 0 && (
            <p className="text-xs text-destructive">
              Giá trị ngoài phạm vi cho phép.
            </p>
          )}
        </div>
      )}
    </form.Field>
  );
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void form.handleSubmit();
      }}
      className="space-y-5"
    >
      <Alert>
        <AlertDescription>
          Kho bí mật bên ngoài: quản trị cấp BACKUP_SCHEDULE_SECRET_FILE và
          BACKUP_REMOTE_CREDENTIALS_FILE cho BE/worker. Không nhập mật khẩu hoặc
          khóa S3 trên trang này. Windows cần ACL riêng; Ubuntu chỉ tài khoản
          chạy app được đọc.
        </AlertDescription>
      </Alert>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="space-y-4 p-5">
          <h2 className="text-sm font-semibold">Lịch tự động</h2>
          {toggle("schedule_enabled", "Bật lịch")}
          <form.Field name="frequency">
            {(field) => (
              <div className="space-y-2">
                <Label htmlFor="policy-frequency">Chu kỳ</Label>
                <Select
                  value={field.state.value}
                  onValueChange={(value) =>
                    field.handleChange(value === "weekly" ? "weekly" : "daily")
                  }
                  disabled={mutation.isPending}
                >
                  <SelectTrigger id="policy-frequency">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Hằng ngày</SelectItem>
                    <SelectItem value="weekly">Hằng tuần</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </form.Field>
          <div className="grid grid-cols-2 gap-3">
            {number("hour", "Giờ (0–23)")}
            {number("minute", "Phút (0–59)")}
            {number("weekday", "Ngày tuần: 0=T2, 6=CN")}
            {number("utc_offset_minutes", "Lệch UTC (phút); VN=420")}
          </div>
          <p className="text-xs text-muted-foreground">
            Chỉ chạy khi worker bật. Tác vụ đang chạy sẽ làm hoãn lịch; khi bật
            lịch không chạy bù các ngày cũ.
          </p>
          <p className="text-sm">
            Lần tiếp theo:{" "}
            {policy.next_run_at
              ? new Date(policy.next_run_at).toLocaleString("vi-VN")
              : "Chưa bật"}
          </p>
          {policy.notice && (
            <p className="text-sm text-muted-foreground">{policy.notice}</p>
          )}
        </Card>
        <Card className="space-y-4 p-5">
          <h2 className="text-sm font-semibold">Bản sao S3/MinIO</h2>
          {toggle("remote_enabled", "Tự chuyển sau sao lưu")}
          {text("endpoint", "Endpoint S3/MinIO")}
          {text("bucket", "Bucket riêng cho backup")}
          {text("prefix", "Prefix")}
          {text("region", "Region")}
          <p className="text-xs text-muted-foreground">
            Chỉ chuyển file đã mã hóa, đọc lại để đối soát SHA-256. Không tạo
            bucket tự động. Chọn máy/ổ độc lập; endpoint khác chưa chứng minh
            khác ổ đĩa. Ngoài localhost nên dùng HTTPS.
          </p>
        </Card>
      </div>
      <Card className="space-y-4 p-5">
        <h2 className="text-sm font-semibold">Giữ bản cũ</h2>
        {toggle("retention_enabled", "Tự gỡ bản ngoài chính sách")}
        <div className="grid gap-3 sm:grid-cols-3">
          {number("keep_daily", "Số nhóm ngày")}
          {number("keep_weekly", "Số nhóm tuần")}
          {number("keep_monthly", "Số nhóm tháng")}
        </div>
        <p className="text-sm text-muted-foreground">
          Giữ hợp nhất các nhóm ngày/tuần/tháng, bản mới nhất, bản đã khôi phục
          thử gần nhất và bản ghim. Chỉ dọn sau lần sao lưu mới đạt yêu cầu; nếu
          bật S3, bản cũ phải có checksum S3 khớp. Gỡ vào thư mục phục hồi tạm,
          chưa xóa vĩnh viễn hoặc giải phóng dung lượng.
        </p>
      </Card>
      <Button type="submit" disabled={mutation.isPending}>
        <Save className="size-4" />
        {mutation.isPending ? "Đang lưu…" : "Lưu"}
      </Button>
    </form>
  );
}
